import os
import json
import base64
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv, set_key

# ────────────────────────────────────────
# LOAD ENV FILE
# ────────────────────────────────────────
load_dotenv(".env")
ENV_FILE = ".env"


def reload_settings():
    """
    Reload environment variables from .env
    """
    load_dotenv(ENV_FILE, override=True)

    # Re-assign globals so app uses updated values
    global GROQ_KEY, MONGO_URI, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    global EMAIL_ADDR, EMAIL_PASS, MAIN_MODEL, VISION_MODEL

    GROQ_KEY = os.getenv("GROQ_API_KEY")
    MONGO_URI = os.getenv("MONGODB_URI")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    EMAIL_ADDR = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASS = os.getenv("EMAIL_PASSWORD")
    MAIN_MODEL = os.getenv("MAIN_MODEL", "llama3-70b-8192")
    VISION_MODEL = os.getenv("VISION_MODEL", "llava-v1.5-7b")


# ────────────────────────────────────────
# SAFE GET FUNCTION (3-LAYER)
# ────────────────────────────────────────
def get_secret(key, default=None):
    # 1️⃣ Try Streamlit secrets
    try:
        value = st.secrets[key]
        if value:
            return value
    except Exception:
        pass

    # 2️⃣ Try .env
    value = os.getenv(key)
    if value:
        return value

    # 3️⃣ Fallback
    return default


# ────────────────────────────────────────
# AUTO SAVE TO .ENV
# ────────────────────────────────────────
def save_to_env(key, value):
    if not os.path.exists(ENV_FILE):
        open(ENV_FILE, "w").close()

    set_key(ENV_FILE, key, str(value))


# ────────────────────────────────────────
# USER INPUT UI (AUTO CONFIG)
# ────────────────────────────────────────
def ask_user_for_missing_ui():

    status_map = credential_status()

    st.markdown("### ⚙️ Configure Credentials")

    inputs = {}

    # ─────────────────────────────
    # GROQ
    # ─────────────────────────────
    ok, _ = status_map["GROQ_API_KEY"]

    st.markdown(f"#### 🤖 Groq API {'✅' if ok else '❌'}")
    st.caption("Used for AI resume analysis")

    inputs["GROQ_API_KEY"] = st.text_input(
        "Groq API Key",
        value=GROQ_KEY or "",
        type="password",
        placeholder="gsk_..."
    )

    if not ok:
        st.link_button("🔑 Get Groq API Key", "https://console.groq.com/keys")

    st.markdown("---")

    # ─────────────────────────────
    # MONGODB
    # ─────────────────────────────
    ok, _ = status_map["MONGODB_URI"]

    st.markdown(f"#### 🗄️ MongoDB {'✅' if ok else '❌'}")
    st.caption("Stores resumes & ATS results")

    inputs["MONGODB_URI"] = st.text_input(
        "MongoDB URI",
        value=MONGO_URI or "",
        placeholder="mongodb+srv://..."
    )

    if not ok:
        st.link_button("🌐 Setup MongoDB", "https://www.mongodb.com/cloud/atlas/register")

    st.markdown("---")

    # ─────────────────────────────
    # TELEGRAM
    # ─────────────────────────────
    ok, _ = status_map["TELEGRAM_BOT_TOKEN"]

    st.markdown(f"#### 📱 Telegram Bot {'✅' if ok else '❌'}")
    st.caption("Automate resume via Telegram")

    inputs["TELEGRAM_BOT_TOKEN"] = st.text_input(
        "Bot Token",
        value=TELEGRAM_BOT_TOKEN or "",
        type="password"
    )

    inputs["TELEGRAM_CHAT_ID"] = st.text_input(
        "Chat ID",
        value=TELEGRAM_CHAT_ID or ""
    )

    with st.expander("📘 Setup Guide"):
        try:
            with open("tele_steps.txt") as f:
                st.code(f.read(), language="text")
        except:
            st.warning("tele_steps.txt not found")

    st.markdown("---")

    # ─────────────────────────────
    # EMAIL
    # ─────────────────────────────
    ok, _ = status_map["EMAIL_ADDRESS"]

    st.markdown(f"#### 📧 Email SMTP {'✅' if ok else '❌'}")
    st.caption("Send resumes via email")

    inputs["EMAIL_ADDRESS"] = st.text_input(
        "Email Address",
        value=EMAIL_ADDR or ""
    )

    inputs["EMAIL_PASSWORD"] = st.text_input(
        "App Password",
        value=EMAIL_PASS or "",
        type="password"
    )

    with st.expander("📘 Setup Guide"):
        try:
            with open("mail_steps.txt") as f:
                st.code(f.read(), language="text")
        except:
            st.warning("mail_steps.txt not found")

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────
    # SAVE BUTTON
    # ─────────────────────────────
    

    if st.button("💾 Save & Download Credentials", use_container_width=True):

        saved_data = {}

        for k, v in inputs.items():
            if v:
                save_to_env(k, v)
                saved_data[k] = v

        reload_settings()

        # Create downloadable JSON
        file_data = {
            "created_at": str(datetime.now()),
            "app": "ResumeAI Pro",
            "credentials": saved_data
        }

        json_str = json.dumps(file_data, indent=2)

        st.success("✅ Settings saved!")

        st.download_button(
            label="⬇️ Download Credentials File",
            data=json_str,
            file_name="resumeai_credentials.json",
            mime="application/json"
        )


# ────────────────────────────────────────
# LOAD ALL CREDENTIALS
# ────────────────────────────────────────
GROQ_KEY = get_secret("GROQ_API_KEY")
MONGO_URI = get_secret("MONGODB_URI")

TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")

EMAIL_ADDR = get_secret("EMAIL_ADDRESS")
EMAIL_PASS = get_secret("EMAIL_PASSWORD")

SMTP_HOST = get_secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(get_secret("SMTP_PORT", 587))
IMAP_HOST = get_secret("IMAP_HOST", "imap.gmail.com")

MAIN_MODEL = get_secret("MAIN_MODEL", "llama-3.3-70b-versatile")
VISION_MODEL = get_secret("VISION_MODEL", "llama-3.2-11b-vision-preview")

APP_NAME = get_secret("APP_NAME", "ResumeAI Pro")
APP_VERSION = get_secret("APP_VERSION", "2.0.0")

ENABLE_VOICE = get_secret("ENABLE_VOICE", True)
ENABLE_VISION = get_secret("ENABLE_VISION", True)
ENABLE_MONGODB = get_secret("ENABLE_MONGODB", True)
ENABLE_TELEGRAM = get_secret("ENABLE_TELEGRAM", True)


# ────────────────────────────────────────
# TELEGRAM COMMANDS
# ────────────────────────────────────────
TELEGRAM_COMMANDS = [
    ("/start", "Start bot"),
    ("/resume", "Get resume"),
    ("/ats", "ATS score"),
    ("/job", "Job info"),
    ("/help", "Help"),
]


# ────────────────────────────────────────
# VALIDATION CHECK
# ────────────────────────────────────────
def missing_credentials():
    required = {
        "GROQ_API_KEY": GROQ_KEY,
        "MONGODB_URI": MONGO_URI,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "EMAIL_ADDRESS": EMAIL_ADDR,
    }

    return [k for k, v in required.items() if not v]


# ────────────────────────────────────────
# AUTO INIT CHECK (CALL THIS IN APP START)
# ────────────────────────────────────────
def initialize_settings():
    missing = missing_credentials()

    if missing:
        ask_user_for_missing_ui()


# ────────────────────────────────────────
# STATUS CHECK
# ────────────────────────────────────────
def credential_status():
    return { 
        "GROQ_API_KEY": (bool(GROQ_KEY),"Groq LLM access"),
        "MONGODB_URI": (bool(MONGO_URI), "MongoDB connection"),
        "TELEGRAM_BOT_TOKEN": (bool(TELEGRAM_BOT_TOKEN),"Telegram bot"), 
        "EMAIL_ADDRESS": (bool(EMAIL_ADDR),"SMTP email"),
        "MAIN_MODEL": (bool(MAIN_MODEL),"Primary LLM model"),
        "VISION_MODEL": (bool(VISION_MODEL),"Vision AI model"),
        }

def render_import_credentials():

    st.markdown("### 📂 Import Credentials")
    st.caption("Upload your previously downloaded credentials file to auto-fill settings")

    uploaded_file = st.file_uploader(
        "Upload credentials file (.json)",
        type=["json"]
    )

    if uploaded_file:
        try:
            data = json.load(uploaded_file)

            # Validate structure
            if "credentials" not in data:
                st.error("❌ Invalid file format")
                return

            creds = data.get("credentials", {})

            if not creds:
                st.warning("⚠️ No credentials found in file")
                return

            # Show preview
            st.markdown("#### 🔍 Detected Credentials")
            for k in creds.keys():
                st.markdown(f"- `{k}`")

            if st.button("⚡ Apply Credentials", use_container_width=True):
                for k, v in creds.items():
                    save_to_env(k, v)

                    reload_settings()

                st.success("✅ Credentials imported successfully!")
                st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to read file: {e}")

# ────────────────────────────────────────
# TEMPLATE FOR USERS
SECRETS_TEMPLATE = """ GROQ_API_KEY="gsk_..." 
MONGODB_URI="mongodb+srv://..." 
TELEGRAM_BOT_TOKEN="..." 
EMAIL_ADDRESS="..." 
EMAIL_PASSWORD="..." 
MAIN_MODEL="llama3-70b-8192" 
VISION_MODEL="llava-v1.5-7b-4096-preview" 
APP_NAME="ResumeAI Pro" 
APP_VERSION="2.0" 
ENABLE_VOICE=true 
ENABLE_VISION=true 
ENABLE_MONGODB=true 
ENABLE_TELEGRAM=true """


# ── App metadata ────────────────────────────────────────────────────────────── 
APP_NAME = "ResumeAI Pro"
APP_VERSION = "2.0.0" 
APP_ICON = "🚀"


# ── Feature flags ───────────────────────────────────────────────────────────── 
ENABLE_VOICE = True # Voice command input 
ENABLE_VISION = True # Groq vision model features 
ENABLE_MONGODB = True # MongoDB persistence 
ENABLE_EMAIL = True # Email automation 
ENABLE_TELEGRAM = True # Telegram bot 

# ── Scraping / Job extraction ───────────────────────────────────────────────── 
SCRAPE_TIMEOUT = 20 # seconds 
SCRAPE_MAX_LINES = 400 # max lines of text to keep from scraped page 
SCRAPE_MIN_LINE_LEN = 25 # minimum chars to keep a line

# ── ATS limits ──────────────────────────────────────────────────────────────── 
ATS_RESUME_CHARS = 4000 
ATS_JOB_CHARS = 2500
