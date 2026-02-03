from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
                             QWidget, QGridLayout, QLabel, QFrame, QSizePolicy, QScroller, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QRunnable, QThreadPool, \
    QAbstractAnimation
from PyQt5.QtGui import QFont, QCursor
from collections import deque

from local_image_loader import LocalImage


# ==========================================
# 1. نظام الطابور التسلسلي (The Queue System) 🛡️
# ==========================================
class WorkerSignals(QObject):
    finished = pyqtSignal()


class CartAddWorker(QRunnable):
    def __init__(self, db_manager, product_id):
        super().__init__()
        self.db_manager = db_manager
        self.product_id = product_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # إضافة المنتج في الداتابيس
            self.db_manager.sync_cart_item(self.product_id, 1, is_absolute=False)
        except Exception as e:
            print(f"Error in background worker: {e}")
        finally:
            self.signals.finished.emit()


class RequestQueueManager(QObject):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.queue = deque()
        self.is_processing = False
        self.thread_pool = QThreadPool.globalInstance()
        self.is_active = True  # ✅ علم للتأكد أننا لم نغلق البرنامج

    def add_task(self, product_id):
        self.queue.append(product_id)
        self.process_next()

    def process_next(self):
        if not self.is_active: return  # 🛑 توقف إذا تم الإغلاق
        if self.is_processing or not self.queue: return

        self.is_processing = True
        product_id = self.queue.popleft()

        worker = CartAddWorker(self.db_manager, product_id)
        worker.signals.finished.connect(self.on_worker_finished)
        self.thread_pool.start(worker)

    def on_worker_finished(self):
        if not self.is_active: return  # 🛑 حماية من الكراش بعد الإغلاق
        self.is_processing = False
        self.process_next()

    def stop_all(self):
        """إيقاف استقبال النتائج عند إغلاق النافذة"""
        self.is_active = False
        self.queue.clear()


# ==========================================
# 2. نافذة تكبير الصورة (Zoom Popup)
# ==========================================
class ZoomImageDialog(QDialog):
    def __init__(self, image_url, description, product_name, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(800, 900)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 25px;
                border: 2px solid #FF5722;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(15, 15, 15, 15)
        frame_layout.setSpacing(10)

        # 1. الصورة
        self.img_view = LocalImage("", size=550, full_fill=True)
        self.img_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.img_view.load_url(image_url)
        self.img_view.setStyleSheet("QLabel { background-color: transparent; border-radius: 20px; }")
        frame_layout.addWidget(self.img_view)

        # 2. الاسم
        lbl_title = QLabel(product_name)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2d3436; border: none;")
        frame_layout.addWidget(lbl_title)

        # 3. الوصف
        desc_scroll = QScrollArea()
        desc_scroll.setWidgetResizable(True)
        desc_scroll.setFixedHeight(120)
        desc_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: #f1f1f1; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #bdc3c7; border-radius: 4px; }
        """)

        desc_content = QWidget()
        desc_content.setStyleSheet("background: transparent;")
        desc_layout = QVBoxLayout(desc_content)

        self.desc_lbl = QLabel(description if description else "No description available.")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.desc_lbl.setStyleSheet("""
            font-size: 18px; 
            color: #636e72; 
            font-family: 'Segoe UI', Arial;
            border: none;
            padding: 5px;
        """)

        desc_layout.addWidget(self.desc_lbl)
        desc_scroll.setWidget(desc_content)
        frame_layout.addWidget(desc_scroll)

        # 4. زر الإغلاق
        close_btn = QPushButton("Close ✕")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedHeight(50)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f2f6; color: #2d3436;
                border-radius: 25px; font-weight: bold; font-size: 18px; border: none;
            }
            QPushButton:hover { background-color: #FF5722; color: white; }
        """)
        close_btn.clicked.connect(self.accept)
        frame_layout.addWidget(close_btn)
        layout.addWidget(frame)

    def mousePressEvent(self, event):
        self.accept()


# ==========================================
# 3. كلاس القائمة الرئيسي (محمي من التعليق)
# ==========================================
class ProductSelectionDialog(QDialog):
    product_added_signal = pyqtSignal(str, str, float, str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        # ✅ تهيئة مدير الطابور
        self.queue_manager = RequestQueueManager(self.db_manager)

        # ✅ متغير الكبح (Throttling) لمنع الضغط الجنوني
        self.can_click = True

        self.current_category = "All"
        self.category_buttons = {}

        self.setWindowTitle("Menu")
        self.setFixedSize(900, 1200)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f6fa;
                border-radius: 20px;
                border: 1px solid #dcdde1;
            }
            QScrollArea { border: none; background-color: transparent; }
            QLabel { font-family: 'Segoe UI', Arial, sans-serif; color: #2d3436; }
             QPushButton#CloseBtn {
                background-color: transparent; color: #636e72;
                border: none; font-size: 20px; font-weight: bold;
            }
            QPushButton#CloseBtn:hover { color: #e74c3c; }
        """)

        try:
            self.init_ui()
            self.setup_notification()
        except Exception as e:
            print(f"❌ Popup Init Error: {e}")
            self.reject()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # الرأس
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Our Menu")
        title_lbl.setStyleSheet("font-size: 26px; font-weight: 800; color: #2d3436;")

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.clicked.connect(self.safe_close)  # ✅ استخدام الإغلاق الآمن

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        main_layout.addLayout(header_layout)

        # التصنيفات
        self.category_container_layout = QHBoxLayout()
        self.setup_category_header()

        cat_scroll = QScrollArea()
        cat_scroll.setFixedHeight(70)
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setStyleSheet("background: transparent;")

        cat_widget = QWidget()
        cat_widget.setLayout(self.category_container_layout)
        cat_scroll.setWidget(cat_widget)

        main_layout.addWidget(cat_scroll)
        QScroller.grabGesture(cat_scroll.viewport(), QScroller.LeftMouseButtonGesture)

        # المنتجات
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(content_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        self.populate_products()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)

    def safe_close(self):
        """✅ إغلاق آمن يمنع الكراش"""
        # نوقف الطابور أولاً لمنع عودة العمال لنافذة ميتة
        self.queue_manager.stop_all()
        self.reject()

    def setup_notification(self):
        self.notification_lbl = QLabel("✅ Product Added to Cart", self)
        self.notification_lbl.setAlignment(Qt.AlignCenter)
        self.notification_lbl.setFixedSize(300, 50)
        self.notification_lbl.setStyleSheet("""
            background-color: #2ecc71; 
            color: white; 
            font-size: 16px; 
            font-weight: bold; 
            border-radius: 25px;
            padding: 10px;
        """)
        self.notification_lbl.move((self.width() - 300) // 2, 80)
        self.notification_lbl.hide()

        self.opacity_effect = QGraphicsOpacityEffect(self.notification_lbl)
        self.notification_lbl.setGraphicsEffect(self.opacity_effect)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_notification_animated)

        # تهيئة الأنيميشن مرة واحدة لتوفير الذاكرة
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def show_notification(self, message="Product Added"):
        self.notification_lbl.setText(f"✅ {message}")

        # ✅ إصلاح الأنيميشن: إذا كان ظاهراً بالفعل، فقط مدد الوقت
        # هذا يمنع تراكم الأنيميشن والتعليق
        if self.notification_lbl.isVisible() and self.opacity_effect.opacity() > 0.9:
            self.hide_timer.start(1200)  # تمديد الوقت فقط
            return

        self.notification_lbl.show()
        self.notification_lbl.raise_()

        self.anim.stop()  # إيقاف أي أنيميشن سابق
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

        self.hide_timer.start(1200)

    def hide_notification_animated(self):
        # أنيميشن الإخفاء ننشئه عند الحاجة (لأنه عكسي)
        self.anim_hide = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_hide.setDuration(400)
        self.anim_hide.setStartValue(1)
        self.anim_hide.setEndValue(0)
        self.anim_hide.finished.connect(self.notification_lbl.hide)
        self.anim_hide.start()

    def setup_category_header(self):
        products_dict = getattr(self.db_manager, 'menu_db', {})
        if not products_dict:
            self.db_manager.fetch_menu()
            products_dict = getattr(self.db_manager, 'menu_db', {})

        unique_types = set()
        if products_dict:
            for p in products_dict.values():
                p_type = p.get('type')
                if p_type:
                    unique_types.add(str(p_type).capitalize())

        categories = ["All"] + sorted(list(unique_types))
        self.category_container_layout.setSpacing(10)
        self.category_container_layout.setContentsMargins(0, 0, 0, 0)

        for cat_name in categories:
            btn = QPushButton(cat_name)
            btn.setFixedSize(120, 45)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=cat_name: self.filter_category(c))
            self.category_container_layout.addWidget(btn)
            self.category_buttons[cat_name] = btn

        self.category_container_layout.addStretch()
        self.update_category_styles()

    def filter_category(self, category_name):
        self.current_category = category_name
        self.update_category_styles()
        self.populate_products()

    def update_category_styles(self):
        for name, btn in self.category_buttons.items():
            if name == self.current_category:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF5722; color: white; border-radius: 22px;
                        font-weight: bold; border: none; font-size: 15px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: white; color: #2d3436; border-radius: 22px;
                        font-weight: bold; border: 1px solid #dfe6e9;
                    }
                    QPushButton:hover { background-color: #ffe0b2; border-color: #FF5722; }
                """)

    def populate_products(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        products_dict = getattr(self.db_manager, 'menu_db', {})
        if not products_dict:
            lbl = QLabel("القائمة فارغة")
            lbl.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(lbl, 0, 0)
            return

        row = 0
        col = 0
        max_cols = 3

        for pid, p_data in products_dict.items():
            if not p_data.get('stock', True): continue

            p_type = str(p_data.get('type', '')).capitalize()
            if self.current_category != "All":
                if self.current_category not in p_type and p_type not in self.current_category:
                    continue

            p_name = p_data.get('name', 'Unknown')
            p_price = p_data.get('price', 0)
            img_url = p_data.get('image')
            p_desc = p_data.get('description', '')

            card = QFrame()
            card.setFixedSize(220, 280)
            card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 20px;
                    border: 1px solid #dfe6e9;
                }
                QFrame:hover { border: 1px solid #FF5722; }
            """)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 15)
            card_layout.setSpacing(10)

            img_placeholder = LocalImage(p_name[:2].upper(), full_fill=True)
            img_placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            img_placeholder.load_url(img_url)
            img_placeholder.setCursor(Qt.PointingHandCursor)
            img_placeholder.mousePressEvent = lambda event, u=img_url, d=p_desc, n=p_name: self.open_zoomed_image(u, d,
                                                                                                                  n)

            info_layout = QVBoxLayout()
            info_layout.setContentsMargins(15, 0, 15, 0)
            info_layout.setSpacing(5)

            name_lbl = QLabel(p_name)
            name_lbl.setStyleSheet("font-weight: 700; font-size: 15px; color: #2d3436; border: none;")
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setWordWrap(True)

            price_lbl = QLabel(f"{p_price} ريال")
            price_lbl.setStyleSheet("color: #FF5722; font-size: 16px; font-weight: 800; border: none;")
            price_lbl.setAlignment(Qt.AlignCenter)

            add_btn = QPushButton("+ Add")
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.setFixedSize(100, 38)
            add_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF5722; color: white;
                    border-radius: 19px; font-weight: bold; border: none;
                }
                QPushButton:hover { background-color: #E64A19; }
                QPushButton:pressed { background-color: #BF360C; }
            """)
            add_btn.clicked.connect(lambda checked, i=pid, n=p_name: self.add_product_to_cart(i, n))

            info_layout.addWidget(name_lbl)
            info_layout.addWidget(price_lbl)
            info_layout.addWidget(add_btn, alignment=Qt.AlignCenter)

            card_layout.addWidget(img_placeholder)
            card_layout.addLayout(info_layout)

            self.grid_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def open_zoomed_image(self, img_url, description, product_name):
        if img_url:
            zoom_dialog = ZoomImageDialog(img_url, description, product_name, self)
            zoom_dialog.exec_()

    # ==========================================
    # ✅ إضافة المنتج للسلة (Optimistic + Queued + Throttled)
    # ==========================================
    def add_product_to_cart(self, product_id, product_name):
        # ✅ 1. الكبح (Throttling): منع الضغط إذا لم يمر 150ms على الضغطة السابقة
        # هذا الحل السحري لمنع التعليق
        if not self.can_click:
            return

        self.can_click = False
        # إعادة تفعيل الزر بعد 150 جزء من الثانية
        QTimer.singleShot(500, lambda: setattr(self, 'can_click', True))

        products_dict = getattr(self.db_manager, 'menu_db', {})
        p_data = products_dict.get(str(product_id), {})
        price = p_data.get('price', 0.0)
        image_url = p_data.get('image') or ""

        # 2. تحديث الواجهة فوراً (Optimistic)
        self.show_notification(f"Added: {product_name}")
        self.product_added_signal.emit(str(product_id), product_name, price, image_url)

        # 3. إضافة للداتابيس عبر الطابور (لمنع التعليق)
        self.queue_manager.add_task(product_id)
