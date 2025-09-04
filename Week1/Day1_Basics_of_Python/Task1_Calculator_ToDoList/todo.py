import streamlit as st
import json
import os

DATA_FILE = "tasks.json"

# Load tasks from file
def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

# Save tasks to file
def save_tasks(tasks):
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

# Initialize task list
if 'tasks' not in st.session_state:
    st.session_state.tasks = load_tasks()

# Add a new task
def add_task():
    task = st.session_state["new_task"].strip()
    priority = st.session_state["priority"]
    if task:
        st.session_state.tasks.append({'task': task, 'done': False, 'priority': priority})
        save_tasks(st.session_state.tasks)
    st.session_state["new_task"] = ""

# Header
st.title("📝 My To-Do List")

# Counters
total = len(st.session_state.tasks)
completed = sum(1 for t in st.session_state.tasks if t['done'])
pending = total - completed
st.markdown(f"✅ **Completed:** {completed} | 🕒 **Pending:** {pending} | 📌 **Total:** {total}")

# Input form
cols = st.columns([0.6, 0.3, 0.1])
cols[0].text_input("Enter a task:", key="new_task", on_change=add_task)
cols[1].selectbox("Priority", ["High", "Medium", "Low"], key="priority")
cols[2].markdown("<br>", unsafe_allow_html=True)

# Filter options
filter_opt = st.radio("Filter tasks:", ["All", "Pending", "Completed"], horizontal=True)

# Display tasks
for i, task in enumerate(st.session_state.tasks):
    if filter_opt == "Completed" and not task['done']:
        continue
    if filter_opt == "Pending" and task['done']:
        continue

    bg_color = "#d4edda" if task['done'] else "#fff3cd" if task['priority'] == "High" else "#e2e3e5"
    with st.container():
        cols = st.columns([0.6, 0.15, 0.1, 0.1])
        style = f"background-color:{bg_color}; padding:10px; border-radius:10px;"
        if task['done']:
            cols[0].markdown(f"<div style='{style}'>~~{task['task']}~~</div>", unsafe_allow_html=True)
        else:
            cols[0].markdown(f"<div style='{style}'>{task['task']}</div>", unsafe_allow_html=True)
        cols[1].write(f"**{task['priority']}**")
        if cols[2].button("✔️", key=f"done_{i}"):
            st.session_state.tasks[i]['done'] = True
            save_tasks(st.session_state.tasks)
            st.rerun()
        if cols[3].button("🗑️", key=f"del_{i}"):
            st.session_state.tasks.pop(i)
            save_tasks(st.session_state.tasks)
            st.rerun()
