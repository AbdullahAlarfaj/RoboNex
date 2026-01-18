import os
from dotenv import load_dotenv

#nna4acc948161a2146ac383121a981cb043b9857a398b941a76ann
#=== تحميل المفاتيح من ملف .env ===
load_dotenv()

# === OpenAI Settings ===
OPENAI_API_KEY = api_key= os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-4o"

# === Azure Speech Settings ===
SPEECH_KEY = os.getenv("SPEECH_KEY")
SERVICE_REGION = "qatarcentral"
VOICE_NAME = "ar-SA-HamedNeural"

# === Supabase Settings ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# === ElevenLabs Settings ===
ELEVENLABS_API = os.getenv("ELEVENLABS_API")
ELEVENLABS_REGION = os.getenv("ELEVENLABS_REGION")
ELEVENLABS_VOICE= os.getenv("ELEVENLABS_VOICE")


# === Hardware Settings ===
SERIAL_PORT = "COM3"
BAUDRATE = 9600

# === Paths ===
ASSETS_DIR = "robot_expressions"
