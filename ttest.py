import sys
import threading
import time
import random
import pygame

# مكتبات PyQt5
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


# ============================= استيراد الملفات ====================================
import config
from logger_config import logger
from arduino_controller import ArduinoController
from database_manager import DatabaseManager
from ai_engine import AIEngine
from utils import parse_ai_response

# استيراد الواجهات
from robot_face import RobotFace
import cart_ui  # نستورد الملف كـ موديول

# ============================= التهيئة العامة ====================================
pygame.mixer.init()

# ============================= تهيئة الكلاسات ====================================
arduino = ArduinoController(port=config.SERIAL_PORT, baudrate=config.BAUDRATE)
db_manager = DatabaseManager()
ai_brain = AIEngine()

# متغيرات عالمية للتحكم
face = None
is_recording = False


# ============================= العمليات الخلفية (Threads) ====================================
def menu_sync_loop():
    while True:
        db_manager.fetch_menu()
        time.sleep(60)


def cart_monitor_loop():
    while True:
        db_manager.fetch_remote_cart()
        time.sleep(2)


def random_behavior_loop():
    while True:
        if not is_recording and face:
            time.sleep(random.uniform(10, 20))
            if not is_recording:
                rand_choice = random.randint(1, 3)
                expr = "neutral"
                if rand_choice == 1:
                    expr = "neutral2"
                elif rand_choice == 2:
                    expr = "neutral1"
                elif rand_choice == 3:
                    expr = "sleep"

                if face: face.set_expression(expr)


# ============================= إدارة المحادثة المستمرة ====================================
def run_continuous_conversation():
    global is_recording

    # إعدادات الجلسة
    last_interaction_time = time.time()
    TIMEOUT_SECONDS = 5
    pending_barge_in_text = None

    logger.info("🟢 Starting Continuous Conversation Mode...")

    try:
        # ✅ التعديل 1: الحلقة تعتمد على متغير التسجيل لتتوقف فوراً عند ضغط زر Stop
        while is_recording:

            # التحقق من المهلة الزمنية
            current_time = time.time()
            if current_time - last_interaction_time > TIMEOUT_SECONDS:
                logger.info("⏳ Timeout reached. Ending conversation.")
                break

            # ====================================================
            # مرحلة الاستماع
            # ====================================================
            if pending_barge_in_text:
                user_text = pending_barge_in_text
                pending_barge_in_text = None
                logger.info(f"⏩ Skipping Mic (Using Barge-in text): {user_text}")
            else:
                if face: face.set_expression("listening")
                arduino.send_command("listening")

                # الاستماع
                user_text = ai_brain.listen(robot_last_text=ai_brain.last_ai_msg)

            # 🛑 نقطة تفتيش: هل ضغط المستخدم إيقاف أثناء الاستماع؟
            if not is_recording: break

            # ====================================================
            # مرحلة المعالجة
            # ====================================================
            if user_text:
                last_interaction_time = time.time()
                ai_brain.stop_speaking()

                if face: face.set_expression("thinking")

                ai_raw_response = ai_brain.think(
                    user_text,
                    db_manager.menu_string,
                    db_manager.get_cart_summary()
                )

                # 🛑 نقطة تفتيش ثانية
                if not is_recording: break

                parsed = parse_ai_response(ai_raw_response)

                # تنفيذ أوامر السلة
                if parsed.get("add"):
                    items = parsed["add"].split(',')
                    for item in items:
                        if ":" in item:
                            pid, qty = item.split(":")
                            # هنا نرسل is_absolute=True (تحديد دقيق)
                            db_manager.sync_cart_item(pid.strip(), int(qty), is_absolute=True)
                    cart_ui.refresh_cart_external()

                if parsed["remove"]:
                    items = parsed["remove"].split(',')
                    for item in items:
                        pid = item.split(":")[0].strip()
                        if parsed["remove"].strip().lower() == "all":
                            db_manager.clear_cart()
                        else:
                            db_manager.remove_cart_item(pid)
                    cart_ui.refresh_cart_external()

                if parsed["checkout"]:
                    if db_manager.archive_current_order():
                        logger.info("💰 Checkout Completed")
                    cart_ui.refresh_cart_external()

                # الرد الصوتي والحركي
                emotion = parsed["emotion"]
                if face: face.set_expression(emotion)
                arduino.send_command("happy" if emotion == "neutral" else emotion)

                if emotion == "neutral" and face:
                    face.set_expression("speaking")

                # النطق (فقط إذا ما زلنا نسجل)
                if is_recording:
                    is_interrupted, barge_in_text = ai_brain.speak(parsed["text"])
                    last_interaction_time = time.time()

                    if is_interrupted and barge_in_text:
                        logger.info(f"🔂 Processing Interruption: {barge_in_text}")
                        pending_barge_in_text = barge_in_text

            else:
                # صمت
                if not pygame.mixer.music.get_busy():
                    if face: face.set_expression("neutral")
                    arduino.send_command("neutral")

            time.sleep(0.05)

    except Exception as e:
        logger.error(f"Conversation Loop Error: {e}")
    finally:
        # تنظيف عند الخروج
        if face: face.set_expression("neutral")
        arduino.send_command("neutral")
        is_recording = False  # ضمان إغلاق الفلاق

        # إعادة أزرار السلة لوضعها الطبيعي
        if cart_ui.current_cart_window:
            from PyQt5.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(cart_ui.current_cart_window, "stop_ui_mode", Qt.QueuedConnection)

        logger.info("🔴 Session Ended.")


# ============================= دوال التحكم ====================================
def trigger_recording():
    global is_recording
    if is_recording:
        logger.info("⚠️ Session is already active.")
        return

    is_recording = True
    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
    threading.Thread(target=run_continuous_conversation, daemon=True).start()


def stop_recording_manual():
    global is_recording
    if is_recording:
        logger.info("🛑 Manual Stop Requested...")
        is_recording = False  # هذا سيكسر حلقة while في الدالة بالأعلى
        ai_brain.stop_speaking()
    else:
        logger.info("⚠️ Session is already inactive.")


def safe_exit():
    try:
        pygame.mixer.quit()
    except:
        pass
    sys.exit(0)


# ============================= التشغيل الرئيسي ====================================
if __name__ == "__main__":
    # 1. تشغيل العمليات الخلفية
    threading.Thread(target=menu_sync_loop, daemon=True).start()
    threading.Thread(target=cart_monitor_loop, daemon=True).start()
    threading.Thread(target=random_behavior_loop, daemon=True).start()

    # 2. إعداد تطبيق PyQt5
    app = QApplication(sys.argv)

    # 3. إنشاء نافذة الوجه
    face_window = RobotFace(trigger_callback=trigger_recording)
    face = face_window  # ربط المتغير العالمي

    # 4. إنشاء نافذة السلة (✅ التعديل 2: تمرير db_manager)
    # هذا السطر مهم جداً لكي تعمل قائمة المنتجات
    cart_window = cart_ui.CartWindow(
        db_manager=db_manager,
        start_recording_callback=trigger_recording
    )

    # 5. ربط زر الإيقاف (الأحمر)
    cart_window.btn_stop_conv.clicked.connect(stop_recording_manual)

    # 6. عرض النوافذ
    face_window.show()
    cart_window.show()

    print("🤖 System Started: Final PyQt5 Architecture")
    sys.exit(app.exec_())
