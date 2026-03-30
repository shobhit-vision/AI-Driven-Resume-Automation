"""
telegram_bot.py — ResumeAI Pro · Telegram Bot Automation Module
Full Telegram bot integration: send messages, receive commands, process jobs via bot.
Uses python-telegram-bot (async) and httpx for direct API calls (no async needed in Streamlit).
"""

import json
import time
import threading
from typing import Optional
from datetime import datetime

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_COMMANDS

# ─────────────────────────────────────────────────────────────────────────────
# Core Telegram API (sync, httpx-free, works inside Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _tg(method: str, payload: dict = None, token: str = None) -> dict:
    """
    Low-level Telegram Bot API call.
    Returns parsed JSON response or {'ok': False, 'description': error}.
    """
    t = token or TELEGRAM_BOT_TOKEN
    if not t:
        return {"ok": False, "description": "TELEGRAM_BOT_TOKEN not configured"}
    if not REQUESTS_OK:
        return {"ok": False, "description": "requests not installed"}
    url = TELEGRAM_API.format(token=t, method=method)
    try:
        resp = requests.post(url, json=payload or {}, timeout=15)
        return resp.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Send helpers
# ─────────────────────────────────────────────────────────────────────────────

def send_message(
    text: str,
    chat_id: str = None,
    parse_mode: str = "Markdown",
    disable_preview: bool = True,
    token: str = None,
) -> tuple[bool, str]:
    """
    Send a text message to a Telegram chat.
    Returns (success, error_message).
    """
    cid = chat_id or TELEGRAM_CHAT_ID
    if not cid:
        return False, "No chat_id provided and TELEGRAM_CHAT_ID not configured"
    result = _tg(
        "sendMessage",
        {
            "chat_id":                  cid,
            "text":                     text,
            "parse_mode":               parse_mode,
            "disable_web_page_preview": disable_preview,
        },
        token=token,
    )
    if result.get("ok"):
        return True, ""
    return False, result.get("description", "Unknown error")


def send_document(
    file_bytes: bytes,
    filename: str,
    caption: str = "",
    chat_id: str = None,
    token: str = None,
) -> tuple[bool, str]:
    """Send a file/document to a Telegram chat."""
    t = token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID
    if not (t and cid):
        return False, "Token or chat_id not configured"
    url = TELEGRAM_API.format(token=t, method="sendDocument")
    try:
        resp = requests.post(
            url,
            data={"chat_id": cid, "caption": caption, "parse_mode": "Markdown"},
            files={"document": (filename, file_bytes, "application/octet-stream")},
            timeout=30,
        )
        result = resp.json()
        if result.get("ok"):
            return True, ""
        return False, result.get("description", "Unknown error")
    except Exception as e:
        return False, str(e)


def send_photo(
    image_bytes: bytes,
    caption: str = "",
    chat_id: str = None,
    token: str = None,
) -> tuple[bool, str]:
    """Send an image to a Telegram chat."""
    t = token or TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID
    if not (t and cid):
        return False, "Token or chat_id not configured"
    url = TELEGRAM_API.format(token=t, method="sendPhoto")
    try:
        resp = requests.post(
            url,
            data={"chat_id": cid, "caption": caption, "parse_mode": "Markdown"},
            files={"photo": ("photo.png", image_bytes, "image/png")},
            timeout=30,
        )
        result = resp.json()
        if result.get("ok"):
            return True, ""
        return False, result.get("description", "Unknown error")
    except Exception as e:
        return False, str(e)


def send_ats_report(
    name: str,
    score: int,
    verdict: str,
    matched: list,
    missing: list,
    recommendations: list,
    chat_id: str = None,
    token: str = None,
) -> tuple[bool, str]:
    """Send a formatted ATS report to Telegram."""
    emoji = "🟢" if score >= 80 else "🟡" if score >= 55 else "🔴"
    matched_str  = ", ".join(matched[:10]) or "—"
    missing_str  = ", ".join(missing[:10]) or "None 🎉"
    recs_str     = "\n".join(f"{i+1}. {r}" for i, r in enumerate(recommendations[:4]))
    msg = (
        f"🚀 *ResumeAI Pro — ATS Report*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 *Resume:* {name}\n"
        f"{emoji} *Score:* `{score}/100` — {verdict}\n\n"
        f"✅ *Matched Keywords:*\n`{matched_str}`\n\n"
        f"❌ *Missing Keywords:*\n`{missing_str}`\n\n"
        f"💡 *Recommendations:*\n{recs_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Generated by ResumeAI Pro_"
    )
    return send_message(msg, chat_id=chat_id, token=token)


def send_job_details(
    details: dict,
    chat_id: str = None,
    token: str = None,
) -> tuple[bool, str]:
    """Send extracted job details to Telegram."""
    skills    = ", ".join(details.get("skills", [])[:8]) or "—"
    reqs      = "\n".join(f"• {r}" for r in details.get("requirements", [])[:5])
    msg = (
        f"💼 *Job Extracted — ResumeAI Pro*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *{details.get('title', 'Position')}*\n"
        f"🏛 Company: {details.get('company', '—')}\n"
        f"📍 Location: {details.get('location', '—')}\n"
        f"⏱ Type: {details.get('job_type', '—')}\n"
        f"💰 Salary: {details.get('salary', 'Not specified')}\n"
        f"📚 Experience: {details.get('experience', '—')}\n\n"
        f"🛠 *Skills:* `{skills}`\n\n"
        f"📋 *Requirements:*\n{reqs}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Use ATS tab to score your resume against this job_"
    )
    return send_message(msg, chat_id=chat_id, token=token)


# ─────────────────────────────────────────────────────────────────────────────
# Bot info & webhook
# ─────────────────────────────────────────────────────────────────────────────

def get_bot_info(token: str = None) -> dict:
    """Get bot username and name."""
    result = _tg("getMe", token=token)
    if result.get("ok"):
        return result.get("result", {})
    return {}


def test_connection(token: str = None) -> tuple[bool, str]:
    """Test if the bot token is valid."""
    info = get_bot_info(token)
    if info:
        return True, f"@{info.get('username', 'bot')} ({info.get('first_name', '')})"
    return False, "Invalid token or no connection"


def set_webhook(webhook_url: str, token: str = None) -> tuple[bool, str]:
    """Set a webhook URL for the bot."""
    result = _tg("setWebhook", {"url": webhook_url}, token=token)
    if result.get("ok"):
        return True, "Webhook set successfully"
    return False, result.get("description", "Failed to set webhook")


def delete_webhook(token: str = None) -> tuple[bool, str]:
    """Remove the webhook (switch to polling)."""
    result = _tg("deleteWebhook", token=token)
    if result.get("ok"):
        return True, "Webhook removed"
    return False, result.get("description", "Failed to remove webhook")


def get_updates(offset: int = 0, limit: int = 10, token: str = None) -> list:
    """Get pending updates (messages sent to bot)."""
    result = _tg("getUpdates", {"offset": offset, "limit": limit, "timeout": 5}, token=token)
    if result.get("ok"):
        return result.get("result", [])
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Command processor (processes messages received by the bot)
# ─────────────────────────────────────────────────────────────────────────────

def process_bot_command(
    message_text: str,
    chat_id: str,
    session_state,
    token: str = None,
) -> str:
    """
    Process an incoming Telegram message / command.
    Returns the reply text (also sends it to Telegram).
    Integrates with Streamlit session_state for resume/job/ATS data.
    """
    from resume import compute_ats, format_ats_telegram
    from jobs import extract_job_from_url

    text = message_text.strip()
    cmd  = text.upper()

    # ── HELP ─────────────────────────────────────────────────────────────────
    if cmd in ("HELP", "/HELP", "/START"):
        cmds_list = "\n".join(f"`{c}` — {d}" for c, d in TELEGRAM_COMMANDS)
        reply = (
            f"🚀 *ResumeAI Pro Bot*\n\n"
            f"Available commands:\n{cmds_list}\n\n"
            f"_Send any job URL prefixed with_ `JOB:` _to analyze it._"
        )
        send_message(reply, chat_id=chat_id, token=token)
        return reply

    # ── STATUS ────────────────────────────────────────────────────────────────
    if cmd in ("STATUS", "/STATUS"):
        resume_ok = bool(getattr(session_state, "resume_text", ""))
        job_ok    = bool(getattr(session_state, "job_text", ""))
        ats_score = ""
        if getattr(session_state, "ats_result", None):
            ats_score = f"\n🎯 Last ATS Score: `{session_state.ats_result.get('score', 0)}/100`"
        reply = (
            f"📊 *ResumeAI Pro Status*\n"
            f"📄 Resume: {'✅ Loaded' if resume_ok else '❌ Not loaded'}\n"
            f"💼 Job: {'✅ Loaded' if job_ok else '❌ Not loaded'}"
            f"{ats_score}"
        )
        send_message(reply, chat_id=chat_id, token=token)
        return reply

    # ── RESUME SUMMARY ────────────────────────────────────────────────────────
    if cmd in ("RESUME", "/RESUME"):
        resume_text = getattr(session_state, "resume_text", "")
        if not resume_text:
            reply = "⚠️ No resume loaded. Please upload or paste your resume in the app first."
        else:
            from resume import groq_chat
            summary = groq_chat(
                f"Summarize this resume in 5 bullet points:\n\n{resume_text[:2000]}",
                "You are a career expert. Be concise and highlight key strengths.",
            )
            reply = f"📄 *Resume Summary:*\n\n{summary}"
        send_message(reply, chat_id=chat_id, token=token)
        return reply

    # ── ATS SCORE ─────────────────────────────────────────────────────────────
    if cmd in ("ATS", "/ATS"):
        ats_result = getattr(session_state, "ats_result", None)
        if not ats_result:
            reply = "⚠️ No ATS analysis found. Run ATS analysis in the app first."
        else:
            ok, err = send_ats_report(
                name=getattr(session_state, "resume_name", "Resume"),
                score=ats_result.get("score", 0),
                verdict=ats_result.get("verdict", "—"),
                matched=ats_result.get("matched_keywords", []),
                missing=ats_result.get("missing_keywords", []),
                recommendations=ats_result.get("recommendations", []),
                chat_id=chat_id,
                token=token,
            )
            return "ATS report sent!" if ok else f"Error: {err}"
        send_message(reply, chat_id=chat_id, token=token)
        return reply

    # ── OPTIMIZE ──────────────────────────────────────────────────────────────
    if cmd in ("OPTIMIZE", "/OPTIMIZE"):
        resume_text = getattr(session_state, "resume_text", "")
        job_text    = getattr(session_state, "job_text", "")
        if not resume_text:
            reply = "⚠️ No resume loaded."
        elif not job_text:
            reply = "⚠️ No job loaded. Please load a job description in the app."
        else:
            reply = "⏳ Optimizing your resume... This takes ~30 seconds. Check the app for results."
        send_message(reply, chat_id=chat_id, token=token)
        return reply

    # ── COVER LETTER ──────────────────────────────────────────────────────────
    if cmd in ("COVER", "/COVER"):
        resume_text = getattr(session_state, "resume_text", "")
        job_text    = getattr(session_state, "job_text", "")
        if not resume_text or not job_text:
            reply = "⚠️ Load both resume and job description in the app first."
        else:
            from resume import generate_cover_letter
            cover = generate_cover_letter(resume_text, job_text)
            reply = f"📝 *Cover Letter:*\n\n{cover[:2000]}"
        send_message(reply, chat_id=chat_id, token=token)
        return reply

    # ── JOB: <url> ────────────────────────────────────────────────────────────
    if text.upper().startswith("JOB:") or text.upper().startswith("/JOB"):
        url = text.split(":", 1)[-1].strip() if ":" in text else text.split()[-1]
        if not url.startswith("http"):
            reply = "⚠️ Please provide a valid URL. Example: `JOB: https://linkedin.com/jobs/...`"
            send_message(reply, chat_id=chat_id, token=token)
            return reply
        send_message("⏳ Extracting job details... Please wait.", chat_id=chat_id, token=token)
        details, raw_text, error = extract_job_from_url(url)
        if error:
            reply = f"❌ Could not extract job: {error}"
            send_message(reply, chat_id=chat_id, token=token)
            return reply
        # Update session state
        if hasattr(session_state, "job_text"):
            session_state.job_text  = raw_text
            session_state.job_title = details.get("title", "Job")
        ok, err = send_job_details(details, chat_id=chat_id, token=token)
        return "Job extracted and sent!" if ok else f"Extracted but send failed: {err}"

    # ── Unknown ───────────────────────────────────────────────────────────────
    reply = (
        "🤔 Unknown command. Send `HELP` to see all available commands."
    )
    send_message(reply, chat_id=chat_id, token=token)
    return reply


# ─────────────────────────────────────────────────────────────────────────────
# Polling (background thread for Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

class TelegramPoller:
    """
    Background thread that polls for new Telegram messages and
    processes commands. Used when no webhook is configured.
    """

    def __init__(self, session_state, token: str = None, interval: int = 5):
        self.session_state = session_state
        self.token         = token or TELEGRAM_BOT_TOKEN
        self.interval      = interval
        self._offset       = 0
        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self.received      = []   # list of processed messages

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _poll_loop(self):
        while self._running:
            try:
                updates = get_updates(offset=self._offset, limit=10, token=self.token)
                for update in updates:
                    self._offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    if msg:
                        text    = msg.get("text", "")
                        chat_id = str(msg["chat"]["id"])
                        if text:
                            reply = process_bot_command(
                                text, chat_id, self.session_state, token=self.token
                            )
                            self.received.append({
                                "from":    msg.get("from", {}).get("first_name", "User"),
                                "text":    text,
                                "reply":   reply,
                                "time":    datetime.now().strftime("%H:%M:%S"),
                                "chat_id": chat_id,
                            })
            except Exception:
                pass
            time.sleep(self.interval)