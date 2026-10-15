import os
import io
import json
from typing import List, Dict, Tuple

import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types

st.set_page_config(
    page_title="PrepAI | AI Study Workspace",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- Styling -------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --navy:#0b1020; --panel:#121a2d; --line:#25314a; --cyan:#53d8e8; --blue:#718cff; --muted:#9aa9c4; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: radial-gradient(circle at 85% 0%, #17284a 0%, #0b1020 38%, #080d19 100%); color:#f4f7ff; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.035em; }
.block-container { padding-top:1.6rem; padding-bottom:3rem; max-width: 1400px; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#111a2d,#0c1221); border-right:1px solid #25314a; }
[data-testid="stSidebar"] * { color:#eaf0ff; }
.hero { padding:1.7rem 1.8rem; border:1px solid #2a3c5d; border-radius:24px; background:linear-gradient(120deg,rgba(30,53,91,.9),rgba(17,26,45,.92)); margin-bottom:1.2rem; }
.eyebrow { color:#53d8e8; font-size:.78rem; text-transform:uppercase; letter-spacing:.15em; font-weight:700; }
.hero-title { font-family:'Space Grotesk',sans-serif; font-size:2.5rem; line-height:1.1; font-weight:700; margin:.35rem 0 .65rem; color:#fff; }
.hero-sub { color:#b7c5df; font-size:1.02rem; max-width:780px; }
.pill { display:inline-block; padding:.35rem .7rem; border:1px solid #375174; background:#172741; color:#c6f7fb; border-radius:999px; font-size:.78rem; margin:.2rem .25rem .1rem 0; }
.metric-card { background:rgba(18,26,45,.85); border:1px solid #263651; border-radius:17px; padding:1rem 1.1rem; min-height:110px; }
.metric-label { color:#9aa9c4; font-size:.82rem; }
.metric-value { color:#fff; font-size:1.6rem; font-family:'Space Grotesk',sans-serif; font-weight:700; margin-top:.25rem; }
.section-card { background:rgba(18,26,45,.72); border:1px solid #263651; border-radius:18px; padding:1.2rem; margin-bottom:.8rem; }
.small-muted { color:#9aa9c4; font-size:.9rem; }
div.stButton > button { border-radius:11px; border:1px solid #3a4f73; background:linear-gradient(110deg,#4565f5,#4c9de8); color:white; font-weight:700; min-height:2.8rem; }
div.stButton > button:hover { border-color:#74e6ef; color:white; }
.stTextInput input, .stTextArea textarea { background:#0e1728 !important; color:#f4f7ff !important; border-color:#30405e !important; border-radius:11px !important; }
[data-testid="stFileUploader"] { background:rgba(15,23,40,.6); border:1px dashed #3d5579; border-radius:14px; padding:.4rem; }
.stTabs [data-baseweb="tab-list"] { gap:.35rem; border-bottom:1px solid #273650; }
.stTabs [data-baseweb="tab"] { background:#111a2d; border-radius:10px 10px 0 0; padding:.65rem 1rem; }
.stAlert { border-radius:12px; }
hr { border-color:#263651; }
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ------------------------- Helpers -------------------------
def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)

def get_client():
    key = get_secret("GEMINI_API_KEY")
    if not key:
        return None
    return genai.Client(api_key=key)

def get_model_name() -> str:
    return get_secret("GEMINI_MODEL", "gemini-3.8-flash")

def extract_pdf(uploaded_file) -> Tuple[str, List[Dict]]:
    reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
    page_records = []
    all_text = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            page_records.append({"page": page_num, "text": text})
            all_text.append(f"[Page {page_num}]\n{text}")
    return "\n\n".join(all_text), page_records

def chunk_pages(pages: List[Dict], chunk_chars: int = 1400, overlap: int = 180) -> List[Dict]:
    chunks = []
    for item in pages:
        text = item["text"]
        start = 0
        while start < len(text):
            end = min(start + chunk_chars, len(text))
            chunks.append({"page": item["page"], "text": text[start:end]})
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks

def retrieve_chunks(question: str, chunks: List[Dict], limit: int = 5) -> List[Dict]:
    terms = {w.lower().strip(".,!?():;[]{}\"'") for w in question.split() if len(w) > 2}
    scored = []
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        score = sum(text_lower.count(term) for term in terms)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for _, item in scored[:limit]]
    return selected or chunks[:min(limit, len(chunks))]

def call_gemini(prompt: str, temperature: float = 0.3) -> str:
    client = get_client()
    if client is None:
        raise RuntimeError("Gemini API key missing. Add GEMINI_API_KEY in Streamlit Secrets.")
    response = client.models.generate_content(
        model=get_model_name(),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=1800,
        ),
    )
    return (response.text or "").strip()

def require_document() -> bool:
    if not st.session_state.get("pdf_pages"):
        st.warning("Pehle sidebar se ek text-based PDF upload karo.")
        return False
    return True

# ------------------------- Sidebar -------------------------
with st.sidebar:
    st.markdown("## 🎓 PrepAI")
    st.caption("Your AI-powered study workspace")
    st.markdown("---")
    st.markdown("### 📚 Study material")
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"], help="Text-based PDFs work best. Scanned PDFs may need OCR.")
    if uploaded is not None:
        signature = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("pdf_signature") != signature:
            with st.spinner("Reading your PDF..."):
                try:
                    full_text, pages = extract_pdf(uploaded)
                    if not full_text.strip():
                        st.session_state.pdf_pages = []
                        st.error("PDF se selectable text nahi mila. Scanned PDF ke liye OCR ki zaroorat ho sakti hai.")
                    else:
                        st.session_state.pdf_signature = signature
                        st.session_state.pdf_name = uploaded.name
                        st.session_state.pdf_text = full_text
                        st.session_state.pdf_pages = pages
                        st.session_state.pdf_chunks = chunk_pages(pages)
                        st.session_state.chat_history = []
                        st.success(f"Loaded {len(pages)} text pages")
                except Exception as exc:
                    st.error(f"PDF read nahi ho paya: {exc}")
    if st.session_state.get("pdf_name"):
        st.markdown(f"**Current file:** `{st.session_state.pdf_name}`")
        st.caption(f"{len(st.session_state.get('pdf_pages', []))} pages with extracted text")
        if st.button("Remove document", use_container_width=True):
            for key in ["pdf_signature", "pdf_name", "pdf_text", "pdf_pages", "pdf_chunks", "chat_history"]:
                st.session_state.pop(key, None)
            st.rerun()
    st.markdown("---")
    st.markdown("### 🧠 Tools")
    st.caption("Ask questions · Summarize · Make quizzes · Revise with flashcards")
    st.markdown("---")
    st.markdown("<span class='small-muted'>Prototype · Built for Education Technologies & Future Learning</span>", unsafe_allow_html=True)

# ------------------------- Main -------------------------
st.markdown("""
<div class="hero">
  <div class="eyebrow">AI-powered personalized learning</div>
  <div class="hero-title">Study smarter with <span style="color:#53d8e8">PrepAI.</span></div>
  <div class="hero-sub">Upload your study material, ask questions in plain language, and turn long documents into clear explanations, practice quizzes, and revision cards.</div>
  <div style="margin-top:1rem">
    <span class="pill">📄 PDF-based answers</span><span class="pill">✨ Gemini AI</span><span class="pill">🔎 Context retrieval</span><span class="pill">🔐 Session-based prototype</span>
  </div>
</div>
""", unsafe_allow_html=True)

pages_count = len(st.session_state.get("pdf_pages", []))
chunks_count = len(st.session_state.get("pdf_chunks", []))
c1, c2, c3, c4 = st.columns(4)
for col, label, value in [
    (c1, "Study document", st.session_state.get("pdf_name", "Not uploaded")),
    (c2, "Text pages", str(pages_count)),
    (c3, "Context chunks", str(chunks_count)),
    (c4, "AI status", "Ready" if get_secret("GEMINI_API_KEY") else "API key needed"),
]:
    with col:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value' style='font-size:{'1.0rem' if len(str(value)) > 14 else '1.6rem'}'>{value}</div></div>", unsafe_allow_html=True)

st.write("")
tab_chat, tab_summary, tab_quiz, tab_cards, tab_about = st.tabs([
    "💬 Ask PrepAI", "📝 Smart Summary", "🧩 Practice Quiz", "🗂️ Flashcards", "ℹ️ About"
])

with tab_chat:
    st.subheader("Ask questions from your document")
    st.caption("Answers are generated from retrieved PDF text. Always verify important facts against the source.")
    if not st.session_state.get("chat_history"):
        st.markdown("<div class='section-card'><b>Try asking:</b><br>• Explain this topic in simple words<br>• What are the key definitions?<br>• Give me an exam-oriented answer<br>• Which page discusses this concept?</div>", unsafe_allow_html=True)
    for msg in st.session_state.get("chat_history", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    question = st.chat_input("Ask a question about your uploaded PDF...")
    if question:
        if not require_document():
            st.stop()
        st.session_state.setdefault("chat_history", []).append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        retrieved = retrieve_chunks(question, st.session_state.pdf_chunks, limit=5)
        context = "\n\n".join([f"Source: page {x['page']}\n{x['text']}" for x in retrieved])
        prompt = f"""You are PrepAI, a careful study assistant. Answer the student's question using ONLY the source context below.
If the context does not contain the answer, say that the uploaded document does not provide enough information. Do not invent page numbers or facts.
Explain clearly for a student preparing for exams. Use headings or bullets when useful.
At the end add a short 'Sources' line with the page numbers from the supplied context.

QUESTION:
{question}

SOURCE CONTEXT:
{context}
"""
        with st.chat_message("assistant"):
            with st.spinner("PrepAI is reading the relevant sections..."):
                try:
                    answer = call_gemini(prompt)
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as exc:
                    st.error(f"AI request failed: {exc}")
                    st.info("Check your Streamlit Secrets and Gemini model availability.")

with tab_summary:
    st.subheader("Turn long notes into a revision summary")
    summary_style = st.selectbox("Summary style", ["Exam revision notes", "Beginner-friendly explanation", "Key points only", "Definitions and formulas"])
    if st.button("Generate summary", key="make_summary", use_container_width=False):
        if require_document():
            source_text = st.session_state.pdf_text[:24000]
            prompt = f"""Create {summary_style.lower()} from the study document below.
Use clear headings, concise bullets, key terms and examples when supported. Do not add unsupported facts.
If the text is too long or incomplete, mention that this is based on the extracted portion.

DOCUMENT:
{source_text}
"""
            with st.spinner("Creating your summary..."):
                try:
                    st.session_state.summary_result = call_gemini(prompt)
                except Exception as exc:
                    st.error(f"Could not generate summary: {exc}")
    if st.session_state.get("summary_result"):
        st.markdown(st.session_state.summary_result)
        st.download_button("Download summary (.txt)", st.session_state.summary_result, file_name="prepai_summary.txt", mime="text/plain")

with tab_quiz:
    st.subheader("Create an exam-style practice quiz")
    q_count = st.slider("Number of questions", 3, 10, 5)
    difficulty = st.selectbox("Difficulty", ["Mixed", "Easy", "Medium", "Hard"])
    if st.button("Generate quiz", key="make_quiz"):
        if require_document():
            prompt = f"""Create exactly {q_count} multiple-choice questions based ONLY on this document.
Difficulty: {difficulty}. Return valid JSON only in this schema:
{{"questions":[{{"question":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},"answer":"A","explanation":"...","page":1}}]}}
Each answer must be A, B, C, or D. Use a real page number only if it can be inferred from the document text; otherwise use null.
DOCUMENT:
{st.session_state.pdf_text[:22000]}
"""
            with st.spinner("Building your quiz..."):
                try:
                    raw = call_gemini(prompt, temperature=0.2)
                    cleaned = raw.strip()
                    if cleaned.startswith("```"):
                        cleaned = cleaned.split("\n", 1)[-1]
                        cleaned = cleaned.rsplit("```", 1)[0]
                    quiz = json.loads(cleaned)
                    st.session_state.quiz_result = quiz
                    st.session_state.quiz_answers = {}
                except Exception as exc:
                    st.error(f"Quiz generation failed or returned invalid JSON: {exc}")
                    st.caption("Try again. The AI may occasionally return a format that needs another attempt.")
    quiz = st.session_state.get("quiz_result")
    if quiz:
        with st.form("quiz_form"):
            for i, item in enumerate(quiz.get("questions", [])):
                st.markdown(f"**Q{i+1}. {item.get('question','')}**")
                options = item.get("options", {})
                st.radio("Choose one", options=list(options.keys()), format_func=lambda k, opts=options: f"{k}. {opts.get(k,'')}", key=f"quiz_q_{i}", index=None)
                st.markdown("---")
            submitted = st.form_submit_button("Check my answers")
        if submitted:
            correct = 0
            for i, item in enumerate(quiz.get("questions", [])):
                chosen = st.session_state.get(f"quiz_q_{i}")
                answer = str(item.get("answer", "")).upper()
                if chosen == answer:
                    correct += 1
                st.markdown(f"**Q{i+1}: {'✅ Correct' if chosen == answer else '❌ Incorrect'}** — Correct answer: {answer}. {item.get('explanation','')}")
            total = len(quiz.get("questions", []))
            st.success(f"Score: {correct}/{total} ({round(correct/total*100) if total else 0}%)")

with tab_cards:
    st.subheader("Generate quick revision flashcards")
    if st.button("Create flashcards", key="make_cards"):
        if require_document():
            prompt = f"""Create 8 useful study flashcards from the document. Return valid JSON only:
{{"cards":[{{"front":"Question or term","back":"Short answer","page":1}}]}}
Do not invent facts. Use page number only if supported, otherwise null.
DOCUMENT:
{st.session_state.pdf_text[:20000]}
"""
            with st.spinner("Creating flashcards..."):
                try:
                    raw = call_gemini(prompt, temperature=0.25).strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
                    st.session_state.flashcards_result = json.loads(raw).get("cards", [])
                    st.session_state.flashcard_index = 0
                    st.session_state.flashcard_revealed = False
                except Exception as exc:
                    st.error(f"Flashcard generation failed: {exc}")
    cards = st.session_state.get("flashcards_result", [])
    if cards:
        idx = st.session_state.get("flashcard_index", 0) % len(cards)
        card = cards[idx]
        st.markdown(f"<div class='section-card'><div class='eyebrow'>Flashcard {idx+1} of {len(cards)}</div><h3>{card.get('front','')}</h3></div>", unsafe_allow_html=True)
        if st.button("Reveal answer" if not st.session_state.get("flashcard_revealed") else "Hide answer"):
            st.session_state.flashcard_revealed = not st.session_state.get("flashcard_revealed", False)
        if st.session_state.get("flashcard_revealed"):
            st.info(card.get("back", ""))
            if card.get("page"):
                st.caption(f"Reference page: {card['page']}")
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Previous"):
                st.session_state.flashcard_index = (idx - 1) % len(cards)
                st.session_state.flashcard_revealed = False
                st.rerun()
        with col_next:
            if st.button("Next →"):
                st.session_state.flashcard_index = (idx + 1) % len(cards)
                st.session_state.flashcard_revealed = False
                st.rerun()
    else:
        st.markdown("<div class='section-card'>Generate flashcards from your uploaded notes, then flip through them to revise key concepts.</div>", unsafe_allow_html=True)

with tab_about:
    st.subheader("About PrepAI")
    st.markdown("""
    PrepAI is a hackathon prototype for **Education Technologies and Future Learning**.

    **What this prototype demonstrates**
    - PDF text extraction with PyPDF
    - Lightweight keyword-based context retrieval
    - Gemini-powered document Q&A, summaries, quizzes, and flashcards
    - A single-page study workspace built with Streamlit

    **Current limitations**
    - Text-based PDFs work best; scanned PDFs may require OCR.
    - Retrieval uses keyword matching, not vector embeddings or semantic search.
    - Uploaded documents and generated content are session-based and are not stored in a permanent database.
    - AI output can be incorrect; verify important answers against the source document.
    - This prototype is for educational assistance, not a replacement for teachers or official study material.
    """)
    st.markdown("**Architecture:** PDF → Text extraction → Chunking → Keyword retrieval → Gemini → Student interface")
