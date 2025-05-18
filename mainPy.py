import tkinter as tk
from pynput import keyboard
import threading
import time
import serial
from Robot import AnimatedRobot, Controller, expression_loop
from Cart import POSApp

class MainController:
    def __init__(self):
        self.current_program = "robot"  # أو "pos" حسب البداية
        self.root = tk.Tk()
        self.root.withdraw()

        # إعدادات النوافذ
        self.robot_window = tk.Toplevel(self.root)
        self.pos_window = tk.Toplevel(self.root)

        # تهيئة البرامج
        try:
            self.robot = AnimatedRobot(self.robot_window, serial_port='COM3', baudrate=9600)
            self.controller = Controller(self.robot)
        except Exception as e:
            print(f"Failed to initialize robot: {e}")
            self.robot = None
            self.controller = None

        # تشغيل تعبيرات وحركات وانتظار عشوائية إذا تم التهيئة بنجاح
        if self.controller and self.robot:
            threading.Thread(target=lambda: expression_loop(self, self.robot, self.controller), daemon=True).start()

        self.pos_app = POSApp(self.pos_window)

        # إعدادات التحكم
        self.current_program = "robot"
        self.setup_programs()
        self.setup_keyboard()

        # بدء التشغيل
        self.running = True
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        self.keyboard_thread.start()

        self.update_windows_visibility()
        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)
        self.root.mainloop()

    def setup_programs(self):
        """تهيئة إعدادات النوافذ"""
        for window in [self.robot_window, self.pos_window]:
            window.overrideredirect(True)
            window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}+0+0")
            window.attributes('-topmost', True)

    def setup_keyboard(self):
        self.listener = keyboard.Listener(
            on_press=self.on_key_press)
        self.listener.start()

    def on_key_press(self, key):
        try:
            if key.char == ' ':
                self.handle_space()
            elif key.char == 'q':
                self.safe_exit()
        except AttributeError:
            if key == keyboard.Key.ctrl:
                self.switch_programs()

    def handle_space(self):
        """معالجة ضغط مفتاح المسافة"""
        if self.current_program == "robot" and hasattr(self, 'controller'):
            self.controller.toggle()

    def switch_programs(self):
        print(self.current_program)
        """التبديل بين البرنامجين"""
        if not hasattr(self, 'last_switch_time') or time.time() - self.last_switch_time > 0.5:
            self.current_program = "pos" if self.current_program == "robot" else "robot"
            self.update_windows_visibility()
            self.last_switch_time = time.time()

    def update_windows_visibility(self):
        """تحديث حالة النوافذ"""
        if self.current_program == "robot":
            self.robot_window.deiconify()
            self.pos_window.withdraw()
        else:
            self.robot_window.withdraw()
            self.pos_window.deiconify()

    def keyboard_listener(self):
        """مراقبة لوحة المفاتيح"""
        while self.running:
            time.sleep(0.1)

    def safe_exit(self):
        """إغلاق آمن للبرنامج"""
        self.running = False
        if hasattr(self, 'listener'):
            self.listener.stop()
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    try:
        app = MainController()
    except KeyboardInterrupt:
        pass
    finally:
        keyboard.unhook_all()
