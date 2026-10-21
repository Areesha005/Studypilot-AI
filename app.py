import re
import random
import unicodedata
from io import BytesIO
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from pypdf import PdfReader


# ---------------------------------------------------------
# StudyPilot AI — Streamlit app
# ---------------------------------------------------------
st.set_page_config(
    page_title="StudyPilot AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """ <style> .stApp { background: linear-gradient(135deg, #f7f8ff 0%, #f4fbff 100%); } [data-testid="stSidebar"] { background: linear-gradient(180deg, #101936 0%, #202b54 100%); } [data-testid="stSidebar"] * { color: #ffffff !important; } .hero { padding: 1.5rem 1.7rem; border-radius: 22px; background: linear-gradient(120deg, #172554, #4338ca, #0891b2); color: white; margin-bottom: 1rem; } .hero h1 { color: white; margin-bottom: .3rem; } .hero p { color: #e0f2fe; margin-bottom: 0; } .metric-card { background: white; border: 1px solid #e4e9f7; border-radius: 16px; padding: 1rem; box-shadow: 0 5px 18px rgba(30, 41, 90, .06); } .small-muted { color: #64748b; font-size: .9rem; } div[data-testid="stMetric"] { background: white; border: 1px solid #e4e9f7; padding: 12px 16px; border-radius: 14px; } </style> """,
    unsafe_allow_html=True,
)


# -------------------- Session state ----------------------
DEFAULTS = {
    "completed": [],
    "plan": [],
    "quiz": [],
    "quiz_answers": {},
    "quiz_submitted": False,
    "flashcards": [],
    "card_index": 0,
    "card_revealed": False,
    "pdf_text": "",
    "pdf_name": "",
    "weak_topics": [],
    "quiz_history": [],
    "planner_topics": "",
    "planner_days": 7,
    "planner_hours": 2,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -------------------- Text helpers -----------------------
def clean_text(text):
    """Clean extracted text while preserving paragraph boundaries."""
    text = unicodedata.normalize("NFKC", text or "")
    text = "".join(
        ch for ch in text
        if ch in "\n\t" or unicodedata.category(ch)[0] != "C"
    )
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", text)
    return text.strip()


def pdf_text_quality(text):
    visible = [ch for ch in text if not ch.isspace()]
    if not visible:
        return 0.0
    readable = sum(
        ch.isalnum() or unicodedata.category(ch)[0] in ("P", "S")
        for ch in visible
    )
    return readable / len(visible)


def extract_pdf_text(uploaded_file):
    """Try pypdf and PyMuPDF, then select the more readable extraction."""
    pdf_bytes = uploaded_file.getvalue()
    candidates = []

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        if reader.is_encrypted:
            raise ValueError("This PDF is password-protected.")
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        candidates.append(("pypdf", clean_text(text)))
    except ValueError:
        raise
    except Exception:
        pass

    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            text = "\n\n".join(
                page.get_text("text", sort=True) for page in document
            )
        candidates.append(("PyMuPDF", clean_text(text)))
    except Exception:
        pass

    if not candidates:
        raise ValueError("Could not read this PDF with either extractor.")

    candidates.sort(
        key=lambda item: (pdf_text_quality(item[1]), len(item[1])),
        reverse=True,
    )
    method, best_text = candidates[0]

    if len(best_text) < 50:
        raise ValueError(
            "Too little text was extracted. This PDF may be scanned or image-only."
        )
    if pdf_text_quality(best_text) < 0.80:
        raise ValueError(
            "The extracted text looks corrupted. Try exporting the original "
            "document as a new PDF."
        )
    return best_text, method


def extract_sentences(text):
    text = clean_text(text)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip().split()) >= 5
    ]


def make_flashcards(text, count=10):
    sentences = list(dict.fromkeys(extract_sentences(text)))
    cards = []
    for sentence in sentences[:count]:
        words = sentence.split()
        prompt = " ".join(words[: min(7, len(words))])
        cards.append({"front": f"Explain or complete this idea: {prompt}…", "back": sentence})
    return cards


def make_pdf_quiz(text, count=5):
    """Create simple revision prompts from extracted PDF sentences."""
    sentences = list(dict.fromkeys(extract_sentences(text)))
    return [
        {
            "question": "Explain this statement in your own words:",
            "study_note": sentence,
            "topic": "PDF revision",
        }
        for sentence in sentences[:count]
    ]


# -------------------- Planner helpers --------------------
def build_study_plan(topics, days, hours_per_day):
    clean_topics = [t.strip() for t in topics if t.strip()]
    if not clean_topics:
        return []
    total_slots = max(1, days * max(1, hours_per_day))
    plan = []
    start = date.today()
    for index, topic in enumerate(clean_topics):
        day_index = min(index % days, days - 1)
        plan.append({
            "Day": (start + timedelta(days=day_index)).strftime("%a, %d %b"),
            "Topic": topic,
            "Duration": f"{max(15, int(60 * hours_per_day / max(1, min(len(clean_topics), total_slots))))} min",
            "Status": "Completed" if topic in st.session_state.completed else "Pending",
        })
    return plan


# -------------------- Sidebar / header -------------------
with st.sidebar:
    st.markdown("# 📚 StudyPilot AI")
    st.caption("Your personal study workspace")
    st.markdown("---")
    st.markdown("### Your study loop")
    st.markdown("1. **Plan** your topics")
    st.markdown("2. **Practise** from your PDF")
    st.markdown("3. **Review** weaker topics")
    st.markdown("4. **Recall** with flashcards")
    st.markdown("---")
    st.caption("Prototype • Python + Streamlit")

st.markdown(
    """ <div class="hero"> <h1>Study smarter. Not longer. ✨</h1> <p>Plan your learning, turn PDFs into revision prompts, and track what to revisit.</p> </div> """,
    unsafe_allow_html=True,
)


# -------------------- Tabs -------------------------------
overview_tab, planner_tab, pdf_tab, gaps_tab, cards_tab = st.tabs(
    ["🏠 Overview", "🗓️ Study Planner", "📄 PDF Studio", "🎯 Knowledge Gaps", "🃏 Flashcards"]
)


# ==================== OVERVIEW ============================
with overview_tab:
    st.subheader("Your learning dashboard")
    total_topics = len(st.session_state.plan)
    completed_count = len(st.session_state.completed)
    completion_rate = int(completed_count / total_topics * 100) if total_topics else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planned topics", total_topics)
    c2.metric("Completed topics", completed_count)
    c3.metric("Progress", f"{completion_rate}%")
    c4.metric("PDF loaded", "Yes" if st.session_state.pdf_text else "No")

    st.markdown("### Quick actions")
    q1, q2, q3 = st.columns(3)
    with q1:
        st.markdown("**🗓️ Build a plan**")
        st.write("Break your syllabus into manageable study tasks.")
        if st.button("Open Study Planner", key="go_planner"):
            st.info("Choose the Study Planner tab above.")
    with q2:
        st.markdown("**📄 Study from a PDF**")
        st.write("Extract text and create revision prompts.")
        if st.button("Open PDF Studio", key="go_pdf"):
            st.info("Choose the PDF Studio tab above.")
    with q3:
        st.markdown("**🃏 Active recall**")
        st.write("Use short flashcards to revisit key ideas.")
        if st.button("Open Flashcards", key="go_cards"):
            st.info("Choose the Flashcards tab above.")

    if st.session_state.plan:
        st.markdown("### Your current plan")
        st.dataframe(pd.DataFrame(st.session_state.plan), use_container_width=True, hide_index=True)
    else:
        st.info("Start in Study Planner to create your first study plan.")


# ==================== STUDY PLANNER =======================
with planner_tab:
    st.subheader("🗓️ Build your study plan")
    st.write("Enter one topic per line, then choose how much time you have.")

    topics_input = st.text_area(
        "Your topics",
        value=st.session_state.planner_topics,
        placeholder="Python basics\nLoops and conditions\nFunctions\nLists and dictionaries",
        height=150,
        key="topics_text_area",
    )
    col1, col2 = st.columns(2)
    with col1:
        days = st.number_input("Study days", min_value=1, max_value=60, value=int(st.session_state.planner_days))
    with col2:
        hours = st.number_input("Hours available per day", min_value=1, max_value=12, value=int(st.session_state.planner_hours))

    if st.button("✨ Generate study plan", type="primary", key="generate_plan"):
        topics = [line for line in topics_input.splitlines() if line.strip()]
        if not topics:
            st.warning("Please enter at least one topic.")
        else:
            st.session_state.planner_topics = topics_input
            st.session_state.planner_days = int(days)
            st.session_state.planner_hours = int(hours)
            st.session_state.plan = build_study_plan(topics, int(days), int(hours))
            st.success("Your study plan is ready!")

    if st.session_state.plan:
        st.markdown("### Plan and progress")
        for i, task in enumerate(st.session_state.plan):
            topic = task["Topic"]
            checked = topic in st.session_state.completed
            new_checked = st.checkbox(
                f"{task['Day']} · {topic} · {task['Duration']}",
                value=checked,
                key=f"topic_done_{i}_{topic}",
            )
            if new_checked and topic not in st.session_state.completed:
                st.session_state.completed.append(topic)
            elif not new_checked and topic in st.session_state.completed:
                st.session_state.completed.remove(topic)

        st.dataframe(pd.DataFrame(st.session_state.plan), use_container_width=True, hide_index=True)
        csv = pd.DataFrame(st.session_state.plan).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download plan as CSV", csv, "studypilot_study_plan.csv", "text/csv")


# ==================== PDF STUDIO ==========================
with pdf_tab:
    st.subheader("📄 PDF Studio")
    st.write("Upload selectable-text study notes to prepare revision prompts.")
    uploaded_pdf = st.file_uploader("Choose a PDF", type=["pdf"], key="pdf_uploader")

    if uploaded_pdf is not None:
        if uploaded_pdf.size > 15 * 1024 * 1024:
            st.error("Please upload a PDF smaller than 15 MB.")
        else:
            try:
                extracted, method = extract_pdf_text(uploaded_pdf)
                st.session_state.pdf_text = extracted
                st.session_state.pdf_name = uploaded_pdf.name
                st.success(f"Extracted text from {uploaded_pdf.name} using {method}.")
                if pdf_text_quality(extracted) < 0.90:
                    st.warning("Some characters may be unusual. Check the preview before creating revision material.")
            except Exception as error:
                st.error(f"Could not extract PDF text: {error}")

    if st.session_state.pdf_text:
        st.markdown(f"**Loaded file:** {st.session_state.pdf_name or 'PDF'}")
        with st.expander("Preview extracted text", expanded=True):
            st.text_area(
                "Extracted text (check this against the original PDF)",
                value=st.session_state.pdf_text[:12000],
                height=260,
                disabled=True,
                key="pdf_preview",
            )
            if len(st.session_state.pdf_text) > 12000:
                st.caption("Preview limited to the first 12,000 characters.")

        colq, colf = st.columns(2)
        with colq:
            if st.button("📝 Generate revision quiz", type="primary"):
                st.session_state.quiz = make_pdf_quiz(st.session_state.pdf_text, count=5)
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                if not st.session_state.quiz:
                    st.warning("Not enough readable sentences were found to make prompts.")
                else:
                    st.success(f"Created {len(st.session_state.quiz)} revision prompts.")
        with colf:
            if st.button("🃏 Generate flashcards"):
                st.session_state.flashcards = make_flashcards(st.session_state.pdf_text, count=10)
                st.session_state.card_index = 0
                st.session_state.card_revealed = False
                if not st.session_state.flashcards:
                    st.warning("Not enough readable sentences were found to make flashcards.")
                else:
                    st.success(f"Created {len(st.session_state.flashcards)} flashcards.")

        if st.session_state.quiz:
            st.markdown("### Revision quiz")
            st.caption("These are rule-based prompts from your PDF, not AI-generated factual questions.")
            for i, question in enumerate(st.session_state.quiz):
                st.markdown(f"**{i + 1}. {question['question']}**")
                st.info(question["study_note"])
                st.session_state.quiz_answers[i] = st.text_area(
                    "Your answer",
                    value=st.session_state.quiz_answers.get(i, ""),
                    key=f"pdf_quiz_answer_{i}",
                    height=80,
                )
            if st.button("Check my revision", key="submit_pdf_quiz"):
                st.session_state.quiz_submitted = True
                st.session_state.quiz_history.append({
                    "date": date.today().isoformat(),
                    "total": len(st.session_state.quiz),
                    "answered": sum(bool(a.strip()) for a in st.session_state.quiz_answers.values()),
                })
            if st.session_state.quiz_submitted:
                answered = sum(bool(a.strip()) for a in st.session_state.quiz_answers.values())
                st.write(f"You wrote answers for **{answered} of {len(st.session_state.quiz)}** prompts. Review each answer against your notes.")

    else:
        st.info("Upload a PDF to see its extracted text and create revision prompts.")


# ==================== KNOWLEDGE GAPS =====================
with gaps_tab:
    st.subheader("🎯 Knowledge Gap Detector")
    st.write("Mark topics by confidence. This simple self-assessment helps you decide what to review.")
    if st.session_state.plan:
        gap_topics = []
        for i, task in enumerate(st.session_state.plan):
            topic = task["Topic"]
            level = st.select_slider(
                f"How confident are you with **{topic}**?",
                options=["Need help", "Getting there", "Confident"],
                value="Getting there",
                key=f"confidence_{i}_{topic}",
            )
            if level == "Need help":
                gap_topics.append(topic)
        st.session_state.weak_topics = gap_topics

        if gap_topics:
            st.warning("Topics to review next")
            for topic in gap_topics:
                st.markdown(f"- 🔴 {topic}")
        else:
            st.success("No topics marked as needing help. Keep practising and reassess after a quiz.")
        if st.button("Add weak topics to completed list for review", key="review_gaps"):
            st.session_state.completed = [
                topic for topic in st.session_state.completed if topic not in gap_topics
            ]
            st.success("Those topics are now marked as pending in your plan.")
    else:
        st.info("Create a study plan first. Your topics will appear here for confidence check-ins.")


# ==================== FLASHCARDS ==========================
with cards_tab:
    st.subheader("🃏 Flashcards")
    if not st.session_state.flashcards:
        st.info("Generate flashcards in PDF Studio after uploading a PDF.")
    else:
        cards = st.session_state.flashcards
        st.caption(f"Card {st.session_state.card_index + 1} of {len(cards)}")
        current = cards[st.session_state.card_index]
        st.markdown(
            f""" <div style="background:white;border:1px solid #dbeafe;border-radius:20px; padding:28px;min-height:150px;box-shadow:0 6px 20px rgba(30,41,90,.07)"> <div style="color:#6366f1;font-weight:700;margin-bottom:12px"> {"ANSWER" if st.session_state.card_revealed else "QUESTION"} </div> <div style="font-size:1.15rem;color:#172554"> {current["back"] if st.session_state.card_revealed else current["front"]} </div> </div> """,
            unsafe_allow_html=True,
        )
        nav1, nav2, nav3 = st.columns(3)
        with nav1:
            if st.button("⬅️ Previous", disabled=st.session_state.card_index == 0):
                st.session_state.card_index -= 1
                st.session_state.card_revealed = False
                st.rerun()
        with nav2:
            if st.button("👀 Reveal / hide"):
                st.session_state.card_revealed = not st.session_state.card_revealed
                st.rerun()
        with nav3:
            if st.button("Next ➡️", disabled=st.session_state.card_index >= len(cards) - 1):
                st.session_state.card_index += 1
                st.session_state.card_revealed = False
                st.rerun()

        st.markdown("---")
        st.markdown("### All flashcards")
        for i, card in enumerate(cards):
            with st.expander(f"Card {i + 1}: {card['front']}"):
                st.write(card["back"])


st.markdown("---")
st.caption("StudyPilot AI • A student-built prototype. PDF prompts and confidence ratings are rule-based study aids.")
