from pynput.keyboard import Key, Listener
import tkinter as tk
from PIL import Image, ImageTk
import random
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk
import time
from elevenlabs import play
from elevenlabs.client import ElevenLabs
import threading
import re
import serial
import pygame
from openai import OpenAI
import os

# ========== تركيز تشغيل البرنامج على اعلى كفائة ==========
import resource
resource.setrlimit(resource.RLIMIT_NOFILE, (2048, 2048)

# ========== إعدادات الذكاء الاصطناعي والصوت (API) ==========
client1 = OpenAI(
    api_key="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")
speech_key = "27owsN70H5KeopQ3cQlyW6GOQJTFLepdyX4TOD9Pvg7xuQz2zFqPJQQJ99BDACFcvJRXJ3w3AAAYACOGqEUa"
client = ElevenLabs(api_key='sk_27f6bd5e157f6e01351ab8018a22957089cd49bc6f2a7e6f')
service_region = "qatarcentral"

# ========== توجيهات الرد للروبوت من شات جي بي تي ==========
SYSTEM_PROMPT = """
أنت مساعد ذكي يُدعى \"روبوت عربة مارت\". يجب عليك الالتزام بالتالي:
1. كن دقيقًا في المعلومات وواضحًا في التعبير.
2. إذا لم تعرف الإجابة، قل بصراحة \"لا أعرف\" بدلاً من التخمين.
3. لاتتكلم ابدا في المحتوى غير الأخلاقي أو السياسي الحساس.
4. عند السؤال عن هويتك، قل: \"أنا روبوت عربة مارت، مساعدك الذكي لمنحك تجربة تسوق فريدة وممتعة\".
5. استخدم أسلوبًا مهذبًا وودودًا في جميع الأجوبة.
6. اجب دائما باجوبة قصيرة بين 3 الى 8 جمل فقط.
7. اذا سالك العميل اين قسم النودلز قل: \"على يدك اليمين عند المدخل ستجد طاولة اعداد النودلز\".
8. اكتب ردك بالشكل التالي:
مهم جدا جدا اتباع التنسيق التالي في الرد
اكتب مشاعرك او الحركات التي تريد ان تعملها مثل ان تقول اهلا او هاي اكتبهم بالترتيب التالي والرد الحقيقي ايضا اكتبه بالترتيب التالي:
  [EM]اكتب مشاعرك الخاصة هنا من القائمة التي بالاسفل [/EM]
   [TEXT] هذا هو النص الرئيسي للرد [/TEXT] 
لابد من اضافة [TEXT] قبل الكلام و [/TEXT]  اخر الكلام
ولا بد من اضافة [EM] قيل المشاعر ثم [/EM] بعد المشاعر
   المشاعر والحركات يجب ان تكون من اللستة التالي واختر واحدة فقط: happy, angry, neutral, sad, hello.
   9. اذا سالك العميل اي سؤال يتعلق عن سعر منتج قل له اضغط الزر الذي على راسي لتنتقل الى صفحة تشييك الاسعار وقل له انه بامكانه عن طريق هذه الصفحة اضافة اي منتج في السلة الخاصة به والمحاسبة بشكل مختصر وسريع جدا.
"""
# ===============(تهيئة تشغيل الصوت الاعلاني)=============
os.environ['SDL_AUDIODRIVER'] = 'dsp'  # or 'dsp'
pygame.mixer.init()
# ===========(القيم والمتغيرات العالمية)==============
randnormal = 0
seqsounds = 1


# ========== كلاس تحريك تعابير وجه الروبوت ==========
class AnimatedRobot:
    def __init__(self, master, serial_port='/dev/ttyUSB0', baudrate=9600):
        self.serial_lock = threading.Lock()
        self.master = master
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.ser = None
        self.setup_serial()
        self.setup_window()
        self.create_canvas()
        self.load_expressions()
        self.set_expression("neutral")
        self.update_animation()

    # ========== تهيئة الاردوينو و الاتصال به ==========
    def setup_serial(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baudrate, timeout=1)
            time.sleep(2)
        except serial.SerialException as e:
            print(f"⚠️ Serial error: {e}. Running in demo mode (no Arduino).")
            self.ser = None

    # ========== تجهيز حجم واعدادات النافذة ==========
    def setup_window(self):
        self.master.title("روبوت التعابير المتحركة")
        self.master.geometry("500x500")
        self.master.configure(bg='black')
        self.master.resizable(False, False)

    def create_canvas(self):
        self.canvas_width = 500
        self.canvas_height = 500
        self.canvas = tk.Canvas(self.master, width=self.canvas_width, height=self.canvas_height, bg='black',
                                highlightthickness=0)
        self.canvas.pack()

    # ========== تحميل التعبيرات لوجه الروبوت وتجهيزها للاستعمال ==========
    
    def load_expressions(self):
        # قبل تحميل تعبيرات جديدة، تنظيف القديمة إن وجدت
        if hasattr(self, 'expressions'):
            for expr in self.expressions.values():
                if 'frames' in expr:
                    for frame in expr['frames']:
                        frame.__del__()
        self.expressions = {}
        self.expressions_dir = Path("robot_expressions")
        self.expressions = {}
        expressions_list = [
            ("neutral", "neutral.gif"),
            ("happy", "happy.gif"),
            ("sad", "sad.gif"),
            ("angry", "angry.gif"),
            ("surprised", "surprised.gif"),
            ("thinking", "thinking.gif"),
            ("listening", "listening.gif"),
            ("hello", "happy.gif"),
            ("neutral1", "neutral.gif"),
            ("neutral2", "happy.gif"),
            ("sleep", "sleep.gif")
        ]

        for name, filename in expressions_list:
            path = self.expressions_dir / filename
            try:
                gif = Image.open(path)
                frames, durations = [], []
                for frame_num in range(gif.n_frames):
                    gif.seek(frame_num)
                    frame = gif.copy().resize((self.canvas_width, self.canvas_height), Image.LANCZOS)
                    frames.append(ImageTk.PhotoImage(frame))
                    durations.append(gif.info.get('duration', 100))
                self.expressions[name] = {
                    "frames": frames,
                    "durations": durations,
                    "current_frame": 0,
                    "total_frames": len(frames)
                }
            except Exception as e:
                print(f"خطأ في تحميل {filename}: {e}")

    # ========== امر تغيير تعبير وجه الروبوت ==========
    def set_expression(self, name):
        with self.serial_lock:  # Protect serial access
            if self.ser is not None:
                self.ser.write((name + "\n").encode())
        try:
            print("name" + name)
            if self.ser is not None and self.ser.is_open:
                self.ser.write((name + "\n").encode())
            else:
                print("⚠️ الأردوينو غير متصل، تم تجاهل الإرسال")

            if name not in self.expressions:
                print(f"⚠️ التعبير {name} غير موجود")
                if 'neutral' in self.expressions:
                    name = 'neutral'
                else:
                    return

            self.current_expression = self.expressions[name]
            self.current_expression["current_frame"] = 0
            self.current_expression_name = name
        except Exception as e:
            print(f"خطأ في تعيين التعبير {name}:", e)
            if 'neutral' in self.expressions:
                self.current_expression = self.expressions['neutral']

    # ========== تحريك انميشن الصور المتحركة ==========
    def update_animation(self):
        try:
            if not hasattr(self, 'current_expression') or not self.current_expression:
                self.master.after(100, self.update_animation)
                return

            frame_index = self.current_expression["current_frame"]
            frame = self.current_expression["frames"][frame_index]
            self.canvas.delete("all")
            self.canvas.create_image(self.canvas_width // 2, self.canvas_height // 2, image=frame)
            self.current_expression["current_frame"] = (frame_index + 1) % self.current_expression["total_frames"]
            delay = self.current_expression["durations"][frame_index]
            self.master.after(delay, self.update_animation)
        except Exception as e:
            print("خطأ في التحريك:", e)
            # إعادة المحاولة بعد فترة
            self.master.after(100, self.update_animation)
            # العودة إلى الوضع الطبيعي
            if hasattr(self, 'expressions') and 'neutral' in self.expressions:
                self.current_expression = self.expressions['neutral']


# ========== تحليل رد الذكاء الاصطناعي ==========
def emotion_split(response):
    print("deepseek answerr: " + response)
    emotion = re.search(r'\[EM\](.*?)\[/EM\]', response)
    text = re.search(r'\[TEXT\](.*?)\[/TEXT\]', response, re.DOTALL)
    return {
        "emotion": emotion.group(1) if emotion else "neutral",
        "text": text.group(1).strip() if text else response
    }


# ========== ارسال طلب وسحب الرد من شات جي بي تي ==========
def chat_with_gpt(prompt):
    try:
        response = client1.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("⚠️ فشل الاتصال بـ GPT:", e)
        return "[EM]neutral[/EM][TEXT]حدث خطأ مؤقت، يرجى المحاولة لاحقًا.[/TEXT]"


# =============================(تحويل النص الى صوت)=================
def speakwithelevenlabs(answer, emotion, robot, stop_event):
    try:
        audio = client.generate(text=answer, voice="Alice", model="eleven_multilingual_v2")
        if stop_event.is_set():
            return
        def delayed_expression():
            time.sleep(0)
            robot.set_expression(emotion)

        threading.Thread(target=delayed_expression).start()
        play(audio)
    except Exception as e:
        print("⚠️ فشل تشغيل الصوت:", e)
    finally:
        robot.set_expression("neutral")


# ========== تحويل الصوت الى نص وارسال الاوامر لشات جي بي تي بعد تلقي الرد ==========
def recognize_from_microphone(robot, stop_event):
    # تهيئة إعدادات التعرف الصوتي من Azure
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    # تحديد لغة التعرف (العربية السعودية)
    speech_config.speech_recognition_language = "ar-SA"

    # تهيئة إعدادات الميكروفون
    audio_config = speechsdk.audio.AudioConfig(
        use_default_microphone=True,  # استخدام الميكروفون الافتراضي
    )

    # إنشاء كائن التعرف الصوتي
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    # متغير لتخزين نتيجة التعرف
    recognition_result = None

    # دالة رد نداء عند التعرف على الكلام
    def recognized_cb(evt):
        nonlocal recognition_result  # للوصول إلى المتغير الخارجي
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:  # إذا تم التعرف على كلام
            recognition_result = evt.result  # حفظ النتيجة

    # ربط دالة الرد بالحدث
    recognizer.recognized.connect(recognized_cb)
    # تغيير تعبير وجه الروبوت إلى "يستمع"
    robot.set_expression("listening")

    try:
        # بدء عملية التعرف المستمر
        recognizer.start_continuous_recognition()
        # حفظ وقت البدء لتحديد المدة القصوى
        start_time = time.time()

        # حلقة انتظار حتى يتم التعرف على الكلام أو الضغط على إيقاف
        while not stop_event.is_set() and recognition_result is None:
            if time.time() - start_time > 10:  # إذا تجاوزت المدة 10 ثواني
                break  # إنهاء الانتظار
            time.sleep(0.05)  # انتظار قصير لتقليل الحمل على المعالج

        # إيقاف التعرف بعد الخروج من الحلقة
        recognizer.stop_continuous_recognition()

        # إذا تم الضغط على إيقاف
        if stop_event.is_set():
            robot.set_expression("neutral")  # إعادة الوجه لوضعه الطبيعي
            return None  # إنهاء الدالة

        # إذا كانت هناك نتيجة تعرف
        if recognition_result:
            robot.set_expression("thinking")  # تغيير التعابير إلى "يفكر"
            # إرسال النص إلى ChatGPT
            response = chat_with_gpt(recognition_result.text)
            # تحليل الرد لفصل المشاعر عن النص
            parsed = emotion_split(response)
            # تحويل النص إلى صوت مع تعابير الوجه المناسبة
            speakwithelevenlabs(parsed["text"], parsed["emotion"], robot, stop_event)

    except Exception as e:
        # في حالة حدوث خطأ، طباعة الرسالة
        print(f"⚠️ خطأ: {e}")
    finally:
        # في النهاية، ضمان إعادة الروبوت للوضع الطبيعي
        robot.set_expression("neutral")
        # وإيقاف التعرف الصوتي نهائياً
        recognizer.stop_continuous_recognition()


# ========== التحكم بزر Space ==========
class Controller:
    def __init__(self, robot):
        self.listening = False
        self.robot = robot


    def toggle(self):
        try:
            if not self.listening:
                print("تشغيل الاستماع")
                stop_ad_sound()
                self.listening = True
                if hasattr(self, 'stop_event'):
                    self.stop_event.clear()
                else:
                    self.stop_event = threading.Event()
            
                # إيقاف أي ثريد قديم إن وجد
                if hasattr(self, 'listening_thread'):
                    self.listening_thread.join(timeout=0.1)
                
                self.listening_thread = threading.Thread(
                    target=self.listen_loop,
                    args=(self.stop_event,),
                    daemon=True
                )
                self.listening_thread.start()
            else:
                print("إيقاف مؤقت")
                self.listening = False
                self.stop_event.set()
        except Exception as e:
            print(f"Error in toggle: {e}")


    def listen_loop(self, stop_event):
        while not stop_event.is_set() and self.listening:
            recognize_from_microphone(self.robot, stop_event)
            time.sleep(1)  # تأخير بين المحاولات لتجنب الحمل الزائد

# ثريد مخصص لحساب ردات الفعل العشوائية
def expression_loop(main_controller, robot, co, stop_event):
    import random
    import time
    while not stop_event.is_set():
        if main_controller.current_program == "robot":
            if not co.listening:
                rndm_exprtion(robot)
        time.sleep(random.uniform(20, 30))


# ديفنشن مخصص لتنفيذ الحركات العشوائية
def rndm_exprtion(robot):
    global randnormal
    randnormal = random.randint(1, 3)
    print(randnormal)
    if randnormal == 1:
        robot.set_expression("neutral2")
        sounds_ads()
    elif randnormal == 2:
        robot.set_expression("neutral1")
    elif randnormal == 3:
        robot.set_expression("sleep")
    else:
        print("nothing")


# قسم تشغيل الاصوات العشوائية التسويقية عند الانتظار
def sounds_ads():
    global seqsounds

    filenames = {
        1: "1.mp3",
        2: "2.mp3",
        3: "3.mp3"
    }

    filename = filenames.get(seqsounds, "1.mp3")
    default_audio_path = Path("sounds") / filename

    if default_audio_path.exists():
        print(f"🔊 تشغيل الصوت {seqsounds}: {filename}")
        pygame.mixer.music.load(str(default_audio_path))
        pygame.mixer.music.play()
    else:
        print("⚠️ الملف الصوتي غير موجود:", default_audio_path)

    seqsounds += 1
    if seqsounds > 3:
        seqsounds = 1


# ========== دالة إيقاف الصوت التسويقي ==========
def stop_ad_sound():
    if pygame.mixer.music.get_busy():
        print("⏹️ إيقاف الصوت")
        pygame.mixer.music.stop()

def safe_exit():
    pygame.mixer.quit()

# ========== تشغيل البرنامج ==========
if __name__ == "__main__":
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", safe_exit)
    robot = AnimatedRobot(root, serial_port='/dev/ttyACM0')  # Pi-compatible port
    controller = Controller(robot)

    # Start expression loop in a thread
    stop_event = threading.Event()
    threading.Thread(target=expression_loop, args=(None, robot, controller, stop_event), daemon=True).start()


    # Start pynput keyboard listener
    def on_press(key):
        if key == Key.space:
            controller.toggle()


    keyboard_listener = Listener(on_press=on_press)
    keyboard_listener.daemon = True
    keyboard_listener.start()

    root.mainloop()
