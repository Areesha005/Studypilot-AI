import re
import random
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(
page_title="StudyPilot AI",
page_icon="🎓",
layout="wide",
initial_sidebar_state="expanded",
)

#---------- DESIGN ----------

st.markdown("""

<style>  
.stApp {  
    background: linear-gradient(135deg, #f6f8ff, #eef2ff);  
}  
.block-container {  
    padding-top: 1.5rem;  
    max-width: 1200px;  
}  
.hero {  
    background: linear-gradient(120deg, #4338ca, #2563eb);  
    padding: 28px;  
    border-radius: 20px;  
    color: white;  
    margin-bottom: 22px;  
}  
.hero h1 { color: white; }  
.hero p { color: #e0e7ff; }  
div[data-testid="stMetric"] {  
    background: white;  
    padding: 16px;  
    border-radius: 14px;  
    border: 1px solid #e0e7ff;  
}  
div.stButton > button {  
    border-radius: 10px;  
    font-weight: 600;  
}  
</style>  """, unsafe_allow_html=True)

#---------- SESSION STATE ----------

defaults = {
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
}

for key, value in defaults.items():
if key not in st.session_state:
st.session_state[key] = value

def clean_text(text):
return re.sub(r"\s+", " ", text).strip()

def extract_sentences(text):
parts = re.split(r"(?<=[.!?])\s+", clean_text(text))
return [
sentence.strip()
for sentence in parts
if len(sentence.strip().split()) >= 6
]

def make_flashcards(text, count=10):
sentences = extract_sentences(text)
cards = []

for sentence in sentences:  
    parts = re.split(  
        r"\s+(?:is|are|means|refers to)\s+",  
        sentence,  
        maxsplit=1,  
        flags=re.IGNORECASE,  
    )  

    if len(parts) == 2 and len(parts[0].split()) <= 8:  
        question = f"What is {parts[0].strip()}?"  
    else:  
        question = "Explain this point from your notes."  

    cards.append({  
        "front": question,  
        "back": sentence,  
    })  

unique = []  
seen = set()  

for card in cards:  
    if card["back"] not in seen:  
        unique.append(card)  
        seen.add(card["back"])  

return unique[:count]

def make_pdf_quiz(text, count=5):
sentences = extract_sentences(text)
questions = []

for sentence in sentences:  
    words = sentence.split()  

    candidates = [  
        (i, word.strip(".,;:!?()[]{}"))  
        for i, word in enumerate(words)  
        if len(word.strip(".,;:!?()[]{}")) >= 5  
        and word.strip(".,;:!?()[]{}").isalpha()  
    ]  

    if not candidates:  
        continue  

    index, answer = max(  
        candidates,  
        key=lambda item: len(item[1])  
    )  

    blanked = words.copy()  
    blanked[index] = "_____"  

    questions.append({  
        "question": "Complete the statement: " + " ".join(blanked),  
        "answer": answer,  
        "source": sentence,  
    })  

unique = []  
seen = set()  

for question in questions:  
    if question["question"] not in seen:  
        unique.append(question)  
        seen.add(question["question"])  

random.shuffle(unique)  
return unique[:count]

#------- SIDEBAR ----------

with st.sidebar:
st.markdown("## 🎓 StudyPilot AI")
st.caption("Your personal study companion")

student = st.text_input("Student name", value="Student")  
days = st.slider("Planning period (days)", 1, 14, 6)  
daily_minutes = st.slider(  
    "Daily study time (minutes)", 20, 240, 60  
)  

st.divider()  
st.caption("Study smart. Revise consistently.")

#-------- HEADER ----------

safe_name = student.strip() or "Student"

st.markdown(f"""

<div class="hero">  
    <h1>Welcome, {safe_name} 👋</h1>  
    <p>Plan your studies, practise from your notes, and track topics to revise.</p>  
</div>  
""", unsafe_allow_html=True)  tabs = st.tabs([
"🏠 Overview",
"📅 Study Planner",
"📄 PDF Studio",
"🧠 Knowledge Gaps",
"🃏 Flashcards",
])

#------- OVERVIEW ----------

with tabs[0]:
total_completed = len(st.session_state.completed)
total_topics = len({
item["Topic"] for item in st.session_state.plan
})

progress = (  
    total_completed / total_topics  
    if total_topics else 0  
)  

a, b, c = st.columns(3)  
a.metric("Completed topics", total_completed)  
b.metric("Planned topics", total_topics)  
c.metric("Progress", f"{progress:.0%}")  

st.progress(progress)  

left, right = st.columns(2)  

with left:  
    st.subheader("📅 Study Planner")  
    st.write("Create a schedule and track completed topics.")  

with right:  
    st.subheader("📄 PDF Studio")  
    st.write("Extract notes and generate revision material.")  

    if st.session_state.pdf_name:  
        st.success(f"Loaded: {st.session_state.pdf_name}")  
    else:  
        st.info("Upload a PDF in the PDF Studio tab.")  

if st.session_state.weak_topics:  
    st.subheader("Topics to revisit")  
    for topic in st.session_state.weak_topics[:5]:  
        st.warning(topic)

#------ STUDY PLANNER ----------

with tabs[1]:
st.subheader("📅 Build your study plan")

default_topics = """Python basics

Variables and data types
Conditions and loops
Functions
Lists and dictionaries
File handling"""

topic_input = st.text_area(  
    "Enter one topic per line",  
    value=default_topics,  
    height=160,  
)  

topics = list(dict.fromkeys(  
    line.strip()  
    for line in topic_input.splitlines()  
    if line.strip()  
))  

if st.button("Generate / update study plan", type="primary"):  
    if not topics:  
        st.warning("Enter at least one topic.")  
    else:  
        plan = []  
        start = date.today()  

        for i, topic in enumerate(topics):  
            day_num = i % days  

            topics_on_day = sum(  
                1 for j in range(len(topics))  
                if j % days == day_num  
            )  

            plan.append({  
                "Date": str(start + timedelta(days=day_num)),  
                "Day": day_num + 1,  
                "Topic": topic,  
                "Suggested minutes": max(  
                    10, daily_minutes // max(1, topics_on_day)  
                ),  
            })  

        st.session_state.plan = plan  
        st.session_state.completed = [  
            topic for topic in st.session_state.completed  
            if topic in topics  
        ]  

        st.success("Your study plan is ready!")  

if st.session_state.plan:  
    df = pd.DataFrame(st.session_state.plan)  

    st.dataframe(  
        df,  
        use_container_width=True,  
        hide_index=True,  
    )  

    st.download_button(  
        "⬇️ Download study plan (CSV)",  
        df.to_csv(index=False).encode("utf-8"),  
        file_name="studypilot_study_plan.csv",  
        mime="text/csv",  
    )  

    all_topics = list(dict.fromkeys(  
        item["Topic"] for item in st.session_state.plan  
    ))  

    st.subheader("Track completed topics")  

    completed_now = st.multiselect(  
        "Select topics you have completed",  
        all_topics,  
        default=[  
            topic for topic in st.session_state.completed  
            if topic in all_topics  
        ],  
    )  

    st.session_state.completed = completed_now  

    completion = len(completed_now) / max(1, len(all_topics))  
    st.progress(completion)  
    st.write(  
        f"Completed: {len(completed_now)} of {len(all_topics)} topics"  
    )

#--------- PDF STUDIO ----------

with tabs[2]:
st.subheader("📄 PDF Studio")
st.write("Upload a text-based PDF to create revision material.")

uploaded_pdf = st.file_uploader(  
    "Choose a PDF",  
    type=["pdf"],  
)  

if uploaded_pdf is not None:  
    if uploaded_pdf.size > 15 * 1024 * 1024:  
        st.error("Please upload a PDF smaller than 15 MB.")  
    else:  
        try:  
            reader = PdfReader(uploaded_pdf)  

            extracted = "\n".join(  
                page.extract_text() or ""  
                for page in reader.pages  
            )  

            extracted = clean_text(extracted)  

            if not extracted:  
                st.warning(  
                    "No selectable text was found. "  
                    "This PDF may be scanned and need OCR."  
                )  
            else:  
                st.session_state.pdf_text = extracted  
                st.session_state.pdf_name = uploaded_pdf.name  

                st.success(  
                    f"Extracted text from {len(reader.pages)} page(s)."  
                )  

        except Exception as error:  
            st.error(f"Could not read the PDF: {error}")  

if st.session_state.pdf_text:  
    with st.expander("Preview extracted text"):  
        st.write(st.session_state.pdf_text[:6000])  

    st.markdown("### Generate a revision quiz")  

    quiz_count = st.slider(  
        "Number of questions",  
        3, 10, 5,  
        key="quiz_count",  
    )  

    if st.button("✨ Generate quiz from PDF", type="primary"):  
        questions = make_pdf_quiz(  
            st.session_state.pdf_text,  
            quiz_count,  
        )  

        st.session_state.quiz = questions  
        st.session_state.quiz_answers = {}  
        st.session_state.quiz_submitted = False  

        if questions:  
            st.success(f"Generated {len(questions)} questions.")  
        else:  
            st.warning(  
                "Not enough complete sentences were found in this PDF."  
            )  

    if st.session_state.quiz:  
        st.markdown("### Your quiz")  

        for i, question in enumerate(st.session_state.quiz):  
            st.markdown(  
                f"**Q{i + 1}.** {question['question']}"  
            )  

            answer = st.text_input(  
                "Your answer",  
                key=f"pdf_answer_{i}",  
            )  

            st.session_state.quiz_answers[i] = answer  

        if st.button("Check my answers"):  
            st.session_state.quiz_submitted = True  

        if st.session_state.quiz_submitted:  
            score = 0  
            missed = []  

            for i, question in enumerate(st.session_state.quiz):  
                answer = st.session_state.quiz_answers.get(i, "")  
                correct_answer = question["answer"]  

                correct = (  
                    answer.strip().casefold()  
                    == correct_answer.casefold()  
                )  

                if correct:  
                    score += 1  
                    st.success(f"Q{i + 1}: Correct!")  
                else:  
                    st.info(  
                        f"Q{i + 1}: Expected answer: {correct_answer}"  
                    )  
                    missed.append(question["source"])  

            st.metric(  
                "Quiz score",  
                f"{score}/{len(st.session_state.quiz)}",  
            )  

            st.session_state.weak_topics = list(dict.fromkeys(missed))  

    st.divider()  
    st.markdown("### Create flashcards")  

    if st.button("🃏 Generate PDF flashcards"):  
        cards = make_flashcards(  
            st.session_state.pdf_text,  
            count=20,  
        )  

        st.session_state.flashcards = cards  
        st.session_state.card_index = 0  
        st.session_state.card_revealed = False  

        if cards:  
            st.success(f"Created {len(cards)} flashcards.")  
        else:  
            st.warning("No suitable sentences found.")

#-------- KNOWLEDGE GAPS ----------

with tabs[3]:
st.subheader("🧠 Knowledge Gap Detector")
st.write(
"Find concepts to revise based on your quiz results "
"and your own confidence assessment."
)

if st.session_state.weak_topics:  
    st.markdown("### Topics to revisit")  

    for i, topic in enumerate(  
        st.session_state.weak_topics, start=1  
    ):  
        st.warning(f"{i}. {topic}")  

else:  
    st.info(  
        "Complete a PDF quiz and check your answers. "  
        "Missed questions will appear here."  
    )  

st.markdown("### Quick self-assessment")  

topic_check = st.text_input(  
    "Which topic do you want to assess?",  
    placeholder="e.g. Python loops",  
)  

confidence = st.radio(  
    "How confident are you?",  
    [  
        "Need help",  
        "Somewhat confident",  
        "Confident",  
    ],  
    horizontal=True,  
)  

if st.button("Save self-assessment"):  
    if topic_check.strip():  
        if confidence == "Need help":  
            entry = (  
                f"{topic_check.strip()} — self-reported weak topic"  
            )  

            if entry not in st.session_state.weak_topics:  
                st.session_state.weak_topics.append(entry)  

            st.warning("Added to your revision list.")  

        elif confidence == "Somewhat confident":  
            st.info(  
                "Schedule a short practice session for this topic."  
            )  

        else:  
            st.success(  
                "Great! Try a quiz to check your understanding."  
            )  
    else:  
        st.warning("Please enter a topic first.")  

if st.session_state.quiz_history:  
    st.markdown("### Quiz history")  

    st.dataframe(  
        pd.DataFrame(st.session_state.quiz_history),  
        use_container_width=True,  
        hide_index=True,  
    )  

if st.session_state.weak_topics:  
    st.download_button(  
        "⬇️ Download revision list",  
        pd.DataFrame({  
            "Topics to revise": st.session_state.weak_topics  
        }).to_csv(index=False).encode("utf-8"),  
        file_name="studypilot_revision_list.csv",  
        mime="text/csv",  
    )

#-------- FLASHCARDS ----------

with tabs[4]:
st.subheader("🃏 Flashcard Revision")
st.write(
"Review important statements extracted from your uploaded PDF."
)

if st.session_state.flashcards:  
    cards = st.session_state.flashcards  

    # Keep the index within the valid range.  
    idx = st.session_state.card_index % len(cards)  
    card = cards[idx]  

    st.caption(f"Card {idx + 1} of {len(cards)}")  

    if st.session_state.card_revealed:  
        heading = "Answer"  
        content = card["back"]  
    else:  
        heading = "Question"  
        content = card["front"]  

    st.markdown(  
        f"""  
        <div style="  
            background:white;  
            border:1px solid #dbeafe;  
            border-radius:18px;  
            padding:28px;  
            min-height:150px;  
            box-shadow:0 4px 16px rgba(67,56,202,0.07);  
        ">  
            <h3 style="color:#4338ca;">{heading}</h3>  
            <p style="font-size:20px;">{content}</p>  
        </div>  
        """,  
        unsafe_allow_html=True,  
    )  

    col1, col2, col3 = st.columns(3)  

    with col1:  
        if st.button("👀 Reveal / hide"):  
            st.session_state.card_revealed = (  
                not st.session_state.card_revealed  
            )  
            st.rerun()  

    with col2:  
        if st.button("⬅️ Previous"):  
            st.session_state.card_index = (  
                st.session_state.card_index - 1  
            ) % len(cards)  

            st.session_state.card_revealed = False  
            st.rerun()  

    with col3:  
        if st.button("Next ➡️"):  
            st.session_state.card_index = (  
                st.session_state.card_index + 1  
            ) % len(cards)  

            st.session_state.card_revealed = False  
            st.rerun()  

    flashcard_df = pd.DataFrame(cards)  

    st.download_button(  
        "⬇️ Download flashcards (CSV)",  
        flashcard_df.to_csv(index=False).encode("utf-8"),  
        file_name="studypilot_flashcards.csv",  
        mime="text/csv",  
    )  

else:  
    st.info(  
        "Go to PDF Studio, upload a PDF, and click "  
        "'Generate PDF flashcards'. Your cards will appear here."  
    )

#-------- FOOTER ----------

st.divider()

st.markdown(
"""
<div style="text-align:center; padding:12px; color:#64748b;">
<strong>StudyPilot AI</strong> · Learn smarter, not harder 🎓
</div>
""",
unsafe_allow_html=True,
)        
