
import streamlit as st
from datetime import datetime
from bson import ObjectId
from resume import parse_resume_file as prf
import os, json, re, base64, time
import smtplib, imaplib
import email as email_module
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from io import BytesIO

# ─── Module Imports ──────────────────────────────────────────────────────────
from settings import (
    ask_user_for_missing_ui, render_import_credentials,   
    MONGO_URI, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    EMAIL_ADDR, EMAIL_PASS, SMTP_HOST, SMTP_PORT, IMAP_HOST,
    MAIN_MODEL, VISION_MODEL, APP_NAME, APP_VERSION,
    ENABLE_VOICE, ENABLE_VISION, ENABLE_MONGODB, ENABLE_TELEGRAM,
)

from resume import (
    parse_resume_file,parse_resume_with_llm,clean_text, groq_chat, groq_vision,
    compute_ats, optimize_resume, generate_new_resume,
    generate_cover_letter, improve_linkedin,
    analyze_vision, compare_resumes_vision,
    build_resume_agent, format_ats_telegram, resume_email_html,
)
from jobs import (
    extract_job_from_url, extract_job_from_text, extract_job_from_file,
    extract_job_details,
)

# ─── Optional library flags ───────────────────────────────────────────────────
try:
    from pymongo import MongoClient; from bson import ObjectId; MONGO_OK = True
except: MONGO_OK = False
try:
    from groq import Groq; GROQ_OK = True
except: GROQ_OK = False
try:
    from PIL import Image; PIL_OK = True
except: PIL_OK = False
try:
    import speech_recognition as sr; SR_OK = True
except: SR_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION & OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="ResumeAI Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/yourusername/resumeai-pro",
        "About": "ResumeAI Pro v2.2 - AI Resume Automation Platform"
    }
)

# ═══════════════════════════════════════════════════════════════════════════════
# PREMIUM CSS STYLING
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Sohne:wght@300;400;500;600;700&display=swap');

:root {
  --bg-primary: #080c17;
  --bg-secondary: #0f1622;
  --bg-tertiary: #1a202c;
  
  --accent-primary: #00d9ff;
  --accent-secondary: #a78bfa;
  --accent-tertiary: #f97316;
  
  --text-primary: #f5f7fa;
  --text-secondary: #cbd5e1;
  --text-muted: #94a3b8;
  
  --border-color: rgba(255,255,255,0.06);
  --border-light: rgba(255,255,255,0.12);
  
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-full: 999px;
  
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.2);
  --shadow-md: 0 8px 24px rgba(0,0,0,0.3);
  --shadow-lg: 0 16px 48px rgba(0,0,0,0.4);
  
  --transition-fast: 0.15s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.5s ease;
}

html, body, [data-testid="stAppViewContainer"] {
  background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
  font-family: 'Sohne', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--text-primary);
  overflow-x: hidden;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(255,255,255,0.02);
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--accent-primary), var(--accent-secondary));
  border-radius: var(--radius-full);
  transition: background var(--transition-normal);
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, var(--accent-secondary), var(--accent-primary));
}

.main .block-container {
  max-width: 1400px;
  padding: 2.5rem 2rem !important;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  letter-spacing: -0.5px;
}

h1 { font-size: 2.5rem; line-height: 1.2; }
h2 { font-size: 1.875rem; line-height: 1.3; }
h3 { font-size: 1.5rem; line-height: 1.4; }

.hero-title {
  font-size: 3rem;
  font-weight: 800;
  font-family: 'Space Grotesk', sans-serif;
  background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 50%, var(--accent-tertiary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: fadeInDown 0.6s ease-out;
  letter-spacing: -1px;
}

.hero-sub {
  color: var(--text-secondary);
  font-size: 1.1rem;
  margin-bottom: 2rem;
  font-weight: 400;
  animation: fadeInUp 0.6s ease-out 0.1s backwards;
}

.section-header {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 2rem 0 1.5rem 0;
  padding-left: 12px;
  border-left: 4px solid var(--accent-primary);
  display: flex;
  align-items: center;
  gap: 12px;
}

.ai-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  backdrop-filter: blur(10px);
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.ai-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.ai-card:hover {
  border-color: var(--accent-primary);
  background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
  box-shadow: 0 8px 32px rgba(0, 217, 255, 0.1);
  transform: translateY(-2px);
}

.ai-card:hover::before {
  opacity: 1;
}

/* JOB SELECTION CARD - IMPROVED */
.job-selection-card {
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.08) 0%, rgba(167, 139, 250, 0.04) 100%);
  border: 2px solid var(--accent-primary);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin: 1rem 0;
  transition: all var(--transition-normal);
  box-shadow: 0 0 20px rgba(0, 217, 255, 0.15);
}

.job-selection-card:hover {
  box-shadow: 0 0 30px rgba(0, 217, 255, 0.25);
  transform: translateX(4px);
}

.job-selected-badge {
  background: linear-gradient(135deg, var(--success) 0%, var(--accent-primary) 100%);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  display: inline-block;
  margin-left: 8px;
}

.metric-card {
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.08) 0%, rgba(167, 139, 250, 0.05) 100%);
  border: 1px solid rgba(0, 217, 255, 0.2);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  text-align: center;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.metric-card::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(0, 217, 255, 0.1) 0%, transparent 70%);
  pointer-events: none;
}

.metric-card:hover {
  border-color: var(--accent-primary);
  transform: scale(1.03);
  box-shadow: 0 8px 32px rgba(0, 217, 255, 0.15);
}

.metric-val {
  font-size: 1.75rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.metric-lbl {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
  font-weight: 500;
}

.stButton > button {
  border-radius: var(--radius-md) !important;
  background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%) !important;
  color: var(--bg-primary) !important;
  border: none !important;
  font-weight: 600 !important;
  font-family: 'Space Grotesk', sans-serif !important;
  padding: 0.75rem 1.5rem !important;
  font-size: 0.95rem !important;
  letter-spacing: 0.5px !important;
  transition: all var(--transition-normal) !important;
  box-shadow: 0 4px 16px rgba(0, 217, 255, 0.2) !important;
  position: relative;
  overflow: hidden;
}

.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(0, 217, 255, 0.3) !important;
}

.stButton > button:active {
  transform: translateY(0) !important;
}

.stTextInput input,
.stTextArea textarea,
.stSelectbox select {
  background: var(--bg-tertiary) !important;
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-primary) !important;
  font-family: 'Sohne', sans-serif !important;
  padding: 0.75rem 1rem !important;
  transition: all var(--transition-normal) !important;
  font-size: 0.95rem !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
  color: var(--text-muted) !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stSelectbox select:focus {
  border-color: var(--accent-primary) !important;
  box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1) !important;
  background: var(--bg-tertiary) !important;
}

.pill {
  display: inline-block;
  padding: 0.35rem 0.9rem;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 600;
  margin: 0.25rem;
  backdrop-filter: blur(10px);
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.pill:hover {
  transform: scale(1.05);
}

.pill-green {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.3);
}

.pill-red {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}

.pill-blue {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.3);
}

.pill-amber {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.3);
}

.pill-cyan {
  background: rgba(0, 217, 255, 0.15);
  color: var(--accent-primary);
  border-color: rgba(0, 217, 255, 0.3);
}

.score-ring {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 28px;
  background: conic-gradient(
    var(--accent-primary) calc(var(--pct)*1%),
    rgba(255,255,255,0.05) 0
  );
  box-shadow: 0 0 40px rgba(0, 217, 255, 0.2), inset 0 0 40px rgba(0, 217, 255, 0.1);
  position: relative;
  animation: scoreRingPulse 2s ease-in-out infinite;
}

.score-ring::before {
  content: '';
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: var(--bg-primary);
  z-index: -1;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
  border-right: 1px solid var(--border-color);
}

.sidebar-logo {
  font-size: 1.5rem;
  font-weight: 800;
  font-family: 'Space Grotesk', sans-serif;
  margin: 1.5rem 0 2rem 0;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.5px;
}

.stSidebar .stButton > button {
  margin: 0.5rem 0 !important;
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.1) 0%, rgba(167, 139, 250, 0.05) 100%) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-color) !important;
  box-shadow: none !important;
  font-weight: 500 !important;
}

.stSidebar .stButton > button:hover {
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.2) 0%, rgba(167, 139, 250, 0.1) 100%) !important;
  border-color: var(--accent-primary) !important;
  box-shadow: 0 4px 16px rgba(0, 217, 255, 0.1) !important;
}

.resume-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin: 0.75rem 0;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.resume-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.05) 0%, transparent 100%);
  opacity: 0;
  transition: opacity var(--transition-normal);
  pointer-events: none;
}

.resume-card:hover {
  transform: translateX(4px);
  border-color: var(--accent-primary);
  box-shadow: 0 8px 32px rgba(0, 217, 255, 0.1);
}

.resume-card:hover::before {
  opacity: 1;
}

.resume-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent-primary);
  margin-bottom: 0.5rem;
  font-family: 'Space Grotesk', sans-serif;
}

.resume-meta {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
  line-height: 1.6;
}

.resume-preview {
  background: rgba(0,0,0,0.3);
  border-radius: var(--radius-md);
  padding: 1rem;
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  max-height: 300px;
  overflow-y: auto;
  color: var(--text-secondary);
  line-height: 1.4;
}

.job-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin: 0.75rem 0;
  transition: all var(--transition-normal);
}

.job-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 8px 32px rgba(0, 217, 255, 0.1);
  transform: translateY(-2px);
}

.job-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--accent-primary);
  margin-bottom: 0.5rem;
  font-family: 'Space Grotesk', sans-serif;
}

.job-meta {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.6;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.05) 0%, rgba(167, 139, 250, 0.02) 100%);
  border: 2px dashed var(--border-light);
  border-radius: var(--radius-lg);
  margin: 2rem 0;
  color: var(--text-muted);
}

.empty-state-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes scoreRingPulse {
  0%, 100% {
    box-shadow: 0 0 40px rgba(0, 217, 255, 0.2), inset 0 0 40px rgba(0, 217, 255, 0.1);
  }
  50% {
    box-shadow: 0 0 60px rgba(0, 217, 255, 0.3), inset 0 0 60px rgba(0, 217, 255, 0.15);
  }
}

@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.skeleton {
  background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
  background-size: 1000px 100%;
  animation: shimmer 2s infinite;
}

[data-baseweb="tab-list"] {
  gap: 12px !important;
  border-bottom: 1px solid var(--border-color) !important;
}

[data-baseweb="tab"] {
  border-radius: var(--radius-md) !important;
  padding: 0.75rem 1.25rem !important;
  font-weight: 500 !important;
  transition: all var(--transition-normal) !important;
  background: transparent !important;
  color: var(--text-muted) !important;
}

[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, rgba(0, 217, 255, 0.1) 0%, rgba(167, 139, 250, 0.05) 100%) !important;
  color: var(--accent-primary) !important;
  border-bottom-color: var(--accent-primary) !important;
}

#MainMenu {
  visibility: hidden;
}

footer {
  visibility: hidden;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
  }
  
  .section-header {
    font-size: 1.25rem;
  }
  
  .main .block-container {
    padding: 1.5rem 1rem !important;
  }
}

/* Hide entire header */
[data-testid="stHeader"] {
    display: none;
}

/* Optional: remove top padding gap */
.block-container {
    padding-top: 1rem;
}

</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE - IMPROVED WITH BETTER JOB MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULTS = {
    "page": "dashboard",
    "resume_text": "",
    "resume_name": "",
    "resume_id": None,
    "job_text": "",
    "job_title": "",
    "job_id": None,  # ✅ NEW: Track job ID
    "job_details": {},  # ✅ NEW: Store full job details
    "jobs_history": [],
    "selected_jobs": [],  # ✅ NEW: For comparison feature
    "ats_result": None,
    "optimized_resume": "",
    "notifications": [],
    "template_text": "",
    "chat_history": [],
    "voice_input": "",
    "sidebar_state": "expanded",
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════════════════════
# CACHING
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_steps_cached(file):
    """Cache file loading for 1 hour"""
    try:
        with open(file, "r") as f:
            return f.read()
    except:
        return "⚠️ Steps file not found."

# ═══════════════════════════════════════════════════════════════════════════════
# MONGODB DATABASE - IMPROVED
# ═══════════════════════════════════════════════════════════════════════════════

class DB:
    _client = None
    _db = None

    @classmethod
    def get(cls):
        if not (MONGO_OK and MONGO_URI and ENABLE_MONGODB):
            return None
        if cls._client is None:
            try:
                cls._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
                cls._client.server_info()
                cls._db = cls._client["resumeai_pro"]
            except Exception as e:
                st.toast(f"MongoDB: {e}", icon="⚠️")
                return None
        return cls._db


    @classmethod
    def upsert_resume(cls, name, text, structured=None, meta=None):
        db = cls.get()
        if db is None:
            return None

        query = {
            "name": name,
            "meta.filename": meta.get("filename") if meta else None
        }

        update = {
            "$set": {
                "text": text,
                "structured": structured or {},
                "meta": meta or {},
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        }

        result = db["resumes"].update_one(query, update, upsert=True)

        if result.upserted_id:
            return str(result.upserted_id)

        # If updated existing, fetch ID
        existing = db["resumes"].find_one(query)
        return str(existing["_id"]) if existing else None

    @classmethod
    def delete_resume(cls, resume_id):
        db = cls.get()
        if db is None:
            return False

        try:
            obj_id = ObjectId(str(resume_id))  # 🔥 force string conversion

            result = db["resumes"].delete_one({"_id": obj_id})

            return result.deleted_count > 0

        except Exception as e:
            print("Delete error:", e)
            return False
    

    @classmethod
    def save_optimized_resume(cls, name, text, meta=None):
        db = cls.get()
        if db is None: return None
        doc = {
            "name": name, 
            "text": text, 
            "meta": meta or {}, 
            "type": "optimized",
            "created_at": datetime.utcnow()
        }
        return str(db["resumes"].insert_one(doc).inserted_id)


    @classmethod
    def list_resumes(cls):
        db = cls.get()
        if db is None:
            return []
        return list(db["resumes"].find({}, {"text": 0}).sort("created_at", -1).limit(50))
    
    @classmethod
    def get_resume(cls, rid):
        db = cls.get()
        if db is None:
            return None
        try:
            return db["resumes"].find_one({"_id": ObjectId(str(rid))})
        except Exception as e:
            print("Get error:", e)
            return None

    @classmethod
    def save_job_limited(cls, title, text, details, source="manual", meta=None):
        db = cls.get()
        if db is None: return None
        collection = db["jobs"]
        count = collection.count_documents({})
        if count >= 3:
            oldest = collection.find().sort("created_at", 1).limit(1)
            for doc in oldest:
                collection.delete_one({"_id": doc["_id"]})
        doc = {
            "title": title,
            "text": text,
            "details": details,
            "source": source,
            "meta": meta or {},
            "created_at": datetime.utcnow()
        }
        return str(collection.insert_one(doc).inserted_id)

    @classmethod
    @st.cache_data(ttl=300)
    def list_jobs(cls):
        db = cls.get()
        if db is None: return []
        return list(db["jobs"].find({}, {"text": 0}).sort("created_at", -1))

    @classmethod
    def get_job(cls, jid):
        """✅ FIXED: Get complete job with text field"""
        db = cls.get()
        if db is None: return None
        try:
            return db["jobs"].find_one({"_id": ObjectId(jid)})
        except:
            return None

    @classmethod
    def delete_job(cls, jid):
        db = cls.get()
        if db is None: return
        try:
            db["jobs"].delete_one({"_id": ObjectId(jid)})
        except:
            pass

    @classmethod
    def save_ats(cls, resume_id, job_id, score, result):
        db = cls.get()
        if db is None: return None
        db["ats_results"].insert_one({"resume_id": resume_id, "job_id": job_id, "score": score, "result": result, "created_at": datetime.utcnow()})

    @classmethod
    @st.cache_data(ttl=600)
    def recent_ats(cls, limit=10):
        db = cls.get()
        if db is None: return []
        return list(db["ats_results"].find().sort("created_at", -1).limit(limit))

# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def send_email(to_addr, subject, body, attachment_bytes=None, attachment_name=None):
    if not (EMAIL_ADDR and EMAIL_PASS):
        st.error("📧 Email credentials not configured."); return False
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDR
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        if attachment_bytes and attachment_name:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{attachment_name}"')
            msg.attach(part)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as srv:
            srv.ehlo(); srv.starttls(); srv.login(EMAIL_ADDR, EMAIL_PASS)
            srv.sendmail(EMAIL_ADDR, to_addr, msg.as_string())
        return True
    except Exception as e:
        st.error(f"📧 Email send failed: {e}"); return False

# ═══════════════════════════════════════════════════════════════════════════════
# UI HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def render_metric_card(value, label, icon="📊"):
    """Render an optimized metric card"""
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">{icon}</div>
        <div class="metric-val">{value}</div>
        <div class="metric-lbl">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def render_status_indicator(label, ok):
    """Render status indicator with dot"""
    color = "var(--success)" if ok else "var(--danger)"
    return f'<span style="display:inline-flex;align-items:center;gap:8px;color:var(--text-secondary)"><span style="width:8px;height:8px;border-radius:50%;background:{color};box-shadow:0 0 8px {color}"></span>{label}</span>'

def render_pill(text, color="cyan"):
    """Render optimized pill badge"""
    return f'<span class="pill pill-{color}">{text}</span>'

def render_score_ring(score):
    """Render animated score ring with gradient"""
    score_val = min(100, max(0, score))
    st.markdown(f"""
    <div style="display:flex;justify-content:center;align-items:center;padding:2rem 0">
        <div class="score-ring" style="--pct:{score_val}; color: var(--accent-primary); font-family: 'Space Grotesk', sans-serif;">
            {int(score_val)}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_divider():
    """Render elegant divider"""
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,var(--border-light),transparent);margin:1.5rem 0"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def page_dashboard():
    import settings
    
    st.markdown('<div class="hero-title">🚀 ResumeAI Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">AI-Powered Resume Automation & ATS Optimization Platform</div>', unsafe_allow_html=True)
    render_divider()

    mail_steps = load_steps_cached("mail_steps.txt")
    tele_steps = load_steps_cached("tele_steps.txt")

    GROQ_OK = bool(settings.GROQ_KEY)
    MONGO_OK = bool(settings.MONGO_URI)

    st.markdown("### 🔧 System Status")
    
    checks = [
        ("🤖 Groq LLM", GROQ_OK),
        ("🗄️ MongoDB", MONGO_OK),
        ("📱 Telegram", bool(settings.TELEGRAM_BOT_TOKEN)),
        ("📧 Email SMTP", bool(settings.EMAIL_ADDR and settings.EMAIL_PASS)),
    ]

    cols = st.columns(4)
    for col, (lbl, ok) in zip(cols, checks):
        with col:
            st.markdown(
                f'<div class="metric-card">{render_status_indicator(lbl, ok)}</div>',
                unsafe_allow_html=True
            )

    if not settings.GROQ_KEY:
        st.error("🤖 Groq API Key not configured!")
        st.markdown("👉 Please set it in **Settings Page**.")
        st.link_button("🔑 Get Groq API Key", "https://console.groq.com/keys", use_container_width=True)

    if not settings.MONGO_URI:
        st.error("🗄️ MongoDB URI not configured!")
        st.markdown("👉 Please set it in **Settings Page**.")
        st.link_button("🌐 Get MongoDB Atlas URI", "https://www.mongodb.com/cloud/atlas/register", use_container_width=True)

    render_divider()

    st.markdown("### 📊 Dashboard Statistics")
    db = DB.get()
    total_resumes = total_ats = avg_score = 0

    if db is not None:
        total_resumes = db["resumes"].count_documents({})
        ats_docs = list(db["ats_results"].find({}, {"score": 1}))
        total_ats = len(ats_docs)
        avg_score = int(sum(d.get("score", 0) for d in ats_docs) / max(total_ats, 1))

    stat_cols = st.columns(4)
    for col, (val, lbl, icon) in zip(stat_cols, [
        (total_resumes, "Resumes Stored", "📄"),
        (total_ats, "ATS Analyses", "📊"),
        (avg_score, "Avg ATS Score", "⭐"),
        ("∞", "Optimizations", "✨"),
    ]):
        with col:
            render_metric_card(val, lbl, icon)

    if total_ats > 0:
        render_divider()
        st.markdown("### 📊 Recent ATS Results")

        for r in DB.recent_ats(5):
            sc = r.get("score", 0)
            v = r.get("result", {}).get("verdict", "—") if isinstance(r.get("result"), dict) else "—"
            color = "green" if sc >= 80 else "amber" if sc >= 55 else "red"

            st.markdown(f"""
            <div class="ai-card" style="display:flex;align-items:center;gap:16px;justify-content:space-between">
                <div style="display:flex;align-items:center;gap:12px">
                    <span class="pill pill-{color}" style="font-size:0.9rem;padding:0.5rem 1rem">{sc}/100</span>
                    <span style="font-weight:600">{v}</span>
                </div>
                <span style="color:var(--text-muted);font-size:.85rem">{str(r.get("created_at",""))[:19]}</span>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — RESUME MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

def page_resume():
    st.markdown('<div class="hero-title">📄 Resume Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Upload, analyze, and manage your professional resumes</div>', unsafe_allow_html=True)
    render_divider()

    st.markdown("### 🗄️ Your Resumes")
    
    resumes = DB.list_resumes()
        
    if not resumes:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">No resumes yet</div>
            <div>Upload your first resume below to get started</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        resume_map = {str(r["_id"]): r for r in resumes}
        cols = st.columns(2)
        for idx, resume in enumerate(resumes):
            with cols[idx % 2]:
                resume_id = str(resume["_id"])
                created_date = str(resume.get("created_at", ""))[:10] if resume.get("created_at") else "Unknown"
                structured = resume.get("structured", {})
                real_name = structured.get("name") if isinstance(structured, dict) else None
                display_name = real_name if real_name else "Unnamed Candidate"
                file_name = resume.get("name", "Unnamed File")
                st.markdown(f"""
                <div class="resume-card">
                    <div class="resume-name">📄 {display_name}</div>
                    <div class="resume-meta">
                        📅 {created_date}<br>
                    📁 {file_name}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✅ Use", key=f"use_resume_{resume_id}", use_container_width=True):
                        full =  DB.get_resume(resume_id) 
                        text = full.get("text", "")
                        if full:
                            st.session_state.resume_text = full["text"]
                            st.session_state.resume_name = full["name"]
                            st.session_state.resume_id = resume_id
                            st.success(f"✅ Loaded: {full['name']}")
                            st.rerun()
                
                with col2:
                    if st.button("👁️ Preview", key=f"preview_resume_{resume_id}", use_container_width=True):
                        st.session_state[f"show_preview_{resume_id}"] = True

                # 🔥 SHOW PREVIEW PANEL
                if st.session_state.get(f"show_preview_{resume_id}", False):

                    full = resume_map.get(resume_id)

                    if full:
                        structured = full.get("structured", {})
                        text = full.get("text", "")

                        with st.container():
                            # 🔝 HEADER WITH CLOSE BUTTON
                            colA, colB = st.columns([8, 1])
                            with colA:
                                st.markdown(f"### 📄 {full['name']}")
                            with colB:
                                if st.button("❌", key=f"close_preview_{resume_id}"):
                                    st.session_state[f"show_preview_{resume_id}"] = False
                                    st.rerun()

                            st.markdown("---")

                            # 🔥 BEAUTIFUL SCROLLABLE BOX
                            st.markdown("""
                            <style>
                            .resume-box {
                                max-height: 400px;
                                overflow-y: auto;
                                padding: 15px;
                                border-radius: 10px;
                                background-color: #0e1117;
                                border: 1px solid #333;
                                font-size: 14px;
                                line-height: 1.6;
                            }
                            .section-title {
                                font-weight: 600;
                                margin-top: 10px;
                                color: #4CAF50;
                            }
                            </style>
                            """, unsafe_allow_html=True)

                            # 🔥 STRUCTURED VIEW (if exists)
                            if structured and isinstance(structured, dict) and "error" not in structured:

                                html = '<div class="resume-box">'

                                def add_section(title, content):
                                    if content:
                                        return f'<div class="section-title">{title}</div><div>{content}</div>'
                                    return ""

                                html += add_section("👤 Name", structured.get("name"))
                                html += add_section("📧 Email", structured.get("email"))
                                html += add_section("📱 Phone", structured.get("phone"))
                                html += add_section("📍 Address", structured.get("address"))
                                html += add_section("🧾 Summary", structured.get("summary"))

                                # 🔥 Skills (special handling)
                                skills = structured.get("skills", {})
                                if skills:
                                    html += '<div class="section-title">🛠 Skills</div>'
                                    for k, v in skills.items():
                                        if v:
                                            html += f"<div><b>{k.replace('_',' ').title()}:</b> {', '.join(v)}</div>"

                                html += add_section("💼 Experience", structured.get("experience"))
                                html += add_section("🚀 Projects", structured.get("projects"))
                                html += add_section("🎓 Education", structured.get("education"))
                                html += add_section("📜 Certifications", structured.get("certifications"))

                                html += '</div>'

                                st.markdown(html, unsafe_allow_html=True)

                            else:
                                # 📄 FALLBACK RAW TEXT
                                st.markdown(f"""
                                <div class="resume-box">
                                    {text[:2000]}...
                                </div>
                                """, unsafe_allow_html=True)

                with col3:
                    if st.button("🗑️ Delete", key=f"delete_resume_{resume_id}", use_container_width=True):
                        st.session_state.pop(f"show_preview_{resume_id}", None)
                        success = DB.delete_resume(resume_id)

                        if success:
                            st.success("🗑️ Resume deleted successfully")

                            # 🔥 CLEAR CACHE (CRITICAL)
                            st.cache_data.clear()

                            # 🔥 CLEAR SESSION IF ACTIVE
                            if st.session_state.get("resume_id") == resume_id:
                                st.session_state.resume_text = ""
                                st.session_state.resume_name = ""
                                st.session_state.resume_id = None

                            st.rerun()

                        else:
                            st.error("❌ Failed to delete resume")
                st.divider()

    if st.session_state.get("resume_text") and st.session_state.get("resume_name"):
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(16,185,129,0.1) 0%, rgba(16,185,129,0.05) 100%); border-left: 4px solid var(--success); padding: 1rem; border-radius: 8px; margin: 1.5rem 0;">
            <strong>✅ Active Resume:</strong> {st.session_state.get('resume_name', 'Loaded Resume')}<br>
            <span style="color: var(--text-muted); font-size: 0.9rem;">📝 {len(st.session_state.resume_text):,} characters loaded</span>
        </div>
        """, unsafe_allow_html=True)

    render_divider()

    tab1, tab2, tab3 = st.tabs(["⬆️ Upload File", "📋 Paste Text", "👁️ Vision Analyze"])

    with tab1:
        st.markdown("#### 📁 Upload Resume File")
        st.markdown("Supported: PDF, DOCX, TXT")
        
        uf = st.file_uploader("Choose file", type=["pdf","docx","txt"], label_visibility="collapsed")

        # ✅ TRACK FILE STATE (CRITICAL FIX)
        if "last_uploaded_file" not in st.session_state:
            st.session_state.last_uploaded_file = None

        # 🔥 FILE REMOVED → HARD RESET
        if uf is None and st.session_state.last_uploaded_file is not None:
            st.session_state.resume_text = ""
            st.session_state.resume_name = ""
            st.session_state.resume_id = None
            st.session_state.pop("resume_structured", None)
            st.session_state.last_uploaded_file = None
            st.rerun()

        # 🔥 NEW FILE UPLOADED → RESET OLD STRUCTURE
        if uf is not None:
            if st.session_state.last_uploaded_file != uf.name:
                st.session_state.pop("resume_structured", None)
            st.session_state.last_uploaded_file = uf.name

        if uf and "parsed_text" not in st.session_state:
            with st.spinner("📄 Parsing document..."):
                raw_text = parse_resume_file(uf)

            if raw_text and not raw_text.startswith("[Error"):
                text = clean_text(raw_text)
                st.session_state.parsed_text = text
                st.session_state.resume_text = text
                st.session_state.resume_name = uf.name

            if raw_text and not raw_text.startswith("[Error"):

                # 🔥 CLEAN TEXT
                text = clean_text(raw_text)

                st.session_state.resume_text = text
                st.session_state.resume_name = uf.name

                # 📊 METRICS
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Characters", f"{len(text):,}")
                with col2:
                    st.metric("Words", f"{len(text.split()):,}")
                with col3:
                    st.metric("Format", uf.name.split('.')[-1].upper())

                st.success(f"✅ Successfully parsed **{uf.name}**")

                # 📄 RAW PREVIEW
                with st.expander("📄 Raw Preview", expanded=False):
                    st.markdown(f"""
                    <div class="resume-preview">
                        {text[:1500]}
                    </div>
                    """, unsafe_allow_html=True)

                # 🔥 LLM STRUCTURING BUTTON
                if st.button("🧠 Generate Structured Resume", use_container_width=True):
                    with st.spinner("🧠 AI is structuring your resume..."):
                        try:
                            structured = parse_resume_with_llm(text)

                            # 🔥 FORCE DICT FORMAT
                            if not isinstance(structured, dict):
                                structured = {"raw_output": str(structured)}

                        except Exception as e:
                            structured = {"error": str(e)}

                    st.session_state.resume_structured = structured

                    if "error" not in structured:
                        st.success("✅ Resume structured successfully!")
                    else:
                        st.warning(f"⚠️ Issue: {structured.get('error')}")


                # 🧠 SHOW STRUCTURED OUTPUT
                if "resume_structured" in st.session_state:
                    st.markdown("### 🧠 Structured Resume")
                    st.json(st.session_state.resume_structured)


                # ✅ ONLY SHOW SAVE AFTER SUCCESSFUL STRUCTURING
                if (
                    "resume_structured" in st.session_state 
                    and isinstance(st.session_state.resume_structured, dict)
                    and len(st.session_state.resume_structured) > 0
                ):

                    st.markdown("#### 💾 Save Resume")

                    name_inp = st.text_input(
                        "Resume name", 
                        value=uf.name, 
                        key="save_name_upload"
                    )

                    if st.button("💾 Save to Database", type="primary", use_container_width=True):

                        structured_data = st.session_state.get("resume_structured", {})

                        rid = DB.upsert_resume(
                            name=name_inp,
                            text=text,
                            structured=structured_data,
                            meta={
                                "source": "upload",
                                "filename": uf.name
                            }
                        )

                        if rid:
                            st.session_state.resume_id = rid
                            st.success(f"✅ Saved successfully! ID: `{rid}`")

                            st.toast("🧠 Structured resume saved!", icon="✅")
                            st.balloons()
                        else:
                            st.warning("⚠️ MongoDB not connected — loaded in session only.")

        # 🔥 FIX: Clear state when file removed
        if not uf:
            st.session_state.pop("resume_text", None)
            st.session_state.pop("resume_name", None)
            st.session_state.pop("resume_structured", None)

    with tab2:
        st.markdown("#### 📋 Paste Resume Text")
        
        pasted = st.text_area(
            "Resume content", 
            height=350,
            
            placeholder="Paste your complete resume...",
            label_visibility="collapsed"
        )
        
        name_p = st.text_input("Resume name", value="My Resume", key="resume_name_paste")

        # 🔥 RESET STRUCTURED IF TEXT CHANGES
        if "last_pasted_text" not in st.session_state:
            st.session_state.last_pasted_text = ""

        if pasted != st.session_state.last_pasted_text:
            st.session_state.pop("resume_structured_paste", None)
            st.session_state.last_pasted_text = pasted

        # ✅ ONLY CONTINUE IF TEXT EXISTS
        if pasted.strip():

            text = clean_text(pasted)

            # 📊 METRICS (same as upload)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Characters", f"{len(text):,}")
            with col2:
                st.metric("Words", f"{len(text.split()):,}")

            # 📄 PREVIEW
            with st.expander("📄 Preview", expanded=False):
                st.markdown(f"""
                <div class="resume-preview">
                    {text[:1200]}
                </div>
                """, unsafe_allow_html=True)

            # 🔥 AUTO SHOW STRUCTURE BUTTON
            if name_p.strip():
                if st.button("🧠 Generate Structured Resume", use_container_width=True):

                    with st.spinner("🧠 AI is structuring your resume..."):
                        try:
                            structured = parse_resume_with_llm(text)
                        except Exception as e:
                            structured = {"error": str(e)}

                    st.session_state.resume_structured_paste = structured

                    if "error" not in structured:
                        st.success("✅ Resume structured successfully!")
                    else:
                        st.warning("⚠️ AI response parsing issue")

            else:
                st.info("ℹ️ Enter resume name to enable structuring")

            # 🧠 SHOW STRUCTURED OUTPUT
            if "resume_structured_paste" in st.session_state:
                st.markdown("### 🧠 Structured Resume")
                st.json(st.session_state.resume_structured_paste)

            # ✅ SAVE AFTER STRUCTURING
            if (
                "resume_structured_paste" in st.session_state
                and isinstance(st.session_state.resume_structured_paste, dict)
                and "error" not in st.session_state.resume_structured_paste
            ):

                if st.button("💾 Save to Database", type="primary", use_container_width=True):

                    rid = DB.upsert_resume(
                        name=name_p,
                        text=text,
                        structured=st.session_state.resume_structured_paste,
                        meta={"source": "paste"}
                    )

                    if rid:
                        st.success(f"✅ Saved successfully! ID: `{rid}`")
                        st.toast("🧠 Structured resume saved!", icon="✅")
                        # 🔥 CLEAR INPUT FIELD
                        
                        st.balloons()

                        # 🔥 RESET EVERYTHING (IMPORTANT)
                        st.session_state.pop("resume_structured_paste", None)
                        st.session_state.pop("last_pasted_text", None)

                        # optional (if you store globally)
                        st.session_state.resume_text = ""
                        st.session_state.resume_name = ""
                        st.session_state.resume_id = None

                        # 🔥 FORCE UI RESET
                        st.rerun()

                    else:
                        st.warning("⚠️ MongoDB not connected — loaded in session only.")
        else:
            st.info("💡 Paste your resume text above")
    with tab3:
        if not ENABLE_VISION:
            st.info("🔮 Vision AI is disabled. Enable in settings.")
            return
        
        st.markdown("#### 👁️ Vision Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Single Resume**")
            img_file = st.file_uploader("Upload screenshot", type=["png","jpg","jpeg"], key="vision_upload")
            
            if img_file:
                st.image(img_file, caption="Resume Screenshot", use_container_width=True)
                
                if st.button("🔍 Analyze", type="primary", use_container_width=True):
                    with st.spinner("🧠 Analyzing..."):
                        result = analyze_vision(img_file.read())
                    st.markdown(f'<div class="ai-card">{result}</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Compare Two Resumes**")
            f1 = st.file_uploader("Resume A", type=["png","jpg","jpeg"], key="comp1")
            f2 = st.file_uploader("Resume B", type=["png","jpg","jpeg"], key="comp2")
            
            if f1 and f2:
                if st.button("⚡ Compare", type="primary", use_container_width=True):
                    with st.spinner("🔄 Analyzing..."):
                        r1, r2 = compare_resumes_vision(f1.read(), f2.read())
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f'<div class="ai-card"><strong>📄 Resume A</strong><br>{r1}</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="ai-card"><strong>📄 Resume B</strong><br>{r2}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — JOB EXTRACTION (IMPROVED - FIXES JOB SELECTION)
# ═══════════════════════════════════════════════════════════════════════════════

def render_job_details_ui(details: dict, raw_text: str):
    """Render job details in a beautiful card format"""
    st.markdown("---")
    st.markdown("### 📋 Job Details")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"""
        <div class="job-card">
            <div class="job-title">🎯 {details.get('title', '—')}</div>
            <div class="job-meta">
                <strong>🏢 Company:</strong> {details.get('company', 'Not specified')}<br>
                <strong>📍 Location:</strong> {details.get('location', 'Not specified')}<br>
                <strong>💼 Type:</strong> {details.get('job_type', 'Not specified')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="job-card">
            <div class="job-meta">
                <strong>💰 Salary:</strong> {details.get('salary', 'Not specified')}<br>
                <strong>📚 Experience:</strong> {details.get('experience', 'Not specified')}<br>
                <strong>📅 Posted:</strong> {details.get('posted_date', 'Not specified')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    if details.get("skills"):
        st.markdown("### 🔧 Required Skills")
        skills_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">'
        for skill in details["skills"][:20]:
            skills_html += f'<span class="pill pill-cyan">{skill}</span>'
        skills_html += '</div>'
        st.markdown(skills_html, unsafe_allow_html=True)

    if details.get("responsibilities"):
        with st.expander("📝 Responsibilities", expanded=False):
            for r in details["responsibilities"][:10]:
                st.markdown(f"• {r}")

    if details.get("description"):
        with st.expander("📄 Full Description", expanded=False):
            st.write(details["description"][:2000])

    st.markdown("---")
    if st.button("💾 Save Job", type="primary", use_container_width=True):
        rid = DB.save_job_limited(
            title=details.get("title", "Job"),
            text=raw_text,
            details=details,
            source="manual"
        )
        if rid:
            st.success("✅ Job saved!")
            st.balloons()
            st.rerun()

def page_jobs():
    st.markdown('<div class="hero-title">💼 Job Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Extract, save, and manage job opportunities</div>', unsafe_allow_html=True)
    render_divider()

    # ─── SAVED JOBS SECTION ───
    jobs = DB.list_jobs()

    if jobs:
        st.markdown("### 💾 Saved Jobs")
        search_term = st.text_input("🔍 Search jobs", placeholder="Filter by title or company...")
        
        filtered_jobs = jobs
        if search_term:
            filtered_jobs = [
                job for job in jobs 
                if search_term.lower() in job.get("title", "").lower() 
                or search_term.lower() in job.get("details", {}).get("company", "").lower()
            ]
        
        if not filtered_jobs:
            st.info(f"No jobs matching '{search_term}'")
        else:
            for job in filtered_jobs:
                job_id = str(job["_id"])
                is_selected = st.session_state.get("job_id") == job_id
                
                company = job.get("details", {}).get("company", "")
                location = job.get("details", {}).get("location", "")
                
                # ✅ IMPROVED: Better visual indication of selected job
                col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
                
                with col1:
                    if is_selected:
                        st.markdown(f"""
                        <div class="job-selection-card">
                            <div style="display:flex;justify-content:space-between;align-items:center">
                                <div>
                                    <strong style="font-size:1.1rem; color:var(--accent-primary)">{job.get('title', 'Untitled')}</strong><br>
                                    <span style="color:var(--text-muted)">{company} {f'• {location}' if location else ''}</span>
                                </div>
                                <span class="job-selected-badge">✅ SELECTED</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        if st.button(f"**{job.get('title', 'Untitled')}**\n{company} {f'• {location}' if location else ''}", key=f"job_{job_id}", use_container_width=True):
                            # ✅ FIXED: Load BOTH job_title AND job_text
                            full_job = DB.get_job(job_id)
                            if full_job:
                                st.session_state.job_id = job_id
                                st.session_state.job_title = full_job.get("title", "")
                                st.session_state.job_text = full_job.get("text", "")  # ✅ FIX: This was missing!
                                st.session_state.job_details = full_job.get("details", {})
                                st.success(f"✅ Job selected: {full_job.get('title', '')}")
                                st.rerun()
                
                with col2:
                    if st.button("👁️", key=f"view_{job_id}", help="View details", use_container_width=True):
                        full_job = DB.get_job(job_id)
                        if full_job:
                            render_job_details_ui(full_job.get("details", {}), full_job.get("text", ""))
                
                with col3:
                    if st.button("🗑️", key=f"del_{job_id}", help="Delete", use_container_width=True):
                        DB.delete_job(job_id)
                        if st.session_state.get("job_id") == job_id:
                            st.session_state.job_id = None
                            st.session_state.job_text = ""
                            st.session_state.job_title = ""
                        st.rerun()
                
                with col4:
                    if st.button("⚖️", key=f"comp_{job_id}", help="Compare", use_container_width=True):
                        if job_id not in st.session_state.selected_jobs:
                            st.session_state.selected_jobs.append(job_id)
                            st.success(f"Added to comparison")
                        else:
                            st.session_state.selected_jobs.remove(job_id)
                            st.info(f"Removed from comparison")
                        st.rerun()
                
                st.divider()
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <div style="font-size: 1.1rem; font-weight: 600;">No saved jobs</div>
            <div>Extract your first job below!</div>
        </div>
        """, unsafe_allow_html=True)

    # ✅ NEW: Job Comparison Feature
    if len(st.session_state.selected_jobs) > 1:
        render_divider()
        st.markdown("### ⚖️ Compare Jobs")
        
        comp_jobs = []
        for job_id in st.session_state.selected_jobs[:3]:  # Max 3 jobs to compare
            job = DB.get_job(job_id)
            if job:
                comp_jobs.append((job_id, job))
        
        if comp_jobs:
            # Show comparison
            comp_cols = st.columns(len(comp_jobs))
            for col, (job_id, job) in zip(comp_cols, comp_jobs):
                with col:
                    details = job.get("details", {})
                    st.markdown(f"""
                    <div class="job-card" style="border-color: var(--accent-primary);">
                        <div class="job-title">{details.get('title', '—')}</div>
                        <div class="job-meta">
                            🏢 {details.get('company', '—')}<br>
                            📍 {details.get('location', '—')}<br>
                            💰 {details.get('salary', '—')}<br>
                            <br>
                            <strong>Experience:</strong><br>
                            {details.get('experience', '—')}<br>
                            <br>
                            <strong>Skills:</strong><br>
                            {', '.join(details.get('skills', [])[:5])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Clear comparison
        if st.button("🔄 Clear Comparison", use_container_width=True):
            st.session_state.selected_jobs = []
            st.rerun()

    # ✅ SHOW SELECTED JOB STATUS
    if st.session_state.get("job_id"):
        render_divider()
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0, 217, 255, 0.1) 0%, rgba(0, 217, 255, 0.05) 100%); border-left: 4px solid var(--accent-primary); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <strong>✅ Selected Job:</strong> {st.session_state.job_title}<br>
            <span style="color: var(--text-muted); font-size: 0.9rem;">Ready for ATS analysis!</span>
        </div>
        """, unsafe_allow_html=True)

    render_divider()
    st.markdown("### 🔍 Extract New Job")

    tab1, tab2, tab3 = st.tabs(["🌐 URL", "📋 Text", "📁 File"])

    with tab1:
        url = st.text_input("Job URL", placeholder="https://example.com/job-posting")
        if st.button("🚀 Extract", type="primary", use_container_width=True):
            if url:
                with st.spinner("Fetching..."):
                    details, raw_text, error = extract_job_from_url(url)
                if error:
                    st.error(f"❌ {error}")
                else:
                    render_job_details_ui(details, raw_text)
            else:
                st.warning("⚠️ Enter a URL")

    with tab2:
        jd_text = st.text_area("Job Description", height=300, placeholder="Paste the job description...", label_visibility="collapsed")
        if st.button("📊 Analyze", type="primary", use_container_width=True):
            if jd_text.strip():
                with st.spinner("Analyzing..."):
                    details = extract_job_from_text(jd_text)
                render_job_details_ui(details, jd_text)
            else:
                st.warning("⚠️ Paste a job description")

    with tab3:
        jf = st.file_uploader("Choose file", type=["pdf", "docx", "txt"], label_visibility="collapsed")
        if jf:
            with st.spinner("Parsing..."):
                details, raw_text, error = extract_job_from_file(jf)
            if error:
                st.error(f"❌ {error}")
            else:
                st.success("✅ File parsed!")
                with st.spinner("Extracting..."):
                    details = extract_job_details(raw_text)
                render_job_details_ui(details, raw_text)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ATS & OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════════

def page_ats():
    st.markdown('<div class="hero-title">🎯 ATS Optimizer</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Analyze and optimize your resume for Applicant Tracking Systems</div>', unsafe_allow_html=True)
    render_divider()

    # ✅ IMPROVED: Better error messages
    if not st.session_state.resume_text:
        st.error("⚠️ No resume loaded")
        st.markdown("👉 Go to **Resume Manager** to upload or load a resume")
        return
    
    if not st.session_state.job_text:
        st.error("⚠️ No job loaded")
        st.markdown("👉 Go to **Job Dashboard** to select or extract a job")
        st.markdown("**To select a saved job:** Click on any job in the 'Saved Jobs' section")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="ai-card"><strong>📄 Resume:</strong> {st.session_state.resume_name or "Loaded"}<br><span style="color:var(--text-muted)">{len(st.session_state.resume_text):,} chars</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="ai-card"><strong>💼 Job:</strong> {st.session_state.job_title or "Loaded"}<br><span style="color:var(--text-muted)">{len(st.session_state.job_text):,} chars</span></div>', unsafe_allow_html=True)

    if st.button("🚀 Run ATS Analysis", use_container_width=True, type="primary"):
        with st.spinner("🤖 Analyzing..."):
            result = compute_ats(st.session_state.resume_text, st.session_state.job_text)
            st.session_state.ats_result = result
            DB.save_ats(st.session_state.resume_id or "session", st.session_state.job_id or "manual", result.get("score",0), result)

    if st.session_state.ats_result:
        r = st.session_state.ats_result
        score = r.get("score", 0)
        verdict = r.get("verdict","—")

        render_divider()
        st.markdown("### 📊 Results")

        render_score_ring(score)
        st.markdown(f'<div style="text-align:center"><span class="pill pill-{"green" if score>=80 else "amber" if score>=55 else "red"}" style="font-size:0.95rem;padding:0.5rem 1.5rem">{verdict}</span></div>', unsafe_allow_html=True)

        ss = r.get("section_scores",{})
        if ss:
            st.markdown("**Section Breakdown**")
            for section, val in ss.items():
                col1, col2 = st.columns([1,4])
                with col1:
                    st.caption(section.capitalize())
                with col2:
                    st.progress(int(val) / 100 if val <= 1 else int(val) / 100)

        kc1, kc2 = st.columns(2)
        with kc1:
            st.markdown("**✅ Matched Keywords**")
            matched = r.get("matched_keywords",[])
            if matched:
                for k in matched[:15]:
                    st.markdown(render_pill(k, "green"), unsafe_allow_html=True)
        with kc2:
            st.markdown("**❌ Missing Keywords**")
            missing = r.get("missing_keywords",[])
            if missing:
                for k in missing[:15]:
                    st.markdown(render_pill(k, "red"), unsafe_allow_html=True)
            else:
                st.markdown(render_pill("None missing! 🎉", "green"), unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**💪 Strengths**")
            for s in r.get("strengths",[]):
                st.markdown(f"✅ {s}")
        with sc2:
            st.markdown("**⚠️ Gaps**")
            gaps = r.get("gaps",[])
            if gaps:
                for g in gaps:
                    st.markdown(f"⚡ {g}")
            else:
                st.markdown("🎉 No major gaps!")

        recs = r.get("recommendations",[])
        if recs:
            render_divider()
            st.markdown("### 💡 Recommendations")
            for i, rec in enumerate(recs, 1):
                st.markdown(f'<div class="ai-card"><strong>{i}.</strong> {rec}</div>', unsafe_allow_html=True)

        render_divider()
        st.markdown("### ✨ Optimize Resume")
        user_instructions = st.text_input("Additional instructions (optional)")
        
        if st.button("⚡ Optimize", type="primary", use_container_width=True):
            if score >= 90:
                st.success(f"🎉 Score {score}/100 — Already excellent!")
            else:
                with st.spinner("✨ Optimizing..."):
                    optimized = optimize_resume(st.session_state.resume_text, st.session_state.job_text, user_instructions)
                    st.session_state.optimized_resume = optimized
                st.success("✅ Optimized!")
                st.text_area("Optimized Resume", optimized, height=400, disabled=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📥 Download", optimized.encode(), "optimized_resume.txt", "text/plain", use_container_width=True)
                
                with col2:
                    opt_name = st.text_input("Name", value=f"Optimized_{st.session_state.resume_name or 'Resume'}", key="opt_name")
                    if st.button("💾 Save", use_container_width=True):
                        rid = DB.save_optimized_resume(opt_name, optimized)
                        if rid:
                            st.success(f"✅ Saved!")
                        else:
                            st.warning("MongoDB not connected")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — EMAIL AUTOMATION
# ═══════════════════════════════════════════════════════════════════════════════

def page_email():
    st.markdown('<p class="section-header">📧 Email Automation</p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📤 Send Resume", "📥 Check Responses"])

    with tab1:
        st.markdown("#### Send Resume via Email")
        ec1, ec2 = st.columns(2)
        with ec1:
            to_email = st.text_input("Recipient Email", placeholder="recruiter@company.com")
            job_title_e = st.text_input("Job Title", value=st.session_state.job_title or "")
        with ec2:
            candidate = st.text_input("Your Name", placeholder="John Doe")
            subject_e = st.text_input("Subject", value=f"Application for {st.session_state.job_title or 'Position'}")

        if st.button("📤 Send Email", type="primary", use_container_width=True):
            if not to_email:
                st.warning("Enter recipient email.")
                return
            if not st.session_state.resume_text:
                st.warning("Load a resume first.")
                return
            
            body_html = resume_email_html(candidate or "Candidate", job_title_e, st.session_state.resume_text)
            with st.spinner("Sending..."):
                ok = send_email(to_email, subject_e, body_html, st.session_state.resume_text.encode(), f"resume_{candidate or 'candidate'}.txt")
            if ok:
                st.success(f"✅ Sent to {to_email}!")

    with tab2:
        st.markdown("#### Check Job Responses")
        st.info("Email inbox scanning feature coming soon!")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — AI AGENT CHAT
# ═══════════════════════════════════════════════════════════════════════════════

def page_agent():
    st.markdown('<p class="section-header">🤖 AI Agent Chat</p>', unsafe_allow_html=True)
    st.caption(f"Powered by Groq {MAIN_MODEL}")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about your resume, jobs, ATS...")
    
    if user_input:
        st.session_state.chat_history.append({"role":"user","content":user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                context = (
                    f"Resume: {st.session_state.resume_text[:600] if st.session_state.resume_text else 'None'}\n"
                    f"Job: {st.session_state.job_text[:400] if st.session_state.job_text else 'None'}\n"
                    f"User: {user_input}"
                )
                response = groq_chat(context, "You are ResumeAI Pro, an expert career assistant. Be specific and actionable.")
            st.markdown(response)
            st.session_state.chat_history.append({"role":"assistant","content":response})

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def page_settings():
    st.markdown('<p class="section-header">⚙️ Settings</p>', unsafe_allow_html=True)
    render_import_credentials()
    
    with st.expander("➕ Add Credentials", expanded=True):
        ask_user_for_missing_ui()

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<div class="sidebar-logo">🚀 ResumeAI Pro</div>', unsafe_allow_html=True)

    if st.session_state.resume_text:
        st.markdown(f'<div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:8px 12px;margin-bottom:8px;font-size:.82rem"><span style="display:inline-block;width:6px;height:6px;background:var(--success);border-radius:50%;margin-right:6px"></span><b>{(st.session_state.resume_name or "Resume")[:20]}</b></div>', unsafe_allow_html=True)
    
    if st.session_state.job_text:
        st.markdown(f'<div style="background:rgba(0,217,255,.1);border:1px solid rgba(0,217,255,.3);border-radius:8px;padding:8px 12px;margin-bottom:8px;font-size:.82rem"><span style="display:inline-block;width:6px;height:6px;background:var(--accent-primary);border-radius:50%;margin-right:6px"></span><b>{(st.session_state.job_title or "Job")[:20]}</b></div>', unsafe_allow_html=True)

    st.divider()

    nav_items = [
        ("dashboard", "🏠", "Dashboard"),
        ("resume", "📄", "Resume Manager"),
        ("jobs", "💼", "Job Extraction"),
        ("ats", "🎯", "ATS Optimizer"),
        ("email", "📧", "Email"),
        ("agent", "🤖", "AI Chat"),
        ("settings", "⚙️", "Settings"),
    ]
    
    for page_id, icon, label in nav_items:
        active = st.session_state.page == page_id
        if st.button(f"{icon} {label}", key=f"nav_{page_id}", use_container_width=True):
            st.session_state.page = page_id
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

PAGE_MAP = {
    "dashboard": page_dashboard,
    "resume": page_resume,
    "jobs": page_jobs,
    "ats": page_ats,
    "email": page_email,
    "agent": page_agent,
    "settings": page_settings,
}

PAGE_MAP.get(st.session_state.page, page_dashboard)()
