import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="StudyPilot AI", page_icon="🎓", layout="wide")

st.title("🎓 StudyPilot AI")
st.caption("Your personal study-planning and revision assistant")

st.info("Prototype mode: the agents use Python rules. AI-generated explanations can be added next.")

# AGENT 1: Organize the syllabus
def syllabus_agent(raw_topics):
    topics = []
    for line in raw_topics.splitlines():
        topic = line.strip()
        if topic and topic not in topics:
            topics.append(topic)
    return topics


# AGENT 2: Build a study schedule
def planning_agent(topics, days, hours_per_day):
    if not topics:
        return []

    schedule = []
    start_date = date.today()

    for index, topic in enumerate(topics):
        day_index = index % days
        study_date = start_date + timedelta(days=day_index)

        schedule.append({
            "Day": day_index + 1,
            "Date": study_date.strftime("%d %b"),
            "Topic": topic,
            "Study time (min)": max(
                15, int(hours_per_day * 60 / min(len(topics), days))
            )
        })

    return schedule


# AGENT 3: Create active-recall questions
def quiz_agent(topic):
    return [
        f"Explain '{topic}' in your own words.",
        f"What are the key concepts or steps in '{topic}'?",
        f"Give a real-life example of '{topic}'.",
        f"What is one common mistake when learning '{topic}'?"
    ]


# AGENT 4: Track progress
def progress_agent(topics, completed):
    total = len(topics)
    done = len(set(topics) & set(completed))
    percentage = int(done / total * 100) if total else 0
    return done, total, percentage


with st.sidebar:
    st.header("Your study settings")
    student = st.text_input("Your name (optional)")
    days = st.slider("Days available", 1, 14, 7)
    hours = st.slider("Study hours per day", 1, 8, 2)

st.subheader("1. Enter your syllabus")
raw_topics = st.text_area(
    "Enter one topic per line",
    value="Python basics\nVariables and data types\nLoops\nFunctions\nLists and dictionaries\nFile handling",
    height=170,
    help="Use topics from your actual syllabus for your demo."
)

topics = syllabus_agent(raw_topics)

if "completed_topics" not in st.session_state:
    st.session_state.completed_topics = []

# Keep only completed topics still in the syllabus
st.session_state.completed_topics = [
    t for t in st.session_state.completed_topics if t in topics
]

st.subheader("2. Track your learning")
completed = st.multiselect(
    "Select topics you have finished",
    options=topics,
    default=st.session_state.completed_topics
)
st.session_state.completed_topics = completed

done, total, percentage = progress_agent(topics, completed)

c1, c2, c3 = st.columns(3)
c1.metric("Total topics", total)
c2.metric("Completed", done)
c3.metric("Progress", f"{percentage}%")
st.progress(percentage / 100)

st.subheader("3. Your study plan")

if st.button("Generate / update my study plan", type="primary"):
    if not topics:
        st.warning("Please enter at least one topic.")
    else:
        remaining = [t for t in topics if t not in completed]
        if not remaining:
            st.success("Congratulations! All listed topics are complete.")
        else:
            schedule = planning_agent(remaining, days, hours)
            st.session_state.schedule = schedule

if "schedule" in st.session_state:
    if st.session_state.schedule:
        st.dataframe(
            st.session_state.schedule,
            use_container_width=True,
            hide_index=True
        )
        csv = __import__("pandas").DataFrame(
            st.session_state.schedule
        ).to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download study plan (CSV)",
            data=csv,
            file_name="studypilot_plan.csv",
            mime="text/csv"
        )

st.subheader("4. Revision question generator")

if topics:
    selected_topic = st.selectbox("Choose a topic to revise", topics)
    if st.button("Generate revision questions"):
        questions = quiz_agent(selected_topic)
        for i, question in enumerate(questions, start=1):
            st.write(f"**Q{i}.** {question}")
else:
    st.caption("Enter topics above to generate revision questions.")

st.divider()
st.caption("StudyPilot AI | Student project prototype | Verify plans against your actual syllabus.")
