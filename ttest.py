import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame,
                             QGraphicsDropShadowEffect, QLineEdit, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QObject, QRunnable, QThreadPool, QTimer, QEvent, QTime
from PyQt5.QtGui import QFont, QCursor, QColor, QPixmap
from supabase import create_client, Client
import config
from PyQt5.QtWidgets import QScroller

# ✅ استخدام محمل الصور المحلي السريع
from local_image_loader import LocalImage
from Menue_product_popup import ProductSelectionDialog
from screensaver import ScreensaverDialog

# --- إعدادات Supabase ---
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


# ==========================================================
# 1. عامل العمليات الخلفية (Action Worker) - المطور 🛡️
# ==========================================================
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)  # إشارة جديدة للخطأ


class CartActionWorker(QRunnable):
    """يقوم بتنفيذ أوامر الداتابيس في الخلفية ويكتشف الفشل"""

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            # تنفيذ الدالة وتخزين النتيجة
            result = self.func(*self.args, **self.kwargs)

            # إذا كانت الدالة ترجع False (فشل منطقي في الداتا)
            if result is False:
                self.signals.error.emit("Database returned False")

        except Exception as e:
            # إذا حدث كراش أو انقطاع نت
            print(f"❌ Action Worker Critical Error: {e}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


# ==========================================================
# عامل التحقق من كود الخصم 🏷️
# ==========================================================
class CheckPromoWorker(QRunnable):
    def __init__(self, supabase_client, promo_code):
        super().__init__()
        self.client = supabase_client
        self.code = promo_code
        self.signals = WorkerSignals()  # نستخدم نفس إشارات WorkerSignals الموجودة

    def run(self):
        try:
            # 1. البحث عن الكود في جدول coupons (تأكد أن الجدول موجود في داتا بيس)
            # نفترض الجدول اسمه 'coupons' وفيه اعمدة: code, amount, is_active
            response = self.client.table('coupons').select("*").eq('code', self.code).eq('is_active', True).execute()

            if response.data:
                # الكود صحيح، نرجع قيمة الخصم
                discount_val = str(response.data[0]['amount'])  # نرسله كنص لتمريره
                self.signals.error.emit(f"SUCCESS|{discount_val}")  # نستخدم قناة الخطأ للنجاح مؤقتاً لتوفير الكود
            else:
                self.signals.error.emit("INVALID")  # كود غير صحيح

        except Exception as e:
            self.signals.error.emit("ERROR")
        finally:
            self.signals.finished.emit()


# ==========================================================
# عامل تحديث تفاصيل الفاتورة في السيرفر (شامل الخصم) ☁️
# ==========================================================
class UpdateInvoiceTotalWorker(QRunnable):
    def __init__(self, invoice_id, grand_total, subtotal, discount_amount, discount_code, discount_percent):
        super().__init__()
        self.invoice_id = invoice_id
        self.grand_total = grand_total
        self.subtotal = subtotal
        self.discount_amount = discount_amount
        self.discount_code = discount_code
        self.discount_percent = discount_percent

    def run(self):
        try:
            # تحديث الفاتورة بكافة التفاصيل
            supabase.table('invoice').update({
                'total_invoice': self.grand_total,       # الإجمالي النهائي
                'subtotal': self.subtotal,               # المبلغ قبل الخصم
                'discount_amount': self.discount_amount, # قيمة الخصم
                'discount_code': self.discount_code,     # كود الخصم
                'discount_percentage': self.discount_percent # نسبة الخصم
            }).eq('id', self.invoice_id).execute()
        except Exception as e:
            print(f"❌ Failed to update invoice details: {e}")

# ==========================================================
# 2. كلاس جلب البيانات (للتحديث العام)
# ==========================================================
class CartWorker(QObject):
    data_loaded = pyqtSignal(dict, list)
    error_occurred = pyqtSignal(str)

    @pyqtSlot()
    def fetch_data(self):
        try:
            # print("🔄 Worker: Fetching data...")
            response_invoice = supabase.table('invoice').select("*").eq('paid', False).order("id", desc=True).limit(
                1).execute()

            if not response_invoice.data:
                response_invoice = supabase.table('invoice').select("*").eq('id', 1).execute()

            if not response_invoice.data:
                self.error_occurred.emit("No active invoice found.")
                return

            invoice_data = response_invoice.data[0]

            response_cart = supabase.table('cart').select("*").order("id", desc=True).execute()
            cart_items = response_cart.data

            self.data_loaded.emit(invoice_data, cart_items)

        except Exception as e:
            # print(f"❌ Worker Error: {e}")
            self.error_occurred.emit(f"Fetch Error: {str(e)}")


# ==========================================================
# 3. كلاس السلة الرئيسي (CartWindow)
# ==========================================================
current_cart_window = None


class CartWindow(QMainWindow):
    request_fetch = pyqtSignal()

    def __init__(self, db_manager, start_recording_callback=None):
        super().__init__()
        global current_cart_window
        current_cart_window = self

        self.db_manager = db_manager
        self.start_recording_callback = start_recording_callback
        self.current_invoice_id = None

        self.active_menu_dialog = None
        #disscount value
        # متغيرات الخصم
        self.current_discount = 0.0  # النسبة المئوية
        self.current_code_name = None  # ✅ (جديد) اسم الكود لتخزينه في الداتابيس
        self.current_discount = 0.0  # لتخزين قيمة الخصم الحالية

        # ✅ خريطة لتخزين العناصر للوصول السريع
        self.cart_widgets = {}

        # ✅ مسبح الخيوط
        self.thread_pool = QThreadPool.globalInstance()

        self.setWindowTitle("Smart Cart")
        self.resize(500, 900)
        self.setMinimumSize(450, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #F9F9F9; }
            QScrollArea { border: none; background-color: transparent; }
            QLabel { font-family: 'Segoe UI', Arial, sans-serif; color: #2d3436; }
        """)

        self.thread = QThread()
        self.worker = CartWorker()
        self.worker.moveToThread(self.thread)

        self.request_fetch.connect(self.worker.fetch_data)
        self.worker.data_loaded.connect(self.populate_ui)
        self.worker.error_occurred.connect(lambda e: print(f"⚠️ Worker Error: {e}"))

        self.thread.start()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 25, 20, 25)
        self.main_layout.setSpacing(15)

        self.setup_header()
        self.setup_items_area()
        self.setup_conversation_controls()
        self.setup_footer()

        self.request_fetch.emit()

        # --- إعدادات شاشة التوقف ---
        self.screensaver_timer = QTimer(self)
        self.screensaver_timer.setInterval(10000)  # 30 ثانية (30000 ميلي ثانية)
        self.screensaver_timer.timeout.connect(self.show_screensaver)
        self.screensaver_timer.start()  # ابدأ العد فوراً

        # ضع اسم الفيديو هنا (يجب أن يكون بجانب ملفات المشروع)
        self.promo_video_path = "promo.mp4"

        # ✅ تحميل المنيو في الخلفية فوراً عند فتح البرنامج (لحل مشكلة بطء فتح المنيو)
        QTimer.singleShot(100, lambda: self.thread_pool.start(CartActionWorker(self.db_manager.fetch_menu)))

        # تثبيت مراقب الأحداث على التطبيق بالكامل
        QApplication.instance().installEventFilter(self)

    def setup_header(self):
        # نستخدم تخطيط عمودي رئيسي للرأس
        main_header_layout = QVBoxLayout()
        main_header_layout.setSpacing(15)

        # ✅ 1. إضافة اللوجو في المنتصف
        self.logo_lbl = QLabel()
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            # تصغير اللوجو لحجم مناسب (مثلاً أقصى ارتفاع 100)
            scaled_logo = logo_pixmap.scaled(200, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_lbl.setPixmap(scaled_logo)
            # ✅ أهم خطوة: محاذاة اللوجو في المنتصف
            self.logo_lbl.setAlignment(Qt.AlignCenter)
            main_header_layout.addWidget(self.logo_lbl)

        # ✅ 2. صف العنوان وزر المسح (تحت اللوجو)
        bottom_header_layout = QHBoxLayout()

        title_box = QVBoxLayout()
        title = QLabel("My Cart")
        title.setStyleSheet("font-size: 32px; font-weight: 800; color: #2d3436;")
        sub_title = QLabel("Check your items")
        sub_title.setStyleSheet("color: #b2bec3; font-size: 16px; font-weight: 500;")
        title_box.addWidget(title)
        title_box.addWidget(sub_title)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setFixedSize(90, 45)
        self.btn_clear.setStyleSheet("""
            QPushButton { 
                background-color: #ffeaa7; color: #d35400; 
                border-radius: 12px; font-weight: bold; font-size: 16px; border: none;
            }
            QPushButton:hover { background-color: #fab1a0; color: white; }
        """)
        self.btn_clear.clicked.connect(self.trigger_clear_cart)

        bottom_header_layout.addLayout(title_box)
        bottom_header_layout.addStretch()
        bottom_header_layout.addWidget(self.btn_clear)

        # إضافة الصف السفلي للرأس الرئيسي
        main_header_layout.addLayout(bottom_header_layout)

        # إضافة الرأس الرئيسي للنافذة
        self.main_layout.addLayout(main_header_layout)
        self.main_layout.addSpacing(10)

    def setup_items_area(self):
        # 1. حاوية رئيسية لتجميع الطبقات (الخلفية + السلة)
        stack_container = QWidget()
        # نستخدم GridLayout لأنه يسمح بوضع عنصرين فوق بعضهما في نفس الخانة (0,0)
        stack_layout = QGridLayout(stack_container)
        stack_layout.setContentsMargins(0, 0, 0, 0)

        # ============================================
        # الطبقة الأولى (الخلفية): صورة اللوجو الشفافة
        # ============================================
        self.bg_image_label = QLabel()
        self.bg_image_label.setAlignment(Qt.AlignCenter)  # محاذاة في المنتصف تماماً

        # تحميل وتجهيز الصورة
        bg_pixmap = QPixmap("cart_bg.png")
        if not bg_pixmap.isNull():
            # ✅✅✅ تحكم بالحجم من هنا بدقة ✅✅✅
            # الحجم 250x250 بكسل (متوسط ومناسب جداً)
            # Qt.KeepAspectRatio: يحافظ على أبعاد الصورة ولا يمطها
            self.bg_image_label.setPixmap(bg_pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            # جعل الليبل شفافاً ليقبل الصورة فقط
            self.bg_image_label.setStyleSheet("background: transparent;")

        # إضافة الصورة في الخانة (0,0) لتكون في الخلف
        stack_layout.addWidget(self.bg_image_label, 0, 0, Qt.AlignCenter)

        # ============================================
        # الطبقة الثانية (الأمامية): السلة والمنتجات
        # ============================================
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        # إخفاء حدود السكرول وجعله شفافاً لكي نرى الصورة خلفه
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { border: none; background: #f1f1f1; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #bdc3c7; border-radius: 4px; }
        """)

        self.items_container = QWidget()
        self.items_container.setObjectName("ItemsContainer")
        # جعل خلفية المنتجات شفافة
        self.items_container.setStyleSheet("background-color: transparent;")

        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setAlignment(Qt.AlignTop)
        self.items_layout.setSpacing(15)

        self.scroll.setWidget(self.items_container)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)

        # إضافة السكرول في نفس الخانة (0,0) ليكون فوق الصورة
        stack_layout.addWidget(self.scroll, 0, 0)

        # إضافة الحاوية المجمعة للنافذة الرئيسية
        self.main_layout.addWidget(stack_container)

    def setup_conversation_controls(self):
        self.conv_container = QWidget()
        # نستخدم هوامش سفلية وعلوية ليعطي مساحة للتصميم
        main_layout = QVBoxLayout(self.conv_container)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(20)  # مسافة بين زر المايك وزر المنيو

        # ==========================================
        # 1. زر المايك (Start Chat) - الدائري الكبير 🎙️
        # ==========================================
        self.mic_layout = QVBoxLayout()
        self.mic_layout.setAlignment(Qt.AlignCenter)

        # زر البدء (دائري وجميل)
        self.btn_start_conv = QPushButton("Start Order 🎙️")
        self.btn_start_conv.setFixedSize(250, 100)  # حجم كبير دائري
        self.btn_start_conv.setCursor(Qt.PointingHandCursor)
        self.btn_start_conv.setStyleSheet("""
            QPushButton { 
                background-color: #FF5722;
                color: white; 
                border-radius: 40px; /* نصف الحجم ليكون دائرة كاملة */
                font-size: 18px; 
                font-weight: bold; 
                border: 4px solid #f1f2f6; /* إطار خفيف ليعطي شكل جمالي */
            }
            QPushButton:hover { 
                background-color: #27ae60; 
                border: 4px solid #dfe6e9;
            }
            QPushButton:pressed {
                background-color: #219150;
                margin-top: 2px; /* حركة ضغط واقعية */
            }
        """)

        # إضافة ظل للزر ليكون عائماً (Floating Effect)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        self.btn_start_conv.setGraphicsEffect(shadow)

        self.btn_start_conv.clicked.connect(self.handle_start_click)

        # --- عناصر وضع الاستماع (تظهر مكان الزر الكبير) ---
        self.active_mic_widget = QWidget()
        active_layout = QHBoxLayout(self.active_mic_widget)
        active_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_status = QLabel("Listening...")
        self.lbl_status.setStyleSheet("color: #FF5722; font-weight: bold; font-size: 18px;")
        self.lbl_status.setAlignment(Qt.AlignCenter)

        self.btn_stop_conv = QPushButton("Stop 🛑")
        self.btn_stop_conv.setFixedSize(100, 45)
        self.btn_stop_conv.setCursor(Qt.PointingHandCursor)
        self.btn_stop_conv.setStyleSheet("""
            QPushButton { 
                background-color: white; color: #c0392b; 
                border: 2px solid #c0392b; border-radius: 20px; 
                font-size: 16px; font-weight: bold; 
            }
            QPushButton:hover { background-color: #c0392b; color: white; }
        """)
        self.btn_stop_conv.clicked.connect(self.stop_ui_mode)

        active_layout.addWidget(self.lbl_status)
        active_layout.addWidget(self.btn_stop_conv)
        self.active_mic_widget.hide()  # مخفي في البداية

        self.mic_layout.addWidget(self.btn_start_conv)
        self.mic_layout.addWidget(self.active_mic_widget)

        main_layout.addLayout(self.mic_layout)

        # ==========================================
        # 2. زر المنيو (تحت المايك) 📋
        # ==========================================
        self.btn_show_menu = QPushButton("📋 Open Menu")
        self.btn_show_menu.setFixedHeight(75)
        self.btn_show_menu.setCursor(Qt.PointingHandCursor)
        self.btn_show_menu.setStyleSheet("""
            QPushButton {
                background-color: #FF5722; 
                color: white; 
                border: 2px solid #dfe6e9;
                border-radius: 15px;
                font-size: 18px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #27ae60; 
                border-color: #b2bec3;
            }
        """)
        self.btn_show_menu.clicked.connect(self.open_product_menu)
        main_layout.addWidget(self.btn_show_menu)

        self.main_layout.addWidget(self.conv_container)

    def setup_footer(self):
        self.footer_frame = QFrame()
        self.footer_frame.setObjectName("FooterFrame")
        self.footer_frame.setStyleSheet("""
            QFrame#FooterFrame { background-color: white; border-radius: 20px; border: 1px solid #eee; }
        """)
        footer_layout = QVBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(20, 20, 20, 20)

        # --- قسم كود الخصم ---
        promo_layout = QHBoxLayout()
        self.promo_input = QLineEdit()
        self.promo_input.setPlaceholderText("Enter Promo Code (%)")  # توضيح أنها نسبة
        self.promo_input.setFixedHeight(45)
        self.promo_input.setStyleSheet(
            "QLineEdit { border: 1px solid #dfe6e9; border-radius: 10px; padding: 5px; font-size: 14px; }")

        self.btn_apply_promo = QPushButton("Apply")
        self.btn_apply_promo.setFixedSize(80, 45)
        self.btn_apply_promo.setCursor(Qt.PointingHandCursor)
        self.btn_apply_promo.setStyleSheet(
            "QPushButton { background-color: #2d3436; color: white; border-radius: 10px; font-weight: bold; }")
        self.btn_apply_promo.clicked.connect(self.handle_apply_promo)

        self.btn_remove_promo = QPushButton("✕")
        self.btn_remove_promo.setFixedSize(45, 45)
        self.btn_remove_promo.setCursor(Qt.PointingHandCursor)
        self.btn_remove_promo.setStyleSheet(
            "QPushButton { background-color: #ff7675; color: white; border-radius: 10px; font-weight: bold; }")
        self.btn_remove_promo.clicked.connect(self.remove_promo)
        self.btn_remove_promo.hide()

        promo_layout.addWidget(self.promo_input)
        promo_layout.addWidget(self.btn_apply_promo)
        promo_layout.addWidget(self.btn_remove_promo)

        self.lbl_promo_msg = QLabel("")
        self.lbl_promo_msg.setStyleSheet("font-size: 12px; margin-top: 5px;")
        self.lbl_promo_msg.hide()

        footer_layout.addWidget(
            QLabel("Payment Details", styleSheet="font-size: 18px; font-weight: bold; color: #2d3436;"))
        footer_layout.addSpacing(5)
        footer_layout.addLayout(promo_layout)
        footer_layout.addWidget(self.lbl_promo_msg)
        footer_layout.addSpacing(15)

        # --- تفاصيل الفاتورة (التصميم الجديد) ---
        self.invoice_details_layout = QVBoxLayout()

        # سنقوم بإنشاء الليبلات هنا وحفظها لتحديثها لاحقاً
        # 1. المجموع الفرعي
        self.lbl_subtotal = QLabel("Subtotal: 0.00 SAR")
        self.lbl_subtotal.setStyleSheet("font-size: 16px; color: #636e72; font-weight: 500;")

        # 2. قيمة الخصم
        self.lbl_discount_val = QLabel("Discount: 0.00 SAR")
        self.lbl_discount_val.setStyleSheet("font-size: 16px; color: #e74c3c; font-weight: 500;")

        # 3. الخط الفاصل
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #dfe6e9;")

        # 4. المجموع النهائي
        self.lbl_grand_total = QLabel("Grand Total: 0.00 SAR")
        self.lbl_grand_total.setStyleSheet("font-size: 24px; color: #2d3436; font-weight: 800;")

        self.invoice_details_layout.addWidget(self.lbl_subtotal)
        self.invoice_details_layout.addWidget(self.lbl_discount_val)
        self.invoice_details_layout.addWidget(line)
        self.invoice_details_layout.addWidget(self.lbl_grand_total)

        footer_layout.addLayout(self.invoice_details_layout)
        footer_layout.addSpacing(15)

        self.btn_checkout = QPushButton("Checkout")
        self.btn_checkout.setCursor(Qt.PointingHandCursor)
        self.btn_checkout.setFixedHeight(60)
        self.btn_checkout.setStyleSheet("""
            QPushButton { 
                background-color: #FF5722; color: white; 
                border-radius: 15px; font-size: 22px; font-weight: bold; border: none; 
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        footer_layout.addWidget(self.btn_checkout)
        self.main_layout.addWidget(self.footer_frame)

    @pyqtSlot(dict, list)
    def populate_ui(self, invoice_data, cart_items):
        try:
            self.current_invoice_id = invoice_data['id']

            # تنظيف القائمة الحالية والقاموس
            while self.items_layout.count():
                w = self.items_layout.itemAt(0).widget()
                if w: w.setParent(None); w.deleteLater()
            self.cart_widgets.clear()

            # جلب بيانات المنيو للصور
            menu_data = getattr(self.db_manager, 'menu_db', {})
            if not menu_data:
                self.db_manager.fetch_menu()
                menu_data = getattr(self.db_manager, 'menu_db', {})

            for item in cart_items:
                p_id = str(item.get('product_id'))
                img_url = None
                if p_id in menu_data:
                    img_url = menu_data[p_id].get('image')

                self.add_cart_item_widget(
                    item['id'],
                    str(item.get('name', 'Product')),
                    item.get('total_price', 0),
                    int(item.get('quantity', 1)),
                    item.get('price', 0),
                    str(item.get('product_id')),
                    img_url
                )

            self.update_footer_ui(invoice_data['id'], invoice_data.get('total_invoice', 0))

        except Exception as e:
            print(f"UI Error: {e}")

    def add_cart_item_widget(self, item_id, name, totalprice, qty, unitprice, product_id_db, image_url=None):
        item_frame = QFrame()
        item_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 18px; border: 1px solid #f1f2f6; }
            QFrame:hover { border: 1px solid #FF5722; }
        """)
        item_frame.setFixedHeight(120)

        h_layout = QHBoxLayout(item_frame)
        h_layout.setContentsMargins(15, 10, 15, 10)
        h_layout.setSpacing(15)

        img_lbl = LocalImage(name[:2].upper(), size=70)
        img_lbl.load_url(image_url)

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        info_layout.setAlignment(Qt.AlignCenter)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #2d3436; border: none; background: transparent;")

        unit_price_lbl = QLabel(f"Unit Price: {unitprice} SAR")
        unit_price_lbl.setStyleSheet(
            "color: #7f8c8d; font-size: 12px; font-weight: 500; border: none; background: transparent; margin-bottom: 5px;")

        # Controls
        qty_control_layout = QHBoxLayout()
        qty_control_layout.setSpacing(8)

        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(26, 26)
        btn_minus.setCursor(Qt.PointingHandCursor)
        btn_minus.setStyleSheet(
            "QPushButton { background-color: #f1f2f6; color: #2d3436; border-radius: 13px; font-weight: bold; border: none; } QPushButton:hover { background-color: #FF5722; color: white; }")

        qty_val_lbl = QLabel(str(qty))
        qty_val_lbl.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #2d3436; border: none; background: transparent;")

        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(26, 26)
        btn_plus.setCursor(Qt.PointingHandCursor)
        btn_plus.setStyleSheet(
            "QPushButton { background-color: #f1f2f6; color: #2d3436; border-radius: 13px; font-weight: bold; border: none; } QPushButton:hover { background-color: #FF5722; color: white; }")

        btn_minus.clicked.connect(lambda: self.trigger_update_qty(item_id, -1))
        btn_plus.clicked.connect(lambda: self.trigger_update_qty(item_id, 1))

        qty_control_layout.addWidget(btn_minus)
        qty_control_layout.addWidget(qty_val_lbl)
        qty_control_layout.addWidget(btn_plus)
        qty_control_layout.addStretch()

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(unit_price_lbl)
        info_layout.addLayout(qty_control_layout)

        # Total Price Label
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignCenter)
        total_price_lbl = QLabel(f"{totalprice} SR")
        total_price_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #FF5722; border: none; background: transparent;")

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(30, 30)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet(
            "QPushButton { background-color: #fff0f0; color: #ff4757; border-radius: 15px; font-weight: bold; font-size: 14px; border: none; } QPushButton:hover { background-color: #ff4757; color: white; }")
        remove_btn.clicked.connect(lambda: self.trigger_delete(item_id))

        right_layout.addWidget(total_price_lbl, alignment=Qt.AlignRight)
        right_layout.addWidget(remove_btn, alignment=Qt.AlignRight)

        h_layout.addWidget(img_lbl)
        h_layout.addLayout(info_layout)
        h_layout.addStretch()
        h_layout.addLayout(right_layout)

        self.items_layout.addWidget(item_frame)

        # ✅ تخزين المراجع لتحديثها لحظياً
        self.cart_widgets[item_id] = {
            'frame': item_frame,
            'qty_lbl': qty_val_lbl,
            'total_lbl': total_price_lbl,
            'price': unitprice,
            'qty': qty,
            'product_id': product_id_db
        }

    def update_footer_ui(self, inv_id, total):
        # لم نعد بحاجة لبناء الواجهة هنا لأننا بنيناها في setup_footer
        # فقط نعيد حساب الأرقام لتحديث النصوص
        self.recalculate_local_total()


    # ✅ معالجة خطأ الداتابيس (إعادة المزامنة)
    def handle_db_error(self, error_msg):
        print(f"⚠️ Sync Error: {error_msg} - Reverting Changes...")
        # يمكن إضافة تنبيه للمستخدم هنا (Toast)
        # نقوم بعمل تحديث إجباري لإعادة السلة لوضعها الصحيح في السيرفر
        self.request_fetch.emit()

    # ✅ تعديل فوري (Optimistic UI) - حذف
    def trigger_delete(self, item_id):
        if item_id in self.cart_widgets:
            # 1. إخفاء العنصر فوراً
            data = self.cart_widgets.pop(item_id)
            data['frame'].deleteLater()

            # 2. تحديث السعر الإجمالي محلياً
            self.recalculate_local_total()

            # 3. إرسال الطلب للخلفية
            worker = CartActionWorker(self.db_manager.remove_cart_item, data['product_id'])
            # ربط إشارة الخطأ
            worker.signals.error.connect(self.handle_db_error)
            self.thread_pool.start(worker)

    # ✅ تعديل فوري (Optimistic UI) - تعديل الكمية
    def trigger_update_qty(self, item_id, change):
        if item_id in self.cart_widgets:
            data = self.cart_widgets[item_id]
            new_qty = data['qty'] + change

            if new_qty <= 0:
                self.trigger_delete(item_id)
                return

            # 1. تحديث الرقم والسعر محلياً فوراً
            data['qty'] = new_qty
            data['qty_lbl'].setText(str(new_qty))
            data['total_lbl'].setText(f"{new_qty * data['price']} SR")

            # 2. تحديث الإجمالي الكلي
            self.recalculate_local_total()

            # 3. إرسال الطلب للخلفية
            worker = CartActionWorker(self.db_manager.sync_cart_item, data['product_id'], new_qty, is_absolute=True)
            # ربط إشارة الخطأ
            worker.signals.error.connect(self.handle_db_error)
            self.thread_pool.start(worker)

    # ✅ تعديل فوري (Optimistic UI) - مسح السلة
    def trigger_clear_cart(self):
        if not self.cart_widgets: return

        # 1. مسح كل شيء من الشاشة فوراً
        for data in self.cart_widgets.values():
            data['frame'].deleteLater()
        self.cart_widgets.clear()

        # 2. تصفير المجموع
        self.recalculate_local_total()

        # 3. إرسال الطلب للخلفية
        worker = CartActionWorker(self.db_manager.clear_cart)
        # ربط إشارة الخطأ
        worker.signals.error.connect(self.handle_db_error)
        self.thread_pool.start(worker)

    def handle_start_click(self):
        self.btn_start_conv.hide()  # إخفاء الزر الدائري الكبير
        self.active_mic_widget.show()  # إظهار حالة الاستماع وزر الإيقاف

        if self.start_recording_callback:
            self.start_recording_callback()

    @pyqtSlot()
    def stop_ui_mode(self):
        self.active_mic_widget.hide()  # إخفاء حالة الاستماع
        self.btn_start_conv.show()  # إعادة إظهار الزر الدائري

    def closeEvent(self, event):
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)

    def open_product_menu(self):
        if not hasattr(self, 'db_manager') or not self.db_manager: return

        # التأكد من تحميل المنيو
        if not getattr(self.db_manager, 'menu_db', {}):
            self.db_manager.fetch_menu()

        dialog = ProductSelectionDialog(self.db_manager, self)

        # ✅ ربط الإشارة بدالة الإضافة المحلية الفورية
        dialog.product_added_signal.connect(self.handle_instant_add)

        self.active_menu_dialog = dialog
        dialog.exec_()
        self.active_menu_dialog = None

    # ==========================
    # دوال نظام الخصم الجديد 🏷️
    # ==========================
    def handle_apply_promo(self):
        code = self.promo_input.text().strip()
        if not code: return

        self.btn_apply_promo.setEnabled(False)
        self.btn_apply_promo.setText("...")

        # إطلاق العامل في الخلفية
        worker = CheckPromoWorker(supabase, code)
        worker.signals.error.connect(self.on_promo_result)  # نستقبل النتيجة هنا
        self.thread_pool.start(worker)

    def on_promo_result(self, result_str):
        self.btn_apply_promo.setEnabled(True)
        self.btn_apply_promo.setText("Apply")

        if result_str.startswith("SUCCESS"):
            # نجح الخصم
            percentage = float(result_str.split("|")[1])
            self.current_discount = percentage
            self.current_code_name = self.promo_input.text().strip()  # ✅ حفظ اسم الكود

            self.promo_input.setDisabled(True)
            self.btn_apply_promo.hide()
            self.btn_remove_promo.show()

            self.lbl_promo_msg.setText(f"✅ Code Applied: {int(percentage)}% OFF")
            self.lbl_promo_msg.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.lbl_promo_msg.show()

            self.recalculate_local_total()

        else:
            self.lbl_promo_msg.setText("❌ Invalid Promo Code")
            self.lbl_promo_msg.setStyleSheet("color: #e74c3c;")
            self.lbl_promo_msg.show()
            QTimer.singleShot(2000, self.lbl_promo_msg.hide)

    def remove_promo(self):
        self.current_discount = 0.0
        self.current_code_name = None  # ✅ تصفير اسم الكود

        self.promo_input.clear()
        self.promo_input.setEnabled(True)
        self.btn_apply_promo.show()
        self.btn_remove_promo.hide()
        self.lbl_promo_msg.hide()

        self.recalculate_local_total()

    def recalculate_local_total(self):
        """حساب المجموع وتحديث السيرفر بكافة التفاصيل"""
        try:
            # 1. حساب Subtotal
            subtotal = 0.0
            for item in self.cart_widgets.values():
                subtotal += item['price'] * item['qty']

            # 2. حساب قيمة الخصم
            discount_amount = 0.0
            if self.current_discount > 0:
                discount_amount = subtotal * (self.current_discount / 100)

            # 3. حساب الإجمالي النهائي
            grand_total = max(0, subtotal - discount_amount)

            # 4. تحديث الواجهة
            self.lbl_subtotal.setText(f"Subtotal: {subtotal:.2f} SAR")

            if self.current_discount > 0:
                self.lbl_discount_val.setText(f"Discount ({int(self.current_discount)}%): -{discount_amount:.2f} SAR")
                self.lbl_discount_val.show()
            else:
                self.lbl_discount_val.hide()

            self.lbl_grand_total.setText(f"Grand Total: {grand_total:.2f} SAR")

            # 5. 🔥 تحديث السيرفر بالبيانات الكاملة 🔥
            if self.current_invoice_id:
                # نمرر: (رقم الفاتورة، الاجمالي النهائي، المجموع الفرعي، قيمة الخصم، اسم الكود، نسبة الخصم)
                updater = UpdateInvoiceTotalWorker(
                    self.current_invoice_id,
                    grand_total,
                    subtotal,
                    discount_amount,
                    self.current_code_name,
                    self.current_discount
                )
                self.thread_pool.start(updater)

        except Exception as e:
            print(f"Calc Error: {e}")

    # ==========================
    # دوال شاشة التوقف (Idle Check) 💤
    # ==========================
    def eventFilter(self, source, event):
        # أي حركة ماوس أو ضغط زر تعتبر نشاط
        if event.type() in [QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.TouchBegin]:
            self.reset_idle_timer()
        return super().eventFilter(source, event)

    def reset_idle_timer(self):
        # تصفير العداد والبدء من جديد
        self.screensaver_timer.stop()
        self.screensaver_timer.start()

    def show_screensaver(self):
        # 1. إيقاف العداد
        self.screensaver_timer.stop()

        # 2. ✅✅ إغلاق المنيو إذا كان مفتوحاً (هذا يحل مشكلة التعليق) ✅✅
        if self.active_menu_dialog:
            try:
                self.active_menu_dialog.reject()  # إغلاق المنيو برمجياً
                self.active_menu_dialog = None
            except Exception as e:
                print(f"Error closing menu: {e}")

        # 3. فتح شاشة التوقف
        screensaver = ScreensaverDialog(self.promo_video_path, self)
        screensaver.exec_()

        # 4. إعادة تشغيل العداد بعد العودة
        self.reset_idle_timer()

    def handle_instant_add(self, product_id_db, name, price, image_url):
        """إضافة منتج للسلة فوراً (Optimistic UI)"""
        try:
            # 1. البحث هل المنتج موجود بالفعل في الواجهة؟
            # نحتاج للبحث في self.cart_widgets عن عنصر يحمل نفس product_id_db
            existing_item_key = None
            for key, val in self.cart_widgets.items():
                if str(val['product_id']) == str(product_id_db):
                    existing_item_key = key
                    break

            if existing_item_key:
                # ✅ المنتج موجود: نزيد الكمية محلياً فقط
                data = self.cart_widgets[existing_item_key]
                new_qty = data['qty'] + 1

                # تحديث الواجهة
                data['qty'] = new_qty
                data['qty_lbl'].setText(str(new_qty))
                data['total_lbl'].setText(f"{new_qty * data['price']} SR")

            else:
                # ✅ المنتج غير موجود: نضيف ويدجت جديد
                # نستخدم رقم عشوائي مؤقت كـ ID للعنصر حتى نحصل على الـ ID الحقيقي من الداتابيس لاحقاً
                # لكن لغرض العرض، هذا كافٍ جداً
                temp_item_id = f"temp_{product_id_db}_{QTime.currentTime().msec()}"

                self.add_cart_item_widget(
                    item_id=temp_item_id,  # مفتاح مؤقت
                    name=name,
                    totalprice=price,  # الكمية 1
                    qty=1,
                    unitprice=price,
                    product_id_db=product_id_db,
                    image_url=image_url
                )

            # 2. تحديث الإجمالي الكلي (الفوتر) فوراً
            self.recalculate_local_total()

            # ملاحظة: العامل الخلفي (CartAddWorker) في المنيو سيقوم بتحديث الداتابيس،
            # وفي المرة القادمة التي يتم فيها تحديث السلة (fetch_data)، سيتم استبدال المفتاح المؤقت بالمفتاح الحقيقي.

        except Exception as e:
            print(f"Instant Add Error: {e}")

def refresh_cart_external():
    if current_cart_window:
        current_cart_window.request_fetch.emit()
    else:
        print("⚠️ Cart Window not ready yet")

