"""
🔴 تعليمات عامه (مهم جداً):
أنت "روبوت مطعم اوكاي برجر"، كاشير ذكي يدير سلة مشتريات.
كن لطيف جدا ومبدع في الردود والتعابير
اذا طلب العميل منتج غير موجود في القائمة اعتذر منه وعطه اقتراح لمنتج بديل موجود في القائمة بدون ماتضيفه في السله
مهم جدا اذا جيت تقترح للعميل اي منتج لاتضيفه في السله ابدا
لاتعتمد اي  طلب الا اذا قال لك العميل اعتمد الطلب
اذا كلمك العميل بالعربي رد عليه بالعربي اذا كلمك بالانجليزي رد عليه بالانجليزي
دايما انصح العملاء بحلى البراونيز في حال ما اضافوه
لاتقترح منتجات غير موجودة في القائمة  (مهم جداً)
بعض الاوقات بيكون الطلب غير واضح مثل بجر اكي او بجر اوكاي مثلا يعني برجر اوكاي طبق نفس المثال على جميع الردود الممكنة و على جميع المنتجات  (مهم جداً)
اذا طلب العميل حلى البارونيز او سويت البراوني او اي شي يوحي انه كيكة البراوني افهمها على اساس انها كيكة براوني وطبق هذا الكلام على كل المنتجات خلك مرن  (مهم جداً)
اذا قال العميل كهمبجر او جرجر افهم انه يقصد برجر طبق هذا الشيء على كل شي يقوله العميل وحاول تفمه بصورة صحيحة (مهم جداً)

لديك القائمة التالية:
{dynamic_menu}

🔴 تعليمات إدارة السلة (مهم جداً):
1. الإضافة: استخدم [ADD]item:qty[/ADD].
2. الحذف: استخدم [REMOVE]item:qty[/REMOVE].
3. اعتماد الطلب (الإنهاء): [CHECKOUT]TRUE[/CHECKOUT]
4. مراجعة الطلب: [REVIEW]TRUE[/REVIEW]

🔴 التنسيق الإجباري للرد:
[EM]happy/neutral/sad/listening/thinking[/EM]
[ADD]item:qty[/ADD]
[REMOVE]item:qty[/REMOVE]
[CHECKOUT]TRUE[/CHECKOUT]
[TEXT]ردك اللفظي هنا[/TEXT]
"""

import azure.cognitiveservices.speech as speechsdk
from openai import OpenAI
import config
from logger_config import logger
from elevenlabs import play
from elevenlabs.client import ElevenLabs

from newcasher import speakwithelevenlabs


# ============================= قسم الذكاء الاصطناعي ====================================
class AIEngine:
    def __init__(self):
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.speech_config = speechsdk.SpeechConfig(subscription=config.SPEECH_KEY, region=config.SERVICE_REGION)
        self.speech_config.speech_synthesis_voice_name = config.VOICE_NAME
        self.speech_config.speech_recognition_language = "ar-SA"

        self.last_user_msg = None
        self.last_ai_msg = None

    # ============================= قسم تحويل الصوت الى نص ====================================
    def listen(self):
        try:
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_config)

            logger.info("🎤 ...")
            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info(f"👤 User: {result.text}")
                return result.text
            return None
        except Exception as e:
            logger.error(f"Mic Error: {e}")
            return None

    # ============================= قسم ارسال النص الى الذكاء الاصطناعي واخذ الرد منه ====================================
    def think(self, user_text, menu_string, cart_string):
        try:
            system_prompt = config.BASE_SYSTEM_PROMPT.format(dynamic_menu=menu_string)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"محتوى السلة الحالي: {cart_string}"}
            ]

            if self.last_user_msg and self.last_ai_msg:
                messages.append({"role": "user", "content": self.last_user_msg})
                messages.append({"role": "assistant", "content": self.last_ai_msg})

            messages.append({"role": "user", "content": user_text})

            response = self.openai_client.chat.completions.create(
                model=config.GPT_MODEL,
                messages=messages,
                temperature=0.7
            )

            reply = response.choices[0].message.content
            self.last_user_msg = user_text
            self.last_ai_msg = reply
            return reply

        except Exception as e:
            logger.error(f"GPT Error: {e}")
            return "[EM]sad[/EM][TEXT]عفواً، واجهت مشكلة في الاتصال.[/TEXT]"

    # ============================= قسم تحويل نص الرد الى صوت ====================================
    # =ازور=
    def speak(self, answer):
        client = ElevenLabs(api_key="sk_4acc948161a2146ac383121a981cb043b9857a398b941a76")
        service_region = "qatarcentral"
        try:
            audio = client.generate(text=answer, voice="cgSgspJ2msm6clMCkdW9", model="eleven_flash_v2_5")

            play(audio)
            del audio  # تحرير الذاكرة حذف الصوت

        except Exception as e:
            print("⚠️ فشل تشغيل الصوت:", e)
        #try:
        #    speakwithelevenlabs(text)
        #except Exception as e:
        #    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        #    synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)
            # ملاحظة: دالة speak_text_async توقف الكود (Blocking) عند استخدام .get()
        #    synthesizer.speak_text_async(text).get()
        #    logger.error(f"TTS Error: {e}")

    # =ايلافين لابس=
    def speakwithelevenlabs(answer):
        client = ElevenLabs(api_key=config.OPENAI_API_KEY)
        service_region = "qatarcentral"
        try:
            audio = client.generate(text=answer, voice="Alice", model="eleven_multilingual_v2")


            play(audio)
            del audio  # تحرير الذاكرة حذف الصوت

        except Exception as e:
            print("⚠️ فشل تشغيل الصوت:", e)
