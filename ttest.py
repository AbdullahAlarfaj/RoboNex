import tkinter as tk
import threading
import time
import random
import pygame
import requests

# ============================= استيراد الملفات ====================================
import config
from logger_config import logger
from arduino_controller import ArduinoController
from database_manager import DatabaseManager
from ai_engine import AIEngine
from robot_face import RobotFace
from utils import parse_ai_response

# ============================= التهيئة العامة ====================================
pygame.mixer.init()  # لضمان عدم حدوث خطأ إذا استخدمت الصوت مستقبلاً
root = tk.Tk()
SERVER_IP = "192.168.1.15"
URL = f"http://{SERVER_IP}:5000/call_func"

# ============================= تهيئة الكلاسات ====================================
arduino = ArduinoController(port=config.SERIAL_PORT, baudrate=config.BAUDRATE)
db_manager = DatabaseManager()
ai_brain = AIEngine()
face = RobotFace(root)


# متغير التحكم بالتسجيل
is_recording = False


# ============================= العمليات الخلفية (Threads ====================================
def menu_sync_loop():
    """تحديث المنيو كل دقيقة"""
    while True:
        db_manager.fetch_menu()
        time.sleep(60)


def cart_monitor_loop():
    """مراقبة السلة كل ثانيتين (للفلتر فلو)"""
    while True:
        db_manager.fetch_remote_cart()
        time.sleep(2)


def random_behavior_loop():
    """تعابير عشوائية عند الخمول"""
    while True:
        if not is_recording:
            # وقت عشوائي بين الحركات
            time.sleep(random.uniform(10, 20))

            if not is_recording:
                # اختيار حركة عشوائية
                rand_choice = random.randint(1, 3)
                expr = "neutral"
                if rand_choice == 1:
                    expr = "neutral2"  # في تعريف الصور هي happy
                elif rand_choice == 2:
                    expr = "neutral1"
                elif rand_choice == 3:
                    expr = "sleep"

                face_remote_function(expr)
                # لا نرسل للاردوينو في الحركات العشوائية لتجنب الإزعاج (اختياري)
                # arduino.send_command(expr)


# ============================= معالجة المحادثة مع الذكاء الاصطناعي ====================================
def process_voice_command():
    global is_recording
    try:
        # 1. مرحلة الاستماع
        face_remote_function("listening")
        arduino.send_command("listening")  # تأكد أن الاردوينو يفهم هذا الأمر أو سيتجاهله

        user_text = ai_brain.listen()

        if not user_text:
            face_remote_function("neutral")
            is_recording = False
            return

        # 2. مرحلة التفكير
        face_remote_function("thinking")

        ai_raw_response = ai_brain.think(
            user_text,
            db_manager.menu_string,
            db_manager.get_cart_summary()
        )

        # 3. مرحلة التحليل
        parsed = parse_ai_response(ai_raw_response)

        # تنفيذ عمليات السلة
        if parsed["add"]:
            items = parsed["add"].split(',')
            for item in items:
                if ":" in item:
                    pid, qty = item.split(":")
                    db_manager.sync_cart_item(pid.strip(), int(qty))
                else:
                    db_manager.sync_cart_item(item.strip(), 1)

        if parsed["remove"]:
            items = parsed["remove"].split(',')
            for item in items:
                pid = item.split(":")[0].strip()
                if parsed["remove"].strip().lower() == "all":  # حالة خاصة للحذف الكلي
                    db_manager.clear_cart()
                else:
                    db_manager.remove_cart_item(pid)

        if parsed["checkout"]:
            success = db_manager.archive_current_order()
            if success:
                logger.info("💰 Checkout & Archiving Completed Successfully")
                # ممكن نغير الرد الصوتي هنا ليقول "تم حفظ الفاتورة"
            else:
                logger.error("❌ Checkout failed during archiving")

        # 4. مرحلة الرد والحركة (الترتيب المهم)
        emotion = parsed["emotion"]

        # أ. تحديث الوجه
        face_remote_function(emotion)

        # ب. إرسال الحركة للاردوينو (مرة واحدة)
        arduino_cmd = "happy" if emotion == "neutral" else emotion
        arduino.send_command(arduino_cmd)

        # ج. النطق (Azure TTS)
        # إذا كان الوجه محايداً، نجعله "speaking" أثناء النطق
        if emotion == "neutral":
            face_remote_function("speaking")

        ai_brain.speak(parsed["text"])

    except Exception as e:
        logger.error(f"Conversation Error: {e}")
    finally:
        # العودة للوضع الطبيعي دائماً
        face_remote_function("neutral")
        arduino.send_command("neutral")
        is_recording = False


def trigger_recording(event=None):
    global is_recording
    if is_recording: return
    is_recording = True
    # إيقاف أي صوت سابق إذا وجد
    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()

    threading.Thread(target=process_voice_command, daemon=True).start()

    #=======temporary face emotion sender========
def face_remote_function(name):
    payload = {"function": name}
    try:
        response = requests.post(URL, json=payload)
        print(f"استدعاء {name}:", response.json())
    except Exception as e:
        print("خطأ في الاتصال:", e)


def safe_exit():
    try:
        pygame.mixer.quit()
    except:
        pass
    root.destroy()
    import os
    os._exit(0)




if __name__ == "__main__":
    # تشغيل الثريدات
    threading.Thread(target=menu_sync_loop, daemon=True).start()
    threading.Thread(target=cart_monitor_loop, daemon=True).start()
    threading.Thread(target=random_behavior_loop, daemon=True).start()

    # ربط الأحداث
    root.bind("<space>", trigger_recording)
    root.bind("<Button-1>", trigger_recording)
    root.protocol("WM_DELETE_WINDOW", safe_exit)

    root.mainloop()
