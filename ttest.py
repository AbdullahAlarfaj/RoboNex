import sys
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QMovie, QPainter
import config
from logger_config import logger


class ResizableGifLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._movie = None

    def setMovie(self, movie):
        super().setMovie(movie)
        self._movie = movie
        if self._movie:
            self._movie.frameChanged.connect(self.repaint)

    def paintEvent(self, event):
        if self._movie and self._movie.isValid():
            current_pixmap = self._movie.currentPixmap()
            if not current_pixmap.isNull():
                painter = QPainter(self)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                painter.drawPixmap(self.rect(), current_pixmap)
        else:
            super().paintEvent(event)


class RobotFace(QMainWindow):
    update_face_signal = pyqtSignal(str)

    def __init__(self, trigger_callback=None):  # أضفنا trigger_callback
        super().__init__()
        self.setWindowTitle("Araba Mart Robot")
        self.resize(600, 600)
        self.setStyleSheet("background-color: black;")

        # حفظ دالة التسجيل لاستخدامها مع زر المسافة
        self.trigger_callback = trigger_callback

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.gif_label = ResizableGifLabel()
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.gif_label)

        self.current_movie = None
        self.expressions_paths = {}
        self.load_expressions_paths()

        self.update_face_signal.connect(self.perform_expression_change)
        self.perform_expression_change("neutral")

    def load_expressions_paths(self):
        base_path = Path(config.ASSETS_DIR)
        files = [
            ("neutral", "neutral.gif"),
            ("neutral1", "neutral.gif"),
            ("neutral2", "happy.gif"),
            ("happy", "happy.gif"),
            ("sad", "sad.gif"),
            ("angry", "angry.gif"),
            ("thinking", "thinking.gif"),
            ("listening", "listening.gif"),
            ("speaking", "happy.gif"),
            ("sleep", "sleep.gif")
        ]
        for name, filename in files:
            path = base_path / filename
            if path.exists():
                self.expressions_paths[name] = str(path)

    def set_expression(self, name):
        self.update_face_signal.emit(name)

    @pyqtSlot(str)
    def perform_expression_change(self, name):
        name = name.lower()
        if name not in self.expressions_paths:
            name = "neutral" if "neutral" in self.expressions_paths else None
        if not name: return

        file_path = self.expressions_paths[name]
        if self.current_movie:
            self.current_movie.stop()

        self.current_movie = QMovie(file_path)
        self.current_movie.setCacheMode(QMovie.CacheAll)
        self.gif_label.setMovie(self.current_movie)
        self.current_movie.start()

    # --- ميزة التقاط زر المسافة (Space) ---
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if self.trigger_callback:
                print("⌨️ Spacebar pressed!")
                self.trigger_callback()
