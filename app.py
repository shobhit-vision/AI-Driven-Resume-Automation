
"""
app.py — ResumeAI Pro v2.0
AI-Driven Resume Automation Platform
LangChain Agents · Groq LLM · MongoDB · Telegram · Vision AI · Voice Commands
"""
import streamlit as st
from datetime import datetime
from bson import ObjectId
from resume import parse_resume_file as prf

# Page config MUST be the first Streamlit command
st.set_page_config(
    page_title="ResumeAI Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS to fix spacing and sidebar ───────────────────────────────────────────
st.markdown("""
<style>

/* ===== GLOBAL ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
  --bg: #020617;
  --bg-soft: #0f172a;
  --card: rgba(255,255,255,0.04);
  --border: rgba(255,255,255,0.08);

  --accent: #6366f1;
  --accent2: #22d3ee;

  --text: #f8fafc;
  --muted: #94a3b8;

  --radius: 16px;
}

/* ===== BASE ===== */
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg,#020617,#020617 60%,#0f172a) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text);
}

/* ===== CONTAINER ===== */
.main .block-container {
    max-width: 1250px;
    padding: 2rem 1.5rem !important;
}

/* ===== HERO ===== */
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(90deg,#fff,#22d3ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-sub {
    color: var(--muted);
    font-size: 1.05rem;
    margin-bottom: 1rem;
}

/* ===== SECTION HEADERS ===== */
.section-header {
    font-size: 1.4rem;
    font-weight: 700;
    margin: 1.5rem 0 0.8rem 0;
    padding-left: 8px;
    border-left: 4px solid var(--accent);
}

/* ===== CARDS ===== */
.ai-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem;
    transition: 0.25s;
}

.ai-card:hover {
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 0 25px rgba(99,102,241,0.15);
}

/* ===== METRIC ===== */
.metric-card {
    background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(34,211,238,0.05));
    border-radius: var(--radius);
    padding: 1rem;
    text-align: center;
    border: 1px solid var(--border);
}

.metric-val {
    font-size: 1.6rem;
    font-weight: 700;
}

.metric-lbl {
    font-size: 0.85rem;
    color: var(--muted);
}

/* ===== BUTTON ===== */
.stButton>button {
    border-radius: 12px !important;
    background: linear-gradient(135deg,#6366f1,#8b5cf6) !important;
    color: white !important;
    border: none !important;
    font-weight: 600;
}

.stButton>button:hover {
    transform: translateY(-2px);
}

/* ===== INPUT ===== */
.stTextInput input,
.stTextArea textarea {
    background: var(--bg-soft) !important;
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    color: white !important;
}

/* ===== PILLS ===== */
.pill {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    margin: 2px;
}

.pill-green {background:#10b98133;color:#10b981;}
.pill-red {background:#ef444433;color:#ef4444;}
.pill-blue {background:#3b82f633;color:#3b82f6;}
.pill-amber {background:#f59e0b33;color:#f59e0b;}

/* ===== SCORE RING ===== */
.score-ring {
  width:120px;height:120px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-weight:700;font-size:22px;
  background:conic-gradient(#6366f1 calc(var(--pct)*1%), #1e293b 0);
}

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"] {
    background:#020617;
}

/* ===== REMOVE DEFAULT ===== */
#MainMenu, footer {display:none;}

</style>
""", unsafe_allow_html=True)

# ─── Core Imports ─────────────────────────────────────────────────────────────
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
    GROQ_KEY, MONGO_URI, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    EMAIL_ADDR, EMAIL_PASS, SMTP_HOST, SMTP_PORT, IMAP_HOST,
    MAIN_MODEL, VISION_MODEL, APP_NAME, APP_VERSION,
    ENABLE_VOICE, ENABLE_VISION, ENABLE_MONGODB, ENABLE_TELEGRAM,
    TELEGRAM_COMMANDS, credential_status, SECRETS_TEMPLATE, DEPENDENCIES,
)
from resume import (
    parse_resume_file, groq_chat, groq_vision,
    compute_ats, optimize_resume, generate_new_resume,
    generate_cover_letter, improve_linkedin,
    analyze_vision, compare_resumes_vision,
    build_resume_agent, format_ats_telegram, resume_email_html,
)
from jobs import (
    extract_job_from_url, extract_job_from_text, extract_job_from_file,
    extract_job_details,
)
from telegram_bot import (
    send_message as tg_send,
    send_ats_report as tg_ats,
    send_job_details as tg_job,
    send_document as tg_doc,
    test_connection as tg_test,
    set_webhook, delete_webhook, get_updates,
    process_bot_command, TelegramPoller,
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

# ─── Session State ────────────────────────────────────────────────────────────
DEFAULTS = {
    "page":              "dashboard",
    "resume_text":       "",
    "resume_name":       "",
    "resume_id":         None,
    "job_text":          "",
    "job_title":         "",
    "jobs_history":      [],
    "job_details":       {},
    "ats_result":        None,
    "optimized_resume":  "",
    "notifications":     [],
    "tg_messages":       [],
    "template_text":     "",
    "chat_history":      [],
    "voice_input":       "",
    "tg_poller_active":  False,
    "sidebar_state":     "expanded",  # Track sidebar state
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── MongoDB DB Helper ────────────────────────────────────────────────────────
class DB:
    _client = None
    _db     = None

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
    def save_resume(cls, name, text, meta=None):
        db = cls.get()
        if db is None: return None
        doc = {"name": name, "text": text, "meta": meta or {}, "created_at": datetime.utcnow()}
        return str(db["resumes"].insert_one(doc).inserted_id)

    @classmethod
    def list_resumes(cls):
        db = cls.get()
        if db is None: return []
        return list(db["resumes"].find({}, {"text": 0}).sort("created_at", -1).limit(50))

    @classmethod
    def get_resume(cls, rid):
        db = cls.get()
        if db is None: return None
        try: return db["resumes"].find_one({"_id": ObjectId(rid)})
        except: return None

    # ---------------- JOB METHODS ----------------

    @classmethod
    def save_job_limited(cls, title, text, details, source="manual", meta=None):
        db = cls.get()
        if db is None: return None
        collection = db["jobs"]

        # Count jobs
        count = collection.count_documents({})

        # If already 3 → delete oldest
        if count >= 3:
            oldest = collection.find().sort("created_at", 1).limit(1)
            for doc in oldest:
                collection.delete_one({"_id": doc["_id"]})

        # Insert new job
        doc = {
            "title": title,
            "text": text,
            "details": details,   # ✅ IMPORTANT (structured data)
            "source": source,
            "meta": meta or {},
            "created_at": datetime.utcnow()
        }

        return str(collection.insert_one(doc).inserted_id)


    @classmethod
    def list_jobs(cls):
        db = cls.get()
        if db is None: return []

        return list(
            db["jobs"]
            .find({}, {"text": 0})   # exclude large text for speed
            .sort("created_at", -1)
        )


    @classmethod
    def get_job(cls, jid):
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
    def recent_ats(cls, limit=10):
        db = cls.get()
        if db is None: return []
        return list(db["ats_results"].find().sort("created_at", -1).limit(limit))

# ─── Email helpers ────────────────────────────────────────────────────────────
def send_email(to_addr, subject, body, attachment_bytes=None, attachment_name=None):
    if not (EMAIL_ADDR and EMAIL_PASS):
        st.error("Email credentials not configured."); return False
    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_ADDR
        msg["To"]      = to_addr
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
        st.error(f"Email send failed: {e}"); return False

def check_inbox_for_job_responses(limit=20):
    if not (EMAIL_ADDR and EMAIL_PASS): return []
    results = []
    keywords = ["offer","selected","congratulations","interview","regret","unfortunately","position","application","shortlisted","background check","onboarding"]
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST) as mail:
            mail.login(EMAIL_ADDR, EMAIL_PASS)
            mail.select("INBOX")
            _, ids = mail.search(None, "UNSEEN")
            for eid in (ids[0].split() or [])[-limit:]:
                _, data = mail.fetch(eid, "(RFC822)")
                msg     = email_module.message_from_bytes(data[0][1])
                subject = msg.get("Subject","")
                sender  = msg.get("From","")
                body    = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8","ignore"); break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8","ignore")
                full = (subject + " " + body).lower()
                matched = [k for k in keywords if k in full]
                if matched:
                    sentiment = "positive" if any(k in full for k in ["offer","congratulations","selected","shortlisted","onboarding"]) else "negative" if any(k in full for k in ["regret","unfortunately"]) else "neutral"
                    results.append({"subject":subject,"sender":sender,"body":body[:500],"matched":matched,"sentiment":sentiment,"date":msg.get("Date","")})
    except Exception as e:
        st.error(f"IMAP error: {e}")
    return results

# ─── UI Helpers ───────────────────────────────────────────────────────────────
def status_indicator(label, ok):
    cls = "dot-green" if ok else "dot-red"
    return f'<span class="status-dot {cls}"></span>{label}'

def pill(text, color="blue"):
    return f'<span class="pill pill-{color}">{text}</span>'

def score_color(s):
    return "great" if s >= 80 else "ok" if s >= 55 else "bad"

def render_score_ring(score):
    cls = score_color(score)
    st.markdown(f"""<div style="display:flex;justify-content:center;margin:1rem 0">
      <div class="score-ring score-{cls}" style="--pct:{score}">{score}</div></div>""",
      unsafe_allow_html=True)

# ─── Voice Command ────────────────────────────────────────────────────────────
def voice_input_widget():
    """Browser-based voice input using Web Speech API via JS."""
    st.markdown("""
    <script>
    function startVoice(){
      if(!('webkitSpeechRecognition' in window||'SpeechRecognition' in window)){
        alert('Voice not supported in this browser. Use Chrome.');return;}
      const rec=new (window.SpeechRecognition||window.webkitSpeechRecognition)();
      rec.lang='en-US';rec.interimResults=false;rec.maxAlternatives=1;
      rec.onresult=e=>{
        const t=e.results[0][0].transcript;
        const el=window.parent.document.querySelector('textarea[data-testid="stTextArea"]');
        if(el){el.value=t;el.dispatchEvent(new Event('input',{bubbles:true}));}
        document.getElementById('voice-status').innerText='✅ Heard: '+t;
      };
      rec.onerror=e=>document.getElementById('voice-status').innerText='❌ Error: '+e.error;
      rec.onstart=()=>document.getElementById('voice-status').innerText='🎙 Listening...';
      rec.start();
    }
    </script>
    <button onclick="startVoice()" style="background:linear-gradient(135deg,#ef4444,#f97316);color:#fff;border:none;border-radius:10px;padding:8px 20px;font-weight:600;cursor:pointer;font-size:14px;">
      🎙 Voice Command
    </button>
    <span id="voice-status" style="color:#94a3b8;margin-left:12px;font-size:13px;"></span>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    st.markdown('<div class="hero-title">🚀 ResumeAI Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">AI Resume • ATS Optimization • Telegram Automation</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Status row
    checks = [
        ("🤖 Groq LLM",      bool(GROQ_KEY and GROQ_OK)),
        ("🗄️ MongoDB",       bool(MONGO_URI and MONGO_OK)),
        ("📱 Telegram Bot",  bool(TELEGRAM_BOT_TOKEN)),
        ("📧 Email SMTP",    bool(EMAIL_ADDR and EMAIL_PASS)),
    ]
    for col, (lbl, ok) in zip(st.columns(4), checks):
        with col:
            st.markdown(f'<div class="metric-card">{status_indicator(lbl, ok)}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick stats
    db = DB.get()
    total_resumes = total_ats = avg_score = 0
    if db != None:
        total_resumes = db["resumes"].count_documents({})
        ats_docs      = list(db["ats_results"].find({}, {"score": 1}))
        total_ats     = len(ats_docs)
        avg_score     = int(sum(d.get("score", 0) for d in ats_docs) / max(total_ats, 1))

    for col, (val, lbl) in zip(st.columns(4), [
        (total_resumes, "Resumes Stored"),
        (total_ats,     "ATS Analyses"),
        (avg_score,     "Avg ATS Score"),
        ("∞",           "Optimizations"),
    ]):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-val">{val}</div><div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)


    if total_ats > 0:
        st.markdown("<br>")
        st.markdown('<p class="section-header">📊 Recent ATS Results</p>', unsafe_allow_html=True)
        for r in DB.recent_ats(5):
            sc = r.get("score", 0)
            v  = r.get("result", {}).get("verdict", "—") if isinstance(r.get("result"), dict) else "—"
            st.markdown(f'<div class="ai-card" style="display:flex;align-items:center;gap:16px"><span class="pill pill-{"green" if sc>=80 else "amber" if sc>=55 else "red"}">{sc}/100</span><span style="font-weight:500">{v}</span><span style="color:var(--muted);font-size:.8rem;margin-left:auto">{str(r.get("created_at",""))[:19]}</span></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Resume Manager
# ══════════════════════════════════════════════════════════════════════════════
def page_resume():
    # ---------- STYLE ----------
    st.markdown("""
    <style>
    /* Resume page specific styles */
    .resume-header {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    
    .resume-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.1);
        transition: transform 0.2s ease;
    }
    
    .resume-card:hover {
        transform: translateY(-2px);
        border-color: rgba(16,185,129,0.3);
    }
    
    .resume-name {
        font-size: 1.2rem;
        font-weight: 600;
        color: #10b981;
        margin-bottom: 0.5rem;
    }
    
    .resume-meta {
        font-size: 0.85rem;
        color: #9ca3af;
        margin-bottom: 1rem;
    }
    
    .resume-preview {
        background: rgba(0,0,0,0.2);
        border-radius: 8px;
        padding: 1rem;
        font-family: monospace;
        font-size: 0.85rem;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .action-buttons {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    .success-badge {
        background: rgba(16,185,129,0.2);
        border-left: 3px solid #10b981;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .template-section {
        background: linear-gradient(135deg, rgba(16,185,129,0.05) 0%, rgba(16,185,129,0.02) 100%);
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
        border: 1px solid rgba(16,185,129,0.2);
    }
    
    .comparison-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-radius: 12px;
        padding: 1rem;
        height: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<div class="resume-header">📄 Resume Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload, manage, and analyze your resumes</div>', unsafe_allow_html=True)

    # ---------- STORED RESUMES SECTION (TAB 3 - MOVED TO TOP) ----------
    st.markdown("### 🗄️ Stored Resumes")
    
    resumes = DB.list_resumes()

    if not resumes:
        st.info("📭 No resumes stored yet. Upload your first resume using the tools below.")
    else:
        # Create columns for resume cards
        cols = st.columns(2)
        resume_items = list(resumes)
        
        for idx, resume in enumerate(resume_items):
            with cols[idx % 2]:
                resume_id = str(resume["_id"])
                created_date = str(resume.get("created_at", ""))[:10] if resume.get("created_at") else "Unknown date"
                
                st.markdown(f"""
                <div class="resume-card">
                    <div class="resume-name">📄 {resume.get('name', 'Unnamed Resume')}</div>
                    <div class="resume-meta">
                        📅 {created_date}<br>
                        📝 {len(resume.get('text', '')):,} characters
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Use", key=f"use_resume_{resume_id}", use_container_width=True):
                        full = DB.get_resume(resume_id)
                        if full:
                            st.session_state.resume_text = full["text"]
                            st.session_state.resume_name = full["name"]
                            st.session_state.resume_id = resume_id
                            st.success(f"✅ Loaded: {full['name']}")
                            st.rerun()
                
                with col2:
                    if st.button("👁️ Preview", key=f"preview_resume_{resume_id}", use_container_width=True):
                        full = DB.get_resume(resume_id)
                        if full:
                            with st.expander(f"Preview: {full['name']}", expanded=True):
                                st.markdown(f"""
                                <div class="resume-preview">
                                    {full['text'][:1000]}...
                                </div>
                                """, unsafe_allow_html=True)
                
                st.divider()

    # Show current active resume if any
    if "resume_text" in st.session_state and st.session_state.resume_text:
        st.markdown(f"""
        <div class="success-badge">
            ✅ <strong>Active Resume:</strong> {st.session_state.get('resume_name', 'Loaded Resume')}<br>
            📝 {len(st.session_state.resume_text):,} characters loaded
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # ---------- TABS FOR UPLOAD, PASTE, AND VISION ----------
    tab1, tab2, tab4 = st.tabs(["⬆️ Upload File", "📋 Paste Text", "👁️ Vision Analyze"])

    # -------- TAB 1: UPLOAD FILE --------
    with tab1:
        st.markdown("### 📁 Upload Resume File")
        st.markdown("Supported formats: PDF, DOCX, TXT")
        
        uf = st.file_uploader("Choose your resume file", type=["pdf","docx","txt"], label_visibility="collapsed")
        
        if uf:
            with st.spinner("📄 Parsing document..."):
                text = parse_resume_file(uf)
            
            if text and not text.startswith("[Error"):
                st.session_state.resume_text = text
                st.session_state.resume_name = uf.name
                
                # Success message with stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Characters", f"{len(text):,}")
                with col2:
                    st.metric("Words", f"{len(text.split()):,}")
                with col3:
                    st.metric("File", uf.name.split('.')[-1].upper())
                
                st.success(f"✅ Successfully parsed **{uf.name}**")
                
                # Preview section
                with st.expander("📄 Preview Extracted Text", expanded=False):
                    st.markdown(f"""
                    <div class="resume-preview">
                        {text[:1500]}...
                    </div>
                    """, unsafe_allow_html=True)
                
                # Save options
                st.markdown("#### 💾 Save Options")
                col1, col2 = st.columns(2)
                with col1:
                    name_inp = st.text_input("Resume name", value=uf.name, key="save_name_upload")
                
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Save to Database", type="primary", use_container_width=True):
                        rid = DB.save_resume(name_inp, text, {"source":"upload","filename":uf.name})
                        if rid:
                            st.session_state.resume_id = rid
                            st.success(f"✅ Saved successfully! ID: `{rid}`")
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("⚠️ MongoDB not connected — resume loaded in session only.")
            else:
                st.error(f"❌ {text}")

    # -------- TAB 2: PASTE TEXT --------
    with tab2:
        st.markdown("### 📋 Paste Resume Text")
        st.markdown("Copy and paste your resume content below")
        
        pasted = st.text_area(
            "Resume content", 
            height=350, 
            placeholder="Paste your complete resume text here...",
            help="Include all sections like Experience, Education, Skills, etc."
        )
        
        name_p = st.text_input("Resume name", value="My Resume", key="resume_name_paste")
        
        if pasted.strip():
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Load Resume", use_container_width=True):
                    st.session_state.resume_text = pasted
                    st.session_state.resume_name = name_p
                    st.success("✅ Resume loaded successfully!")
                    
                    # Show preview
                    with st.expander("📄 Preview Loaded Resume", expanded=True):
                        st.markdown(f"""
                        <div class="resume-preview">
                            {pasted[:1000]}...
                        </div>
                        """, unsafe_allow_html=True)
            
            with col2:
                if st.button("💾 Save & Load", type="primary", use_container_width=True):
                    st.session_state.resume_text = pasted
                    st.session_state.resume_name = name_p
                    rid = DB.save_resume(name_p, pasted, {"source":"paste"})
                    if rid:
                        st.success(f"✅ Saved and loaded! ID: `{rid}`")
                        st.balloons()
                        st.rerun()
                    else:
                        st.success("✅ Loaded in session (database not connected)")
        else:
            st.info("💡 Paste your resume text above to get started")

        # Template upload section
        st.markdown("---")
        st.markdown("### 📋 Upload Resume Template")
        st.markdown("Upload a template to generate a new resume tailored to a job")
        
        tf = st.file_uploader("Upload template file", type=["pdf","docx","txt"], key="template_upload")
        if tf:
            
            with st.spinner("Loading template..."):
                template_text = prf(tf)
                st.session_state.template_text = template_text
                st.success(f"✅ Template loaded: {tf.name}")
                
                with st.expander("📄 Template Preview"):
                    st.markdown(f"""
                    <div class="resume-preview">
                        {template_text[:800]}...
                    </div>
                    """, unsafe_allow_html=True)

    # -------- TAB 4: VISION ANALYZE --------
    with tab4:
        if not ENABLE_VISION:
            st.info("🔮 Vision AI is disabled in settings. Enable it to analyze resume images.")
            return
        
        st.markdown("### 👁️ Vision AI - Resume Analysis")
        st.markdown(f"Using **{VISION_MODEL}** for intelligent resume analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📸 Single Resume Analysis")
            img_file = st.file_uploader("Upload resume screenshot/image", type=["png","jpg","jpeg"], key="vision_upload")
            
            if img_file:
                img_bytes = img_file.read()
                st.image(img_bytes, caption="Uploaded Resume Screenshot", use_container_width=True)
                
                if st.button("🔍 Analyze with Vision AI", type="primary", use_container_width=True):
                    with st.spinner("🧠 Running vision analysis..."):
                        result = analyze_vision(img_bytes)
                    st.markdown(f"""
                    <div class="ai-card">
                        <div style="color: #10b981; font-weight: 600; margin-bottom: 12px;">👁️ Vision Analysis Results</div>
                        {result}
                    </div>
                    """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 🆚 Compare Two Resumes")
            st.markdown("Upload two resume images for comparison")
            
            f1 = st.file_uploader("Resume A", type=["png","jpg","jpeg"], key="comp1")
            f2 = st.file_uploader("Resume B", type=["png","jpg","jpeg"], key="comp2")
            
            if f1 and f2:
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    st.image(f1.read(), caption="Resume A", use_container_width=True)
                with col_img2:
                    st.image(f2.read(), caption="Resume B", use_container_width=True)
                
                if st.button("⚡ Compare Resumes", type="primary", use_container_width=True):
                    with st.spinner("🔄 Analyzing both resumes..."):
                        # Reset file pointers
                        f1.seek(0)
                        f2.seek(0)
                        r1, r2 = compare_resumes_vision(f1.read(), f2.read())
                    
                    col_res1, col_res2 = st.columns(2)
                    with col_res1:
                        st.markdown(f"""
                        <div class="comparison-card">
                            <div style="color: #10b981; font-weight: 600; margin-bottom: 12px;">📄 Resume A Analysis</div>
                            {r1}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_res2:
                        st.markdown(f"""
                        <div class="comparison-card">
                            <div style="color: #10b981; font-weight: 600; margin-bottom: 12px;">📄 Resume B Analysis</div>
                            {r2}
                        </div>
                        """, unsafe_allow_html=True)

    # Footer with tips
    st.markdown("---")
    with st.expander("💡 Tips for Best Results"):
        st.markdown("""
        - **For Uploaded Files**: Ensure your resume is properly formatted (PDF, DOCX, or TXT)
        - **For Paste Text**: Include all sections like Experience, Education, Skills for better parsing
        - **For Vision Analysis**: Use clear, high-resolution screenshots of your resume
        - **Templates**: Upload a resume template to generate customized versions for different jobs
        """)
# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Job Extraction
# ══════════════════════════════════════════════════════════════════════════════

# ---------------- JOB PAGE ----------------
def page_jobs():
    # ---------- STYLE ----------
    st.markdown("""
    <style>
    /* Global styles */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    
    /* Job name button (acts like card) */
    .job-btn button {
        width: 100%;
        text-align: left;
        padding: 12px 16px;
        border-radius: 12px;
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid rgba(255,255,255,0.1);
        color: #f3f4f6;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .job-btn button:hover {
        transform: translateY(-2px);
        background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
        border-color: rgba(255,255,255,0.2);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }

    /* Selected job */
    .selected-job button {
        background: linear-gradient(135deg, #065f46 0%, #047857 100%) !important;
        border: 1px solid #10b981 !important;
        box-shadow: 0 0 0 2px rgba(16,185,129,0.2);
    }
    
    .selected-job button:hover {
        background: linear-gradient(135deg, #047857 0%, #065f46 100%) !important;
    }

    /* Action buttons */
    .action-btn button {
        width: 100%;
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .action-btn button:hover {
        transform: scale(1.05);
    }

    /* View button */
    .view-btn button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
    }
    
    .view-btn button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 2px 8px rgba(59,130,246,0.3);
    }

    /* Delete button */
    .delete-btn button {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        border: none;
    }
    
    .delete-btn button:hover {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
        box-shadow: 0 2px 8px rgba(239,68,68,0.3);
    }
    
    /* Job card styling */
    .job-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .job-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #10b981;
        margin-bottom: 0.5rem;
    }
    
    .job-meta {
        font-size: 0.9rem;
        color: #9ca3af;
        line-height: 1.4;
    }
    
    /* Empty state styling */
    .empty-state {
        text-align: center;
        padding: 3rem;
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }
    
    /* Stats cards */
    .stats-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .stats-number {
        font-size: 1.5rem;
        font-weight: 700;
        color: #10b981;
    }
    
    .stats-label {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 0.25rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<div class="main-header">💼 Job Dashboard</div>', unsafe_allow_html=True)

    jobs = DB.list_jobs()

    if jobs:
        st.markdown("### 💾 Saved Jobs")
        # Add search/filter for jobs
        search_term = st.text_input("🔍 Search jobs", placeholder="Filter by job title or company...")
        
        filtered_jobs = jobs
        if search_term:
            filtered_jobs = [
                job for job in jobs 
                if search_term.lower() in job.get("title", "").lower() 
                or search_term.lower() in job.get("details", {}).get("company", "").lower()
            ]
        
        if not filtered_jobs:
            st.info(f"No jobs found matching '{search_term}'")
        else:
            for job in filtered_jobs:
                job_id = str(job["_id"])
                is_selected = st.session_state.get("selected_job_id") == job_id
                
                # Get company info for display
                company = job.get("details", {}).get("company", "")
                location = job.get("details", {}).get("location", "")
                
                # Display job card with more info
                col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
                
                # ---------- COLUMN 1: JOB NAME (SELECTABLE) ----------
                wrapper = "selected-job job-btn" if is_selected else "job-btn"
                col1.markdown(f'<div class="{wrapper}">', unsafe_allow_html=True)
                
                # Enhanced button with company info
                button_label = f"**{job.get('title', 'Untitled Job')}**"
                if company:
                    button_label += f"\n\n{company}"
                    if location:
                        button_label += f" • {location}"
                
                if col1.button(button_label, key=f"job_{job_id}", help="Click to select this job"):
                    st.session_state.selected_job_id = job_id
                    st.session_state.job_title = job.get("title", "")
                
                col1.markdown("</div>", unsafe_allow_html=True)
                
                # ---------- COLUMN 2: VIEW ----------
                col2.markdown('<div class="action-btn view-btn">', unsafe_allow_html=True)
                if col2.button("👁️ View", key=f"view_{job_id}", help="View job details"):
                    full_job = DB.get_job(job_id)
                    if full_job:
                        render_job_details_ui(
                            full_job.get("details", {}),
                            full_job.get("text", "")
                        )
                col2.markdown("</div>", unsafe_allow_html=True)
                
                # ---------- COLUMN 3: DELETE ----------
                col3.markdown('<div class="action-btn delete-btn">', unsafe_allow_html=True)
                if col3.button("🗑️ Delete", key=f"del_{job_id}", help="Delete this job"):
                    DB.delete_job(job_id)
                    if st.session_state.get("selected_job_id") == job_id:
                        st.session_state.pop("selected_job_id", None)
                    st.rerun()
                col3.markdown("</div>", unsafe_allow_html=True)
                
                # ---------- COLUMN 4: STATUS (placeholder for future feature) ----------
                with col4:
                    status = job.get("status", "📋 New")
                    st.markdown(f"""
                    <div style="padding: 8px; text-align: center; background: rgba(16,185,129,0.1); border-radius: 8px; font-size: 12px;">
                        {status}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.divider()
    else:
        # Empty state with helpful message
        st.markdown("""
        <div class="empty-state">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>
            <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem;">No saved jobs yet</div>
            <div style="color: #9ca3af;">Use the extraction tools below to save your first job!</div>
        </div>
        """, unsafe_allow_html=True)

    # ---------- SELECTED JOB ----------
    if "job_title" in st.session_state and st.session_state.get("selected_job_id"):
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(16,185,129,0.1) 0%, rgba(16,185,129,0.05) 100%); 
                    border-left: 4px solid #10b981; 
                    padding: 1rem; 
                    border-radius: 8px;
                    margin: 1rem 0;">
            📌 <strong>Selected Job:</strong> {st.session_state.job_title}
        </div>
        """, unsafe_allow_html=True)

    # ---------- EXTRACTION ----------
    st.markdown("### 🔍 Extract New Job")
    st.markdown("Add jobs from URLs, text, or files")

    tab1, tab2, tab3 = st.tabs(
        ["🌐 From URL", "📋 Paste Job Description", "📁 Upload File"]
    )

    # -------- TAB 1 --------
    with tab1:
        st.markdown("### Extract from URL")
        url = st.text_input("Job URL", placeholder="https://example.com/job-posting")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            extract_btn = st.button("🚀 Extract", type="primary", use_container_width=True)
        
        if extract_btn:
            if url:
                with st.spinner("Fetching job details..."):
                    details, raw_text, error = extract_job_from_url(url)

                if error:
                    st.error(f"❌ {error}")
                else:
                    render_job_details_ui(details, raw_text)
            else:
                st.warning("⚠️ Please enter a valid URL")

    # -------- TAB 2 --------
    with tab2:
        st.markdown("### Paste Job Description")
        jd_text = st.text_area("Job Description", height=250, placeholder="Paste the complete job description here...")
        
        if st.button("📊 Analyze Text", type="primary", use_container_width=True):
            if jd_text.strip():
                with st.spinner("Analyzing job description..."):
                    details = extract_job_from_text(jd_text)
                render_job_details_ui(details, jd_text)
            else:
                st.warning("⚠️ Please paste a job description")

    # -------- TAB 3 --------
    with tab3:
        st.markdown("### Upload Job File")
        jf = st.file_uploader("Choose file", type=["pdf", "docx", "txt"], help="Supported formats: PDF, DOCX, TXT")

        if jf:
            with st.spinner("Parsing file..."):
                details, raw_text, error = extract_job_from_file(jf)

            if error:
                st.error(f"❌ {error}")
            else:
                st.success("✅ File parsed successfully!")
                if st.button("📊 Analyze File", type="primary", use_container_width=True):
                    with st.spinner("Extracting job details..."):
                        details = extract_job_details(raw_text)
                    render_job_details_ui(details, raw_text)


# ---------------- JOB DETAILS UI ----------------
def render_job_details_ui(details: dict, raw_text: str):
    st.markdown("---")
    st.markdown("### 📋 Job Details")
    st.markdown("Review the extracted information below")

    # Create two columns for main info
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"""
        <div class="job-card">
            <div class="job-title">🎯 {details.get('title', '—')}</div>
            <div class="job-meta">
                <strong>🏢 Company:</strong> {details.get('company', 'Not specified')}<br>
                <strong>📍 Location:</strong> {details.get('location', 'Not specified')}<br>
                <strong>💼 Job Type:</strong> {details.get('job_type', 'Not specified')}
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

    # SKILLS section with better formatting
    if details.get("skills"):
        st.markdown("### 🔧 Required Skills")
        skills = details["skills"]
        # Display skills as chips
        skills_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0;">'
        for skill in skills:
            skills_html += f'<span style="background: linear-gradient(135deg, #10b98120 0%, #10b98110 100%); padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; border: 1px solid #10b98140;">{skill}</span>'
        skills_html += '</div>'
        st.markdown(skills_html, unsafe_allow_html=True)

    # RESPONSIBILITIES
    if details.get("responsibilities"):
        with st.expander("📝 Key Responsibilities", expanded=False):
            for r in details["responsibilities"]:
                st.markdown(f"• {r}")

    # DESCRIPTION
    if details.get("description"):
        with st.expander("📄 Full Description", expanded=False):
            st.write(details["description"])
    
    # Additional details if available
    if details.get("requirements"):
        with st.expander("✅ Requirements", expanded=False):
            for req in details["requirements"]:
                st.markdown(f"• {req}")
    
    if details.get("benefits"):
        with st.expander("🎁 Benefits", expanded=False):
            for benefit in details["benefits"]:
                st.markdown(f"• {benefit}")

    # ---------- SAVE BUTTON ----------
    st.markdown("---")
    col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
    with col_save2:
        if st.button("💾 Save Job", type="primary", use_container_width=True):
            rid = DB.save_job_limited(
                title=details.get("title", "Job"),
                text=raw_text,
                details=details,
                source="manual"
            )

            if rid:
                st.success(f"✅ Job saved successfully!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Failed to save job. Please check database connection.")
# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ATS & Optimizer
# ══════════════════════════════════════════════════════════════════════════════
def page_ats():
    score = 0
    st.markdown(
    f'<div class="score-ring" style="--pct:{score}">{score}</div>',
    unsafe_allow_html=True
)

    if not st.session_state.resume_text:
        st.warning("⚠️ No resume loaded. Go to **Resume Manager** first."); return
    if not st.session_state.job_text:
        st.warning("⚠️ No job description loaded. Go to **Job Extraction** first."); return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="ai-card"><b>📄 Resume:</b> {st.session_state.resume_name or "Loaded"}<br><span style="color:var(--muted)">{len(st.session_state.resume_text):,} chars</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="ai-card"><b>💼 Job:</b> {st.session_state.job_title or "Loaded"}<br><span style="color:var(--muted)">{len(st.session_state.job_text):,} chars</span></div>', unsafe_allow_html=True)

    if st.button("🚀 Run ATS Analysis with LangChain Agent", use_container_width=True):
        with st.spinner("🤖 LangChain agent analyzing your resume..."):
            result = compute_ats(st.session_state.resume_text, st.session_state.job_text)
            st.session_state.ats_result = result
            DB.save_ats(st.session_state.resume_id or "session", st.session_state.job_title, result.get("score",0), result)

    if st.session_state.ats_result:
        r      = st.session_state.ats_result
        score  = r.get("score", 0)
        verdict = r.get("verdict","—")

        st.markdown("---")
        st.markdown("### 📊 ATS Analysis Results")

        cc1, cc2, cc3 = st.columns([1,2,1])
        with cc2:
            render_score_ring(score)
            st.markdown(f'<div style="text-align:center"><span class="pill pill-{"green" if score>=80 else "amber" if score>=55 else "red"}" style="font-size:1rem;padding:6px 18px">{verdict}</span></div>', unsafe_allow_html=True)

        ss = r.get("section_scores",{})
        if ss:
            st.markdown("<br>")
            st.markdown("**Section Breakdown:**")
            for section, val in ss.items():
                sc1, sc2 = st.columns([1,4])
                with sc1: st.caption(section.capitalize())
                with sc2: st.progress(int(val) / 100 if val <= 1 else int(val) / 100)

        kc1, kc2 = st.columns(2)
        with kc1:
            st.markdown("**✅ Matched Keywords:**")
            matched = r.get("matched_keywords",[])
            st.markdown("".join(pill(k,"green") for k in matched[:20]) if matched else "<i>None detected</i>", unsafe_allow_html=True)
        with kc2:
            st.markdown("**❌ Missing Keywords:**")
            missing = r.get("missing_keywords",[])
            st.markdown("".join(pill(k,"red") for k in missing[:20]) if missing else '<span class="pill pill-green">None missing 🎉</span>', unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**💪 Strengths:**")
            for s in r.get("strengths",[]): st.markdown(f"<div style='padding:4px 0'>✅ {s}</div>", unsafe_allow_html=True)
        with sc2:
            st.markdown("**⚠️ Gaps:**")
            gaps = r.get("gaps",[])
            if gaps:
                for g in gaps: st.markdown(f"<div style='padding:4px 0'>⚡ {g}</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="pill pill-green">🎉 No major gaps!</div>', unsafe_allow_html=True)

        recs = r.get("recommendations",[])
        if recs:
            st.markdown("---")
            st.markdown("### 💡 Recommendations")
            for i, rec in enumerate(recs, 1):
                st.markdown(f'<div class="ai-card" style="padding:12px 16px"><span style="color:var(--accent2);font-weight:600">{i}.</span> {rec}</div>', unsafe_allow_html=True)

        # Telegram send
        if TELEGRAM_BOT_TOKEN:
            st.markdown("---")
            tg_cid_ats = st.text_input("Send ATS report to Telegram chat:", value=TELEGRAM_CHAT_ID, key="ats_tg")
            if st.button("📱 Send ATS Report to Telegram"):
                ok, err = tg_ats(
                    name=st.session_state.resume_name or "Resume",
                    score=score,
                    verdict=verdict,
                    matched=r.get("matched_keywords",[]),
                    missing=r.get("missing_keywords",[]),
                    recommendations=recs,
                    chat_id=tg_cid_ats,
                )
                st.success("✅ ATS report sent to Telegram!") if ok else st.error(f"Error: {err}")

        # Optimizer
        st.markdown("---")
        st.markdown("### ✨ Resume Optimization")
        opt_c1, opt_c2 = st.columns([3,1])
        with opt_c1:
            user_instructions = st.text_input("Additional instructions (optional)", placeholder="e.g. Emphasize leadership, add Python skills...")
        with opt_c2:
            st.markdown("<br>", unsafe_allow_html=True)
            do_optimize = st.button("⚡ Optimize Resume", use_container_width=True)

        if do_optimize:
            if score >= 90:
                st.markdown(f'<div class="ai-card" style="border-color:rgba(16,185,129,.4)">🎉 <b>Score {score}/100 — Already Excellent!</b><br><div style="color:var(--muted);margin-top:8px">Your resume is highly optimized. No major changes needed.</div></div>', unsafe_allow_html=True)
            else:
                with st.spinner("✨ Groq LLM optimizing your resume..."):
                    optimized = optimize_resume(st.session_state.resume_text, st.session_state.job_text, user_instructions)
                    st.session_state.optimized_resume = optimized
                st.success("✅ Resume optimized!")
                st.text_area("🚀 Optimized Resume", optimized, height=400)
                dl_col, tg_col = st.columns(2)
                with dl_col:
                    
                    st.download_button("📥 Download", optimized.encode(), f"optimized_resume.txt", "text/plain")
                    st.markdown("<br>", unsafe_allow_html=True)

                    opt_name = st.text_input(
                        "Enter name for optimized resume",
                        value=f"Optimized_{st.session_state.resume_name or 'Resume'}",
                        key="opt_resume_name"
                    )

                    if st.button("💾 Save Optimized Resume to MongoDB"):
                        rid = DB.save_optimized_resume(
                            name=opt_name,
                            text=optimized,
                            meta={
                                "source": "optimizer",
                                "original_resume_id": st.session_state.resume_id,
                                "job_title": st.session_state.job_title,
                                "ats_score": score
                            }
                        )
                        if rid:
                            st.success(f"✅ Optimized resume saved! ID: `{rid}`")
                        else:
                            st.warning("MongoDB not connected — resume not saved.")
                with tg_col:
                    if TELEGRAM_BOT_TOKEN and st.button("📱 Send to Telegram"):
                        ok, err = tg_doc(optimized.encode(), "optimized_resume.txt", "🚀 Your optimized resume!", chat_id=TELEGRAM_CHAT_ID)
                        st.success("Sent!") if ok else st.error(err)

        # Cover letter
        st.markdown("---")
        st.markdown("### 📝 Cover Letter Generator")
        cname = st.text_input("Your name (for cover letter)", placeholder="John Doe")
        if st.button("✍️ Generate Cover Letter"):
            with st.spinner("Writing cover letter..."):
                details = st.session_state.get("job_details", {})
                job_context = f"""
                Job Title: {details.get("title","")}
                Company: {details.get("company","")}

                Key Skills:
                {", ".join(details.get("skills", []))}

                Requirements:
                {chr(10).join(details.get("requirements", []))}

                Responsibilities:
                {chr(10).join(details.get("responsibilities", []))}
                """

                cover = generate_cover_letter(
                    st.session_state.resume_text,
                    job_context,
                    cname
                )
                cover = generate_cover_letter(st.session_state.resume_text, st.session_state.job_text, cname)
            st.text_area("Cover Letter", cover, height=350)
            st.download_button("📥 Download Cover Letter", cover.encode(), "cover_letter.txt")

        # LinkedIn optimizer
        st.markdown("---")
        st.markdown("### 🔗 LinkedIn Profile Optimizer")
        if st.button("🔗 Optimize LinkedIn Profile"):
            with st.spinner("Optimizing LinkedIn..."):
                linkedin = improve_linkedin(st.session_state.resume_text, st.session_state.job_text)
            st.text_area("LinkedIn Suggestions", linkedin, height=250)

        # Generate from template----------------------------------------------------------------------------------------------------
        if st.session_state.template_text:
            st.markdown("---")
            st.markdown("### 📋 Generate New Resume from Template")
            if st.button("🔨 Generate Complete New Resume"):
                with st.spinner("Building resume..."):
                    new_res = generate_new_resume(st.session_state.resume_text, st.session_state.job_text, st.session_state.template_text)
                st.text_area("🆕 Generated Resume", new_res, height=400)
                st.download_button("📥 Download", new_res.encode(), "new_resume.md")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Email Automation
# ══════════════════════════════════════════════════════════════════════════════
def page_email():
    st.markdown('<p class="section-header">📧 Email Automation</p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📤 Send Resume", "📥 Detect Job Responses"])

    with tab1:
        st.markdown("#### Send Your Resume via Email")
        ec1, ec2 = st.columns(2)
        with ec1:
            to_email    = st.text_input("Recipient Email", placeholder="recruiter@company.com")
            job_title_e = st.text_input("Job Title", value=st.session_state.job_title or "")
        with ec2:
            candidate = st.text_input("Your Name", placeholder="John Doe")
            subject_e = st.text_input("Email Subject", value=f"Application for {st.session_state.job_title or 'Position'}")

        resume_choice = st.radio("Which resume to send?", ["Current Session Resume", "Optimized Resume (if generated)"])
        if st.checkbox("Preview email body"):
            resume_prev = st.session_state.optimized_resume or st.session_state.resume_text
            st.markdown(resume_email_html(candidate or "Candidate", job_title_e, resume_prev), unsafe_allow_html=True)

        if st.button("📤 Send Email", use_container_width=True):
            if not to_email: st.warning("Enter recipient email."); return
            res_to_send = (st.session_state.optimized_resume if resume_choice.startswith("Optimized") else st.session_state.resume_text) or ""
            if not res_to_send: st.warning("No resume loaded."); return
            body_html   = resume_email_html(candidate or "Candidate", job_title_e, res_to_send)
            with st.spinner("Sending email..."):
                ok = send_email(to_email, subject_e, body_html, res_to_send.encode(), f"resume_{candidate or 'candidate'}.txt")
            if ok:
                st.success(f"✅ Email sent to {to_email}!")
                st.session_state.notifications.append({"type":"email","to":to_email,"ts":str(datetime.now())[:19]})

    with tab2:
        st.markdown("#### 📥 Detect Job Selection Emails")
        st.markdown(f'<div class="ai-card"><b>📧 Monitoring:</b> {EMAIL_ADDR or "Not configured"}<br><span style="color:var(--muted)">Checks for: offers, interviews, rejections, selections, shortlists</span></div>', unsafe_allow_html=True)

        limit = st.slider("Emails to scan", 5, 50, 20)
        if st.button("🔍 Scan Inbox", use_container_width=True):
            if not (EMAIL_ADDR and EMAIL_PASS):
                st.error("Email credentials not configured."); return
            with st.spinner("Scanning inbox..."):
                responses = check_inbox_for_job_responses(limit)
            if not responses:
                st.info("No job-related emails found.")
            else:
                st.success(f"Found {len(responses)} job-related emails!")
                for i, resp in enumerate(responses):
                    sentiment = resp.get("sentiment","neutral")
                    icon  = "🎉" if sentiment=="positive" else "😔" if sentiment=="negative" else "📩"
                    color = "green" if sentiment=="positive" else "red" if sentiment=="negative" else "blue"
                    with st.expander(f"{icon} {resp['subject'][:60]} — {resp['sender'][:40]}"):
                        st.markdown(f"**Sentiment:** " + pill(sentiment.upper(), color), unsafe_allow_html=True)
                        st.markdown(f"**Signals:** " + "".join(pill(m,"amber") for m in resp.get("matched",[])), unsafe_allow_html=True)
                        st.markdown(f"**Preview:** {resp.get('body','')[:300]}...")
                        if st.button("🤖 AI Analysis", key=f"ai_{i}"):
                            with st.spinner("Analyzing..."):
                                analysis = groq_chat(f"Analyze this job email: 1) Type (offer/rejection/interview), 2) Action required, 3) Urgency, 4) Recommended response.\n\nSubject: {resp['subject']}\nBody: {resp['body'][:1000]}")
                            st.markdown(f'<div class="ai-card">{analysis}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — Telegram Bot
# ══════════════════════════════════════════════════════════════════════════════
def page_telegram():
    st.markdown('<p class="section-header">📱 Telegram Bot Automation</p>', unsafe_allow_html=True)

    # Bot status
    is_configured = bool(TELEGRAM_BOT_TOKEN)
    st.markdown(f'<div class="ai-card"><b>🤖 Telegram Bot</b><br>Token: <code>{"✅ Configured" if is_configured else "❌ Not configured"}</code><br>Default Chat ID: <code>{TELEGRAM_CHAT_ID or "Not set"}</code><br>Status: {status_indicator("Ready" if is_configured else "Setup required", is_configured)}</div>', unsafe_allow_html=True)

    if is_configured:
        ok, info = tg_test()
        if ok:
            st.success(f"✅ Bot connected: {info}")
        else:
            st.error(f"❌ Bot connection failed: {info}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 Send Message", "📊 Send ATS Report", "🤖 Bot Commands", "📡 Live Polling", "⚙️ Webhook"])

    with tab1:
        st.markdown("#### Send Message via Telegram")
        tg_to  = st.text_input("Chat ID", value=TELEGRAM_CHAT_ID, placeholder="-1001234567890 or @username")
        tg_msg = st.text_area("Message", placeholder="Type your message...", height=150)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📱 Send Message", use_container_width=True):
                if tg_to and tg_msg:
                    ok, err = tg_send(tg_msg, chat_id=tg_to)
                    if ok:
                        st.success("✅ Message sent!")
                        st.session_state.tg_messages.append({"to":tg_to,"msg":tg_msg,"ts":str(datetime.now())[:19],"status":"sent"})
                    else:
                        st.error(f"Failed: {err}")
                else:
                    st.warning("Enter chat ID and message.")
        with c2:
            if st.button("📄 Send Current Resume", use_container_width=True):
                if st.session_state.resume_text and tg_to:
                    ok, err = tg_doc(
                        st.session_state.resume_text.encode(),
                        f"{st.session_state.resume_name or 'resume'}.txt",
                        f"📄 *{st.session_state.resume_name or 'Resume'}*",
                        chat_id=tg_to,
                    )
                    st.success("Resume sent!") if ok else st.error(err)
                else:
                    st.warning("Load a resume first.")

        if st.session_state.tg_messages:
            st.markdown("---")
            st.markdown("**📜 Sent Messages:**")
            for m in reversed(st.session_state.tg_messages[-5:]):
                st.markdown(f'<div class="ai-card" style="padding:10px"><code>To: {m["to"]}</code> <span style="color:var(--muted)">{m["ts"]}</span><br>{m["msg"][:80]}...</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("#### 📊 Send ATS Report to Telegram")
        if not st.session_state.ats_result:
            st.info("Run ATS analysis first.")
        else:
            r     = st.session_state.ats_result
            tg_c2 = st.text_input("Send to chat", value=TELEGRAM_CHAT_ID, key="ats_tg2")
            st.markdown("**Message Preview:**")
            preview = format_ats_telegram(
                st.session_state.resume_name or "Resume",
                r.get("score",0),
                r.get("verdict","—"),
                r.get("recommendations",[]),
            )
            st.code(preview)
            if st.button("📱 Send ATS Report", use_container_width=True):
                ok, err = tg_ats(
                    name=st.session_state.resume_name or "Resume",
                    score=r.get("score",0),
                    verdict=r.get("verdict","—"),
                    matched=r.get("matched_keywords",[]),
                    missing=r.get("missing_keywords",[]),
                    recommendations=r.get("recommendations",[]),
                    chat_id=tg_c2,
                )
                st.success("✅ ATS report sent!") if ok else st.error(f"Error: {err}")

    with tab3:
        st.markdown("#### 🤖 Available Bot Commands")
        for cmd, desc in TELEGRAM_COMMANDS:
            st.markdown(f'<div class="ai-card" style="display:flex;gap:16px;align-items:center"><code style="color:var(--accent2);min-width:150px">{cmd}</code><span style="color:var(--muted)">{desc}</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🧪 Test Bot Command")
        test_cmd = st.selectbox("Command to test:", [c for c, _ in TELEGRAM_COMMANDS])
        test_chat = st.text_input("Test Chat ID", value=TELEGRAM_CHAT_ID, key="test_chat")
        if st.button("▶️ Run Command"):
            if test_chat:
                with st.spinner("Processing..."):
                    reply = process_bot_command(test_cmd, test_chat, st.session_state)
                st.success("Command processed!")
                st.code(reply)
            else:
                st.warning("Enter a chat ID.")

    with tab4:
        st.markdown("#### 📡 Live Message Polling")
        st.caption("Poll your bot for new messages and auto-process commands")

        poll_interval = st.slider("Poll interval (seconds)", 3, 30, 5)
        if st.button("▶️ Fetch Recent Updates"):
            updates = get_updates(limit=10)
            if not updates:
                st.info("No new messages.")
            else:
                st.success(f"{len(updates)} update(s) found:")
                for u in updates:
                    msg  = u.get("message",{})
                    text = msg.get("text","")
                    who  = msg.get("from",{}).get("first_name","User")
                    cid  = str(msg.get("chat",{}).get("id",""))
                    if text:
                        st.markdown(f'<div class="ai-card"><b>{who}</b> (chat: <code>{cid}</code>)<br><code>{text}</code></div>', unsafe_allow_html=True)
                        if st.button(f"↩️ Reply to: {text[:30]}", key=f"reply_{u['update_id']}"):
                            reply = process_bot_command(text, cid, st.session_state)
                            st.info(f"Reply sent: {reply[:100]}")

    with tab5:
        st.markdown("#### ⚙️ Webhook Configuration")
        wh_url = st.text_input("Webhook URL", placeholder="https://your-app.streamlit.app/webhook/telegram")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔗 Set Webhook"):
                if wh_url:
                    ok, msg = set_webhook(wh_url)
                    st.success(msg) if ok else st.error(msg)
        with c2:
            if st.button("❌ Delete Webhook"):
                ok, msg = delete_webhook()
                st.success(msg) if ok else st.error(msg)

        st.markdown("""
        <div class="ai-card">
        <b>📖 Webhook Setup Guide</b><br><br>
        1. Deploy this app to a public URL (e.g., Streamlit Cloud)<br>
        2. Set webhook to: <code>https://YOUR_APP_URL/webhook/telegram</code><br>
        3. Or use polling mode (no webhook needed for Streamlit)<br><br>
        <b>How to get your Chat ID:</b><br>
        • Message @userinfobot on Telegram — it replies with your ID<br>
        • For groups: add @userinfobot to the group
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — AI Agent Chat
# ══════════════════════════════════════════════════════════════════════════════
def page_agent():
    st.markdown('<p class="section-header">🤖 AI Agent Chat</p>', unsafe_allow_html=True)
    st.caption(f"Powered by LangChain + Groq {MAIN_MODEL}")

    # Voice input
    if ENABLE_VOICE:
        with st.expander("🎙️ Voice Input"):
            voice_input_widget()

    # Chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
            st.markdown(msg["content"])

    # Quick prompts
    if not st.session_state.chat_history:
        st.markdown("**Try these:**")
        qs = ["Analyze my resume strengths", "What keywords am I missing?", "How can I improve my ATS score?", "Generate a cover letter", "Optimize my LinkedIn summary", "What jobs match my resume?"]
        cols = st.columns(3)
        for col, q in zip(cols * 2, qs):
            if col.button(q, use_container_width=True):
                st.session_state._quick_prompt = q

    user_input = st.chat_input("Ask about your resume, jobs, ATS optimization...")
    if hasattr(st.session_state, "_quick_prompt"):
        user_input = st.session_state._quick_prompt
        del st.session_state._quick_prompt

    if user_input:
        st.session_state.chat_history.append({"role":"user","content":user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                context = (
                    f"\nContext:\n"
                    f"Resume: {st.session_state.resume_text[:600] if st.session_state.resume_text else 'None loaded'}\n"
                    f"Job: {st.session_state.job_text[:400] if st.session_state.job_text else 'None loaded'}\n"
                    f"ATS Score: {st.session_state.ats_result.get('score','N/A') if st.session_state.ats_result else 'Not analyzed'}\n\n"
                    f"User: {user_input}"
                )
                response = groq_chat(
                    context,
                    "You are ResumeAI Pro, an expert career assistant. Use the context about the user's resume and job. Be specific, actionable, and encouraging.",
                )
            st.markdown(response)
            st.session_state.chat_history.append({"role":"assistant","content":response})

    c1, c2 = st.columns([1,5])
    with c1:
        if st.session_state.chat_history and st.button("🗑️ Clear"):
            st.session_state.chat_history = []
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — Settings
# ══════════════════════════════════════════════════════════════════════════════
def page_settings():
    st.markdown('<p class="section-header">⚙️ Settings & Configuration</p>', unsafe_allow_html=True)
    st.markdown("### 🔑 Credential Status")
    for key, (ok, desc) in credential_status().items():
        st.markdown(f'<div class="ai-card" style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px"><div><code style="color:var(--accent2)">{key}</code><div style="color:var(--muted);font-size:.8rem">{desc}</div></div>{status_indicator("Configured" if ok else "Missing", ok)}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🚀 ResumeAI Pro</div>', unsafe_allow_html=True)

    if st.session_state.resume_text:
        st.markdown(f'<div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);border-radius:8px;padding:8px 12px;margin-bottom:8px;font-size:.82rem"><span class="status-dot dot-green"></span><b>{(st.session_state.resume_name or "Resume")[:22]}</b></div>', unsafe_allow_html=True)
    if st.session_state.job_text:
        st.markdown(f'<div style="background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.3);border-radius:8px;padding:8px 12px;margin-bottom:8px;font-size:.82rem"><span class="status-dot dot-green" style="background:var(--accent)"></span><b>{(st.session_state.job_title or "Job")[:22]} loaded</b></div>', unsafe_allow_html=True)

    nav_items = [
        ("dashboard", "🏠", "Dashboard"),
        ("resume",    "📄", "Resume Manager"),
        ("jobs",      "🔍", "Job Extraction"),
        ("ats",       "🎯", "ATS & Optimizer"),
        ("email",     "📧", "Email Automation"),
        ("telegram",  "📱", "Telegram Bot"),
        ("agent",     "🤖", "AI Agent Chat"),
        ("settings",  "⚙️", "Settings"),
    ]
    for page_id, icon, label in nav_items:
        active = st.session_state.page == page_id
        style  = "border:1px solid rgba(99,102,241,.5);background:rgba(99,102,241,.15);" if active else ""
        if st.button(f"{icon}  {label}", key=f"nav_{page_id}", use_container_width=True):
            st.session_state.page = page_id
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
# Ensure the main content starts from the top by adding an empty element
st.markdown('<div style="height: 0px;"></div>', unsafe_allow_html=True)

PAGE_MAP = {
    "dashboard": page_dashboard,
    "resume":    page_resume,
    "jobs":      page_jobs,
    "ats":       page_ats,
    "email":     page_email,
    "telegram":  page_telegram,
    "agent":     page_agent,
    "settings":  page_settings,
}
PAGE_MAP.get(st.session_state.page, page_dashboard)()
