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

# Database
MONGO_URI = get_secret("MONGODB_URI")

# Telegram
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")

# Email
EMAIL_ADDR = get_secret("EMAIL_ADDRESS")
EMAIL_PASS = get_secret("EMAIL_PASSWORD")

SMTP_HOST = get_secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(get_secret("SMTP_PORT", 587))
IMAP_HOST = get_secret("IMAP_HOST", "imap.gmail.com")


# ────────────────────────────────────────
# APP CONFIG
# ────────────────────────────────────────
APP_NAME = "ResumeAI Pro"
APP_VERSION = "2.0"

ENABLE_VOICE = True
ENABLE_VISION = True
ENABLE_MONGODB = True
ENABLE_TELEGRAM = True


# ────────────────────────────────────────
# STATUS CHECK
# ────────────────────────────────────────
def credential_status():
    return {
        "GROQ_API_KEY": (bool(GROQ_KEY), "Groq LLM access"),
        "MONGODB_URI": (bool(MONGO_URI), "MongoDB connection"),
        "TELEGRAM_BOT_TOKEN": (bool(TELEGRAM_BOT_TOKEN), "Telegram bot"),
        "EMAIL_ADDRESS": (bool(EMAIL_ADDR), "SMTP email"),
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
"""