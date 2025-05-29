import tkinter as tk
from pynput import keyboard, mouse
from pynput.keyboard import Key, Listener
from pynput.mouse import Button, Controller as MouseController
import threading
import time
import serial
from Robot import AnimatedRobot, Controller, expression_loop
from Cart import POSApp
import RPi.GPIO as GPIO


class MainController:
    def __init__(self):
        self.current_program = "robot"
        self.root = tk.Tk()
        self.root.withdraw()

        # Initialize GPIO for touch sensor
        GPIO.setmode(GPIO.BCM)
        self.TOUCH_PIN = 12
        GPIO.setup(self.TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.prev_touch_state = GPIO.HIGH

        # إعدادات النوافذ
        self.robot_window = tk.Toplevel(self.root)
        self.pos_window = tk.Toplevel(self.root)

        # تهيئة البرامج
        try:
            self.robot = AnimatedRobot(self.robot_window, serial_port='/dev/ttyUSB0', baudrate=9600)
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
        self.setup_input_listeners()

        # بدء التشغيل
        self.running = True
        self.setup_input_listeners()

        # Start touch sensor monitoring thread
        self.touch_thread = threading.Thread(target=self.monitor_touch_sensor, daemon=True)
        self.touch_thread.start()

        self.update_windows_visibility()
        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)
        self.root.mainloop()

    def monitor_touch_sensor(self):
        """Monitor the touch sensor in a separate thread"""
        while self.running:
            touch_state = GPIO.input(self.TOUCH_PIN)

            if touch_state != self.prev_touch_state:
                if touch_state == GPIO.LOW:  # Touch detected
                    self.handle_touch()
                self.prev_touch_state = touch_state

            time.sleep(0.1)

    def handle_touch(self):
        """Handle touch sensor input"""
        self.switch_programs()  # change program

    def setup_programs(self):
        """تهيئة إعدادات النوافذ"""
        for window in [self.robot_window, self.pos_window]:
            window.overrideredirect(True)
            window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}+0+0")
            window.attributes('-topmost', True)

    def setup_input_listeners(self):
        # بدء الاستماع لأحداث لوحة المفاتيح
        self.keyboard_listener = Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.keyboard_listener.start()


        # بدء الاستماع لأحداث الماوس
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.mouse_listener.start()
    
    
    def on_key_press(self, key):
        try:
            if key == Key.ctrl_l or key == Key.ctrl_r:
                self.switch_programs()
            elif key == Key.space:
                if self.current_program == "robot" and hasattr(self, 'controller'):
                    self.controller.toggle()
            elif key.char == 'q':
                self.safe_exit()
        except AttributeError:
            pass  # تجاهل الأزرار الخاصة

    def on_key_release(self, key):
        pass  # إضافة منطق هنا إذا لزم الأمر

    def on_mouse_click(self, x, y, button, pressed):
        """معالجة نقرات الماوس"""
        if button == Button.left and pressed:
            self.handle_click()

    def handle_click(self):
        """معالجة النقر/اللمس"""
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

    def safe_exit(self):
        self.running = False
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()  # استخدم stop() وليس استدعاء الكائن
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        GPIO.cleanup()  # Clean up GPIO resources\
        self.root.quit()
        self.root.destroy()
   

if __name__ == "__main__":
    try:
        app = MainController()
    except KeyboardInterrupt:
        pass
