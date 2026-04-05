

import re
import json
import base64
from io import BytesIO
from typing import Optional

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import PyPDF2
    import pdfplumber
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    from docx import Document as DocxDocument
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

try:
    from groq import Groq
    GROQ_OK = True
except ImportError:
    GROQ_OK = False

try:
    from langchain_groq import ChatGroq
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.tools import tool
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.schema import HumanMessage, SystemMessage
    LANGCHAIN_OK = True
except ImportError:
    LANGCHAIN_OK = False

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

from settings import GROQ_KEY, MAIN_MODEL, VISION_MODEL, ATS_RESUME_CHARS, ATS_JOB_CHARS

# ─────────────────────────────────────────────────────────────────────────────
# File parsers
# ─────────────────────────────────────────────────────────────────────────────

def parse_pdf(file_bytes: bytes) -> str:
    if not PDF_OK:
        return "[PDF libraries not installed – run: pip install pdfplumber PyPDF2]"
    text = ""
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception:
        try:
            reader = PyPDF2.PdfReader(BytesIO(file_bytes))
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        except Exception as e:
            return f"[Error parsing PDF: {e}]"
    return text.strip()


def parse_docx(file_bytes: bytes) -> str:
    if not DOCX_OK:
        return "[python-docx not installed – run: pip install python-docx]"
    try:
        doc = DocxDocument(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return f"[Error parsing DOCX: {e}]"


def parse_resume_file(uploaded_file) -> str:
    """Parse a Streamlit uploaded file (PDF / DOCX / TXT) and return text."""
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    data = uploaded_file.read()
    if ext == "pdf":
        return parse_pdf(data)
    elif ext == "docx":
        return parse_docx(data)
    elif ext == "txt":
        return data.decode("utf-8", errors="ignore")
    return "[Unsupported file format. Use PDF, DOCX, or TXT]"


#Parsing resume through llm
def build_resume_parser_prompt(text):
    return f"""
You are an advanced ATS resume parser.

Extract structured information from the resume below.

Return ONLY valid JSON. No explanation, no markdown.

Format:
{{
  "name": "",
  "email": "",
  "phone": "",
  "linkedin_url": "",
  "github_url": "",
  "address": "",
  "profile_summary": "",
  "skills": {{
    "technical_skills": [],
    "core_competencies": [],
    "soft_skills": []
  }},
  "experience": "",
  "projects": "",
  "education": "",
  "certifications": "",
  "other": ""
}}

Rules:
- Map different headings to standard fields:
  - "Skills", "Technical Skills", "Expertise" → skills
  - "Work Experience", "Professional Experience" → experience
  - "Profile", "Summary" → profile_summary
- Extract exact content, do not rewrite
- Skills MUST be arrays (lists)
- Do NOT hallucinate missing data
- If not found, return empty string "" or empty list []
- Keep original wording and formatting

Resume:
{text}
"""


def parse_resume_with_llm(text):
    prompt = build_resume_parser_prompt(text)
    client = Groq(api_key=GROQ_KEY)
    response = client.chat.completions.create(
        model=MAIN_MODEL,  # or your model
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except:
        return {"error": "Invalid JSON", "raw": content}
    
# 🔹 Clean text
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text.strip()

def safe_json_load(content):
    try:
        return json.loads(content)
    except:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return {"error": "Parsing failed", "raw": content}


# ─────────────────────────────────────────────────────────────────────────────
# Core LLM helpers
# ─────────────────────────────────────────────────────────────────────────────

def groq_chat(prompt: str, system: str = "", model: str = None, max_tokens: int = 4096) -> str:
    """Direct Groq LLM call."""
    if not (GROQ_OK and GROQ_KEY):
        return "[Groq unavailable – set GROQ_API_KEY in settings.py or secrets]"
    try:
        client = Groq(api_key=GROQ_KEY)
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=model or MAIN_MODEL,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM Error: {e}]"


def groq_vision(image_bytes: bytes, prompt: str) -> str:
    """Groq vision model call for resume image analysis."""
    if not (GROQ_OK and GROQ_KEY):
        return "[Vision unavailable – Groq not configured]"
    try:
        b64 = base64.b64encode(image_bytes).decode()
        client = Groq(api_key=GROQ_KEY)
        resp = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[Vision error: {e}]"


# ─────────────────────────────────────────────────────────────────────────────
# LangChain Agent
# ─────────────────────────────────────────────────────────────────────────────

def build_resume_agent() -> Optional["AgentExecutor"]:
    """Build a LangChain agent with resume-specific tools."""
    if not (LANGCHAIN_OK and GROQ_KEY):
        return None
    try:
        llm = ChatGroq(api_key=GROQ_KEY, model=MAIN_MODEL, temperature=0.3)

        @tool
        def extract_job_requirements(job_text: str) -> str:
            """Extract structured job requirements from raw job description text."""
            return groq_chat(
                f"Extract: title, company, required skills, preferred skills, "
                f"experience, education, responsibilities, salary. Return as JSON.\n\nJOB:\n{job_text[:3000]}",
                "You are an expert job analyzer. Always return valid JSON.",
            )

        @tool
        def score_resume_against_job(resume_and_job: str) -> str:
            """Score a resume against a job description and return ATS analysis."""
            return groq_chat(
                resume_and_job,
                "You are an expert ATS system. Return JSON with: score(0-100), "
                "matched_keywords[], missing_keywords[], strengths[], gaps[], "
                "recommendations[], verdict(Excellent/Good/Fair/Poor).",
            )

        @tool
        def optimize_resume_section(section_and_job: str) -> str:
            """Optimize a resume section to better match a job description."""
            return groq_chat(
                section_and_job,
                "You are an expert resume writer. Enhance the section with strong "
                "action verbs, quantified achievements, and keywords from the job.",
            )

        @tool
        def generate_cover_letter(resume_and_job: str) -> str:
            """Generate a tailored cover letter based on resume and job."""
            return groq_chat(
                f"Write a compelling, personalized cover letter:\n\n{resume_and_job[:3000]}",
                "You are an expert career coach. Write a concise, impactful 3-paragraph cover letter.",
            )

        @tool
        def analyze_resume_gaps(resume_text: str) -> str:
            """Identify skill gaps and growth opportunities in a resume."""
            return groq_chat(
                f"Analyze this resume for: 1) Skill gaps, 2) Missing sections, "
                f"3) Weak areas, 4) Growth opportunities.\n\nRESUME:\n{resume_text[:3000]}",
                "You are an expert career counselor. Provide specific, actionable insights.",
            )

        tools = [
            extract_job_requirements,
            score_resume_against_job,
            optimize_resume_section,
            generate_cover_letter,
            analyze_resume_gaps,
        ]

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are ResumeAI Pro, an expert career assistant with deep knowledge of "
                "ATS systems, hiring practices, and resume optimization. "
                "Use your tools to help users land their dream jobs. "
                "Always be specific, actionable, and encouraging.",
            ),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=6,
            handle_parsing_errors=True,
        )
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# ATS Scoring
# ─────────────────────────────────────────────────────────────────────────────

def compute_ats(resume_text: str, job_text: str) -> dict:
    """
    Full ATS analysis using Groq LLM.
    Returns a structured dict with score, verdict, keywords, strengths, gaps, etc.
    """
    prompt = f"""Analyze this resume against the job description. Return ONLY valid JSON (no markdown fences).

RESUME:
{resume_text[:ATS_RESUME_CHARS]}

JOB DESCRIPTION:
{job_text[:ATS_JOB_CHARS]}

Return this exact JSON structure:
{{
  "score": <integer 0-100>,
  "verdict": "<Excellent|Good|Fair|Poor>",
  "matched_keywords": ["keyword1", "keyword2"],
  "missing_keywords": ["keyword1", "keyword2"],
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "recommendations": ["rec1", "rec2", "rec3"],
  "section_scores": {{
    "summary": <0-100>,
    "experience": <0-100>,
    "skills": <0-100>,
    "education": <0-100>,
    "format": <0-100>
  }},
  "optimized_summary": "<rewritten summary section>"
}}"""

    raw = groq_chat(
        prompt,
        "You are an expert ATS analyzer. Return ONLY valid JSON, no markdown fences, no extra text.",
    )
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {
            "score": 0,
            "verdict": "Error",
            "matched_keywords": [],
            "missing_keywords": [],
            "strengths": ["Could not parse LLM response — check GROQ_API_KEY"],
            "gaps": [],
            "recommendations": ["Please verify your API key and try again"],
            "section_scores": {"summary": 0, "experience": 0, "skills": 0, "education": 0, "format": 0},
            "optimized_summary": "",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Resume Optimization
# ─────────────────────────────────────────────────────────────────────────────

def optimize_resume(resume_text: str, job_text: str, instructions: str = "") -> str:
    """Optimize resume text for the given job using Groq LLM."""
    extra = f"\nAdditional instructions: {instructions}" if instructions else ""
    return groq_chat(
        f"Optimize this resume for the job.{extra}\n\n"
        f"RESUME:\n{resume_text[:3500]}\n\n"
        f"JOB DESCRIPTION:\n{job_text[:2000]}",
        "You are an expert resume writer. Rewrite the resume with: strong action verbs, "
        "quantified achievements, relevant keywords from the job, clean markdown formatting. "
        "Keep all facts accurate — never fabricate experience.",
        max_tokens=4096,
    )


def generate_new_resume(resume_text: str, job_text: str, template_text: str) -> str:
    """Generate a brand-new resume from candidate info + job + template."""
    return groq_chat(
        f"Create a professional resume based on:\n\n"
        f"CANDIDATE INFO:\n{resume_text[:2000]}\n\n"
        f"TARGET JOB:\n{job_text[:1500]}\n\n"
        f"TEMPLATE STRUCTURE:\n{template_text[:1000]}",
        "You are a world-class resume writer. Create a polished, ATS-optimized resume "
        "using markdown formatting with clear sections: Summary, Experience, Skills, "
        "Education, Projects, Certifications.",
        max_tokens=4096,
    )


def generate_cover_letter(resume_text: str, job_text: str, candidate_name: str = "") -> str:
    """Generate a tailored cover letter."""
    name_line = f"Candidate Name: {candidate_name}\n\n" if candidate_name else ""
    return groq_chat(
        f"{name_line}Write a compelling cover letter:\n\n"
        f"RESUME:\n{resume_text[:2000]}\n\n"
        f"JOB:\n{job_text[:1500]}",
        "You are an expert career coach. Write a concise, impactful 3-paragraph cover letter "
        "that highlights the best fit between candidate and job. Be specific and confident.",
        max_tokens=1500,
    )


def improve_linkedin(resume_text: str, job_text: str = "") -> str:
    """Generate an optimized LinkedIn summary/headline."""
    context = f"\nTarget Job:\n{job_text[:500]}" if job_text else ""
    return groq_chat(
        f"Based on this resume, write:\n"
        f"1. A powerful LinkedIn headline (max 220 chars)\n"
        f"2. A compelling LinkedIn 'About' section (300-400 words)\n"
        f"3. 5 skill keywords to add to LinkedIn{context}\n\n"
        f"RESUME:\n{resume_text[:2000]}",
        "You are a LinkedIn optimization expert. Be compelling, keyword-rich, and authentic.",
    )


def analyze_vision(image_bytes: bytes) -> str:
    """Analyze resume image using Groq Vision model."""
    return groq_vision(
        image_bytes,
        "Analyze this resume image in detail:\n"
        "1. Rate visual clarity (1-10)\n"
        "2. Identify all sections present\n"
        "3. Rate ATS-friendliness (1-10) and explain\n"
        "4. List 3 layout strengths\n"
        "5. List 3 specific improvements\n"
        "6. Assess font, spacing, and structure\n"
        "Be specific and actionable.",
    )


def compare_resumes_vision(image_bytes_1: bytes, image_bytes_2: bytes) -> tuple[str, str]:
    """Compare two resume images with vision model."""
    prompt = (
        "Evaluate this resume comprehensively:\n"
        "Rate design, clarity, and ATS-friendliness (1-10 each).\n"
        "List 3 strengths and 3 weaknesses.\n"
        "Give a hiring manager's impression."
    )
    r1 = groq_vision(image_bytes_1, prompt)
    r2 = groq_vision(image_bytes_2, prompt)
    return r1, r2


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers (Telegram / Email messages)
# ─────────────────────────────────────────────────────────────────────────────

def format_ats_telegram(name: str, score: int, verdict: str, recommendations: list) -> str:
    recs = "\n".join(f"• {r}" for r in recommendations[:3])
    emoji = "🟢" if score >= 80 else "🟡" if score >= 55 else "🔴"
    return (
        f"🚀 *ResumeAI Pro — ATS Report*\n\n"
        f"📄 Resume: *{name}*\n"
        f"{emoji} ATS Score: *{score}/100* ({verdict})\n\n"
        f"📋 *Top Recommendations:*\n{recs}\n\n"
        f"💡 Open ResumeAI Pro for full analysis & optimized resume!"
    )


def resume_email_html(candidate_name: str, job_title: str, resume_preview: str) -> str:
    return f"""
<html><body style="font-family:Arial,sans-serif;background:#f8f9fa;padding:20px;">
<div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1)">
  <div style="background:linear-gradient(135deg,#6366f1,#22d3ee);padding:30px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:28px">🚀 ResumeAI Pro</h1>
    <p style="color:rgba(255,255,255,0.8);margin:8px 0 0">Your AI-Optimized Resume</p>
  </div>
  <div style="padding:30px">
    <h2 style="color:#1e293b">Hi {candidate_name}!</h2>
    <p style="color:#64748b">Your resume has been optimized for <strong>{job_title}</strong>.</p>
    <div style="background:#f1f5f9;border-radius:8px;padding:16px;margin:20px 0;font-family:monospace;font-size:13px;white-space:pre-wrap;max-height:200px;overflow:hidden">{resume_preview[:500]}...</div>
    <p style="color:#64748b">Please find your complete optimized resume attached to this email.</p>
  </div>
  <div style="background:#f8fafc;padding:16px;text-align:center;color:#94a3b8;font-size:12px">
    Generated by ResumeAI Pro · AI-powered career assistance
  </div>
</div>
</body></html>"""
