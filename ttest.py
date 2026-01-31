import os
import hashlib
import requests
import time
from collections import deque
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, Qt, QTimer
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath

# ==========================================
# 1. إعدادات الكاش
# ==========================================
CACHE_DIR = "images_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


def get_local_path(url):
    if not url: return None
    file_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{file_hash}.png")


# ==========================================
# 2. عامل التحميل (Worker)
# ==========================================
class WorkerSignals(QObject):
    finished = pyqtSignal(str)  # يرسل مسار الملف عند الانتهاء
    failed = pyqtSignal()  # يرسل إشارة عند الفشل


class SequentialWorker(QRunnable):
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.signals = WorkerSignals()

    def run(self):
        try:
            # تحميل مع مهلة زمنية قصيرة
            response = requests.get(self.url, timeout=5, stream=True)
            if response.status_code == 200:
                with open(self.save_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                self.signals.finished.emit(self.save_path)
            else:
                self.signals.failed.emit()
        except:
            self.signals.failed.emit()


# ==========================================
# 3. مدير الطابور الذكي (The Manager)
# هذا هو العقل المدبر الذي يمنع التعليق
# ==========================================
class ImageQueueManager(QObject):
    def __init__(self):
        super().__init__()
        self.queue = deque()  # طابور الانتظار
        self.is_working = False
        self.thread_pool = QThreadPool.globalInstance()
        # تقليل عدد الخيوط القصوى لضمان عدم استهلاك الجهاز (احتياط)
        self.thread_pool.setMaxThreadCount(2)

    def add_to_queue(self, url, save_path, callback_widget):
        # إضافة الطلب للطابور
        self.queue.append((url, save_path, callback_widget))
        self.process_next()

    def process_next(self):
        # إذا كان الجهاز مشغولاً أو الطابور فارغاً، توقف
        if self.is_working or not self.queue:
            return

        self.is_working = True

        # استخراج أول طلب في الطابور
        url, save_path, widget = self.queue.popleft()

        # إنشاء العامل
        worker = SequentialWorker(url, save_path)

        # عند الانتهاء بنجاح
        worker.signals.finished.connect(lambda path: self.on_download_finished(path, widget))
        # عند الفشل
        worker.signals.failed.connect(self.on_download_failed)

        self.thread_pool.start(worker)

    def on_download_finished(self, path, widget):
        # 1. تحديث الودجت بالصورة
        if widget:
            try:
                widget.display_image(path)
            except:
                pass  # في حال تم إغلاق الودجت قبل الانتهاء

        # 2. الاستراحة وبدء التالي
        self.schedule_next()

    def on_download_failed(self):
        # حتى لو فشل، نكمل للي بعده
        self.schedule_next()

    def schedule_next(self):
        self.is_working = False
        # استراحة بسيطة (50 ميلي ثانية) ليرتاح المعالج والواجهة
        QTimer.singleShot(50, self.process_next)


# إنشاء نسخة عالمية واحدة من المدير
GLOBAL_MANAGER = ImageQueueManager()


# ==========================================
# 4. الودجت (LocalImage)
# ==========================================
class LocalImage(QLabel):
    def __init__(self, text_fallback="", size=140, parent=None, full_fill=False):
        super().__init__(parent)

        if not full_fill:
            self.setFixedSize(size, size)

        self.full_fill = full_fill
        self.target_size = size
        self.setAlignment(Qt.AlignCenter)

        self.setStyleSheet(f"""
            QLabel {{
                background-color: #f1f2f6;
                color: #a4b0be;
                font-size: 20px;
                font-weight: bold;
                border-radius: 15px; 
            }}
        """)

        self.setText(text_fallback)
        self.current_local_path = None
        self._loaded = False

    def load_url(self, url):
        if not url or str(url).lower() == "none" or len(str(url)) < 5:
            return

        local_path = get_local_path(url)
        self.current_local_path = local_path

        # 1. إذا الصورة موجودة، اعرضها فوراً (بدون طابور)
        if os.path.exists(local_path):
            self.display_image(local_path)
        else:
            # 2. غير موجودة؟ أرسلها للمدير ليضعها في الدور
            if not self._loaded:
                GLOBAL_MANAGER.add_to_queue(url, local_path, self)

    def display_image(self, file_path):
        # التأكد أن الملف يخص هذا العنصر
        if file_path != self.current_local_path:
            return

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            try:
                os.remove(file_path)
            except:
                pass
            return

        # معالجة الرسم
        size = self.width() if self.full_fill else self.target_size
        height = self.height() if self.full_fill else self.target_size

        target = QPixmap(size, height)
        target.fill(Qt.transparent)

        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addRoundedRect(0, 0, size, height, 15, 15)
        painter.setClipPath(path)

        scaled = pixmap.scaled(
            size,
            height,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )

        x = (scaled.width() - size) // 2
        y = (scaled.height() - height) // 2

        painter.drawPixmap(-x, -y, scaled)
        painter.end()

        self.setPixmap(target)
        self.setText("")
        self.setStyleSheet("background: transparent;")
        self._loaded = True

    def resizeEvent(self, event):
        if self.full_fill and self.current_local_path and os.path.exists(self.current_local_path):
            self.display_image(self.current_local_path)
        super().resizeEvent(event)
