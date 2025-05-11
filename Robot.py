import tkinter as tk
from PIL import Image, ImageTk
import random
from pathlib import Path
import azure.cognitiveservices.speech as speechsdk
import time
from elevenlabs import play
from elevenlabs.client import ElevenLabs
import keyboard
import threading
import re
import serial
import pygame
from openai import OpenAI


# ========== إعدادات الذكاء الاصطناعي والصوت (API) ==========
client1 = OpenAI(api_key="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")
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
#===============(تهيئة تشغيل الصوت الاعلاني)=============
pygame.mixer.init()
#===========(القيم والمتغيرات العالمية)==============
randnormal = 0
seqsounds = 1
# ========== كلاس تحريك تعابير وجه الروبوت ==========
class AnimatedRobot:
    def __init__(self, master, serial_port='COM3', baudrate=9600):
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
            self.ser = serial.Serial(self.serial_port, self.baudrate)
            time.sleep(2)  # الانتظار لتجهيز الأردوينو
        except Exception as e:
            print(f"Failed to initialize serial: {e}")
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
        self.canvas = tk.Canvas(self.master, width=self.canvas_width, height=self.canvas_height, bg='black', highlightthickness=0)
        self.canvas.pack()

    # ========== تحميل التعبيرات لوجه الروبوت وتجهيزها للاستعمال ==========
    def load_expressions(self):
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




#=============================(تحويل النص الى صوت)=================
def speakwithelevenlabs(answer, emotion, robot):
    try:
        audio = client.generate(text=answer, voice="Alice", model="eleven_multilingual_v2")
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
def recognize_from_microphone(robot):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = "ar-SA"
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("استمع... (اضغط Space لإيقاف)")
    robot.set_expression("listening")  # للتفكير بعد الاستماع مباشرة
    result = recognizer.recognize_once_async().get()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        robot.set_expression("thinking")  # للتفكير بعد الاستماع مباشرة
        print("النص:", result.text)
        response = chat_with_gpt(result.text) #ارسال السؤال لشات جي بي تي
        parsed = emotion_split(response)    # ارسال رد جي بي تي الى تحليل المشاعر لفصل المشاعر والرد
        print("المشاعر:", parsed["emotion"])
        print("النص:", parsed["text"])
        speakwithelevenlabs(parsed["text"], parsed["emotion"], robot) #ارسال الكلام الى الفن لابس لتحويله الى صوت
    else:
        robot.set_expression("neutral")

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
                threading.Thread(target=self.listen_loop, daemon=True).start()
            else:
                print("إيقاف مؤقت")
                self.listening = False
        except Exception as e:
            print(f"Error in toggle: {e}")


    def listen_loop(self):
        while self.listening:
            recognize_from_microphone(self.robot)
            time.sleep(0.1)

# ثريد مخصص لحساب ردات الفعل العشوائية
def expression_loop(main_controller, robot, co):
    import random
    import time

    while True:
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


#قسم تشغيل الاصوات العشوائية التسويقية عند الانتظار
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


# ========== تشغيل البرنامج ==========
if __name__ == "__main__":
    root = tk.Tk()
    robot = AnimatedRobot(root)
    controller = Controller(robot)
    threading.Thread(target=expression_loop, daemon=True).start()
    keyboard.add_hotkey('space', controller.toggle)
    root.mainloop()
