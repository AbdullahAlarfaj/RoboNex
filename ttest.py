import sys
import os
import cv2
import gc  # 👈 مكتبة تنظيف الذاكرة
from PyQt5.QtWidgets import QDialog, QPushButton, QLabel, QGridLayout, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap


class ScreensaverDialog(QDialog):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: black;")

        # --- إعداد OpenCV ---
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)

        # عداد الفريمات لتنظيف الذاكرة
        self.frame_counter = 0

        if not self.cap.isOpened():
            self.accept()
            return

        # 1. طبقة الفيديو
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setScaledContents(False)

        # Layout
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_label, 0, 0)

        # 2. الزر العائم
        self.start_btn = QPushButton("Start Order \n ابدأ الطلب 👆", self)
        self.start_btn.setFixedSize(350, 120)
        self.start_btn.setCursor(Qt.PointingHandCursor)

        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 160);
                color: white; 
                border: 4px solid rgba(255, 255, 255, 200);
                border-radius: 60px; 
                font-size: 28px; 
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 87, 34, 220);
                border-color: white;
            }
        """)
        self.start_btn.clicked.connect(self.close_screensaver)
        self.start_btn.raise_()

        # --- مؤقت تشغيل الفيديو ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        # ✅ تقليل السرعة لـ 40ms (أي 25 فريم بالثانية) لتخفيف الضغط على المعالج
        self.timer.start(40)

        self.showFullScreen()

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def update_frame(self):
        try:
            # ✅ إجبار النظام على الاستجابة للنقرات
            QApplication.processEvents()

            ret, frame = self.cap.read()
            if not ret:
                # إذا وصلنا للنهاية أو حدث خطأ قراءة، نعيد من البداية
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                # محاولة قراءة أخرى للتأكد
                ret, frame = self.cap.read()
                if not ret: return  # إذا فشل مرة أخرى نخرج

            # معالجة الصورة
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w

            qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qt_img)

            # ✅ استخدام FastTransformation للأداء العالي
            scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.FastTransformation)

            self.video_label.setPixmap(scaled_pixmap)

            # ✅✅✅ التنظيف الدوري للذاكرة (السر الحقيقي للاستقرار) ✅✅✅
            self.frame_counter += 1
            if self.frame_counter >= 300:  # كل 300 فريم (تقريباً كل 10 ثواني)
                gc.collect()  # اجبار بايثون على كنس الذاكرة
                self.frame_counter = 0

        except Exception as e:
            print(f"Video Error: {e}")
            self.close_screensaver()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'start_btn'):
            center_x = (self.width() - self.start_btn.width()) // 2
            center_y = (self.height() - self.start_btn.height()) // 2
            offset_down = 300
            self.start_btn.move(center_x, center_y + offset_down)
            self.start_btn.raise_()

    def close_screensaver(self):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()

        # ✅ تنظيف نهائي عند الإغلاق
        self.video_label.clear()
        gc.collect()

        self.accept()

    def mousePressEvent(self, event):
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
