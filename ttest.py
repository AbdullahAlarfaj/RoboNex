import sys
import os
import cv2
from PyQt5.QtWidgets import QDialog, QPushButton, QLabel, QGridLayout, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont


class ScreensaverDialog(QDialog):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        # --- إعداد OpenCV لتشغيل الفيديو ---
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            print("❌ Error: Could not open video")
            self.accept()
            return

        # 1. طبقة الفيديو (الخلفية)
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        # نجعل الفيديو يتمدد ليملأ المكان
        self.video_label.setScaledContents(False)

        # 2. طبقة الزر (الأمامية)
        self.start_btn = QPushButton("Start Order \n ابدأ الطلب 👆")
        self.start_btn.setFixedSize(350, 120)  # حجم واضح وكبير
        self.start_btn.setCursor(Qt.PointingHandCursor)

        # تنسيق الزر (شفافية مع خط واضح)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 160); /* خلفية سوداء شفافة */
                color: white; 
                border: 4px solid rgba(255, 255, 255, 200); /* إطار أبيض */
                border-radius: 60px; 
                font-size: 28px; 
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 87, 34, 220); /* برتقالي عند المرور */
                border-color: white;
            }
        """)
        self.start_btn.clicked.connect(self.close_screensaver)

        # 3. نظام التخطيط الشبكي (Stacking System)
        # هذا هو السر: نضع العنصرين في نفس الخلية (0,0)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # أولاً نضيف الفيديو (ليكون في الخلف)
        layout.addWidget(self.video_label, 0, 0)

        # ثانياً نضيف الزر (ليكون في الأمام) ونحدد مكانه في المنتصف
        layout.addWidget(self.start_btn, 0, 0, Qt.AlignCenter)

        # --- مؤقت تشغيل الفيديو ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # 30 FPS

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            # إعادة تشغيل الفيديو (Loop)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return

        # تحويل الألوان
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)

        # تكبير الصورة لتناسب حجم الليبل الحالي (وليس الشاشة فقط)
        # KeepAspectRatio: يحافظ على الفيديو كاملاً (قد تظهر حواف سوداء اذا النسب مختلفة)
        # KeepAspectRatioByExpanding: يملأ الشاشة (قد يقص جزء من الفيديو)
        # جرب KeepAspectRatio أولاً لتضمن ظهور الزر والفيديو كاملاً
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.video_label.setPixmap(scaled_pixmap)

    def close_screensaver(self):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        self.accept()

    def mousePressEvent(self, event):
        # إغلاق عند لمس أي مكان في الشاشة
        self.close_screensaver()

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
