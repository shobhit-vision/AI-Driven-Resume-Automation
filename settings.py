# Remove this commented block:
# from settings import (
#     GROQ_KEY, MONGO_URI, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
#     EMAIL_ADDR, EMAIL_PASS, SMTP_HOST, SMTP_PORT, IMAP_HOST,
#     MAIN_MODEL, VISION_MODEL, APP_NAME, APP_VERSION,
#     ENABLE_VOICE, ENABLE_VISION, ENABLE_MONGODB, ENABLE_TELEGRAM,
#     TELEGRAM_COMMANDS, credential_status, SECRETS_TEMPLATE, DEPENDENCIES,
# )

# Keep this section:
#credentials import 
# settings.py

import streamlit as st

# ────────────────────────────────────────
# SAFE GET FUNCTION
# ────────────────────────────────────────
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


# ────────────────────────────────────────
# LOAD ALL CREDENTIALS
# ────────────────────────────────────────

# AI / LLM
GROQ_KEY = get_secret("GROQ_API_KEY")
MAIN_MODEL = get_secret("MAIN_MODEL", "llama3-70b-8192")  # Add this
VISION_MODEL = get_secret("VISION_MODEL", "llava-v1.5-7b-4096-preview")  # Add this

# Database
MONGO_URI = get_secret("MONGODB_URI")

# Telegram
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")
TELEGRAM_COMMANDS = get_secret("TELEGRAM_COMMANDS", [  # Add this
    ("/start", "Start the bot"),
    ("/resume", "Get current resume"),
    ("/ats", "Get ATS analysis"),
    ("/job", "Get current job"),
    ("/help", "Show help"),
])

# Email
EMAIL_ADDR = get_secret("EMAIL_ADDRESS")
EMAIL_PASS = get_secret("EMAIL_PASSWORD")

SMTP_HOST = get_secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(get_secret("SMTP_PORT", 587))
IMAP_HOST = get_secret("IMAP_HOST", "imap.gmail.com")


# ────────────────────────────────────────
# APP CONFIG
# ────────────────────────────────────────
APP_NAME = get_secret("APP_NAME", "ResumeAI Pro")  # Add this
APP_VERSION = get_secret("APP_VERSION", "2.0")  # Add this

ENABLE_VOICE = get_secret("ENABLE_VOICE", True)  # Add this
ENABLE_VISION = get_secret("ENABLE_VISION", True)  # Add this
ENABLE_MONGODB = get_secret("ENABLE_MONGODB", True)  # Add this
ENABLE_TELEGRAM = get_secret("ENABLE_TELEGRAM", True)  # Add this


# ────────────────────────────────────────
# STATUS CHECK
# ────────────────────────────────────────
def credential_status():
    return {
        "GROQ_API_KEY": (bool(GROQ_KEY), "Groq LLM access"),
        "MONGODB_URI": (bool(MONGO_URI), "MongoDB connection"),
        "TELEGRAM_BOT_TOKEN": (bool(TELEGRAM_BOT_TOKEN), "Telegram bot"),
        "EMAIL_ADDRESS": (bool(EMAIL_ADDR), "SMTP email"),
        "MAIN_MODEL": (bool(MAIN_MODEL), "Primary LLM model"),
        "VISION_MODEL": (bool(VISION_MODEL), "Vision AI model"),
    }


# ────────────────────────────────────────
# TEMPLATE FOR USERS
# ────────────────────────────────────────
SECRETS_TEMPLATE = """
GROQ_API_KEY="gsk_..."
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
ENABLE_TELEGRAM=true
"""

# ── Model names ───────────────────────────────────────────────────────────────
MAIN_MODEL          = "llama-3.3-70b-versatile"
VISION_MODEL        = "llama-3.2-11b-vision-preview"

# ── App metadata ──────────────────────────────────────────────────────────────
APP_NAME            = "ResumeAI Pro"
APP_VERSION         = "2.0.0"
APP_ICON            = "🚀"

# ── Feature flags ─────────────────────────────────────────────────────────────
ENABLE_VOICE        = True   # Voice command input
ENABLE_VISION       = True   # Groq vision model features
ENABLE_MONGODB      = True   # MongoDB persistence
ENABLE_EMAIL        = True   # Email automation
ENABLE_TELEGRAM     = True   # Telegram bot

# ── Scraping / Job extraction ─────────────────────────────────────────────────
SCRAPE_TIMEOUT      = 20     # seconds
SCRAPE_MAX_LINES    = 400    # max lines of text to keep from scraped page
SCRAPE_MIN_LINE_LEN = 25     # minimum chars to keep a line

# ── ATS limits ────────────────────────────────────────────────────────────────
ATS_RESUME_CHARS    = 4000
ATS_JOB_CHARS = 2500


# ── Dependencies (shown in settings page) ─────────────────────────────────────
DEPENDENCIES = (
    "streamlit langchain langchain-groq langchain-community groq "
    "pymongo pdfplumber PyPDF2 python-docx requests beautifulsoup4 "
    "Pillow python-telegram-bot trafilatura SpeechRecognition pyaudio "
    "httpx lxml"
)
