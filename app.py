"""
PawPal+ Streamlit UI — connects directly to the pawpal_system logic layer.
AI feature: Claude explains the generated schedule via the Anthropic API.
"""
import os
import streamlit as st
from datetime import date, timedelta
import anthropic

from pawpal_system import Task, Pet, Owner, Scheduler

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling — now with AI-powered explanations.")

# ── Session state bootstrap ────────────────────────────────────────────────────
# Streamlit reruns the script on every interaction, so we persist the Owner
# object (and therefore all pets + tasks) in st.session_state.

if "owner" not in st.session_state:
    st.session_state.owner = None

# ── Sidebar: owner setup ───────────────────────────────────────────────────────

with st.sidebar:
    st.header("Owner Setup")
    owner_name = st.text_input("Owner name", value="Jordan")
    if st.button("Set / Reset Owner"):
        st.session_state.owner = Owner(name=owner_name)
        st.success(f"Owner set to {owner_name}")

    if st.session_state.owner:
        st.divider()
        st.header("Add a Pet")
        pet_name = st.text_input("Pet name", key="pet_name")
        species = st.selectbox("Species", ["dog", "cat", "bird", "other"], key="species")
        if st.button("Add Pet"):
            if pet_name.strip():
                st.session_state.owner.add_pet(Pet(name=pet_name.strip(), species=species))
                st.success(f"Added {pet_name} ({species})")
            else:
                st.error("Pet name cannot be empty.")

# ── Guard: require owner ───────────────────────────────────────────────────────

if st.session_state.owner is None:
    st.info("Set an owner name in the sidebar to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ── Add Tasks ──────────────────────────────────────────────────────────────────

st.subheader("Add a Task")

if not owner.pets:
    st.warning("Add at least one pet (sidebar) before scheduling tasks.")
else:
    col1, col2 = st.columns(2)
    with col1:
        target_pet = st.selectbox("For pet", [p.name for p in owner.pets])
        task_desc = st.text_input("Task description", value="Morning walk")
        task_time = st.text_input("Time (HH:MM)", value="08:00")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
        due = st.date_input("Due date", value=date.today())

    if st.button("Add Task"):
        # Validate HH:MM
        try:
            h, m = task_time.split(":")
            assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
        except Exception:
            st.error("Time must be in HH:MM format (e.g. 08:30).")
        else:
            new_task = Task(
                description=task_desc.strip(),
                time=task_time,
                duration_minutes=int(duration),
                priority=priority,
                frequency=frequency,
                due_date=due,
            )
            for pet in owner.pets:
                if pet.name == target_pet:
                    pet.add_task(new_task)
                    st.success(f"Task '{task_desc}' added to {target_pet}.")
                    break

# ── Current task table ─────────────────────────────────────────────────────────

st.divider()
st.subheader("All Tasks")

all_tasks = owner.get_all_tasks()
if not all_tasks:
    st.info("No tasks yet.")
else:
    rows = [
        {
            "Pet": p,
            "Description": t.description,
            "Time": t.time,
            "Duration": f"{t.duration_minutes}min",
            "Priority": t.priority,
            "Frequency": t.frequency,
            "Due": str(t.due_date),
            "Done": t.completed,
        }
        for p, t in all_tasks
    ]
    st.table(rows)

# ── Mark complete ──────────────────────────────────────────────────────────────

if all_tasks:
    st.subheader("Mark Task Complete")
    incomplete = [(p, t) for p, t in all_tasks if not t.completed]
    if incomplete:
        options = {f"{p} — {t.time} {t.description}": (p, t) for p, t in incomplete}
        chosen_label = st.selectbox("Select task to complete", list(options.keys()))
        if st.button("Mark Complete"):
            pet_name, task = options[chosen_label]
            scheduler = Scheduler(owner)
            scheduler.mark_task_complete(pet_name, task)
            if task.frequency in ("daily", "weekly"):
                delta = timedelta(days=1) if task.frequency == "daily" else timedelta(weeks=1)
                st.success(
                    f"Done! Next '{task.description}' scheduled for {task.due_date + delta}."
                )
            else:
                st.success(f"'{task.description}' marked complete.")
    else:
        st.success("All tasks are complete!")

# ── Generate Schedule ──────────────────────────────────────────────────────────

st.divider()
st.subheader("Generate Today's Schedule")

if st.button("Build Schedule"):
    scheduler = Scheduler(owner)
    schedule = scheduler.get_todays_schedule()
    conflicts = scheduler.detect_conflicts()

    if not schedule:
        st.info("No pending tasks for today.")
    else:
        # Display sorted schedule as a clean table
        st.success(f"Schedule built — {len(schedule)} task(s) pending.")
        rows = [
            {
                "Time": t.time,
                "Pet": p,
                "Task": t.description,
                "Duration": f"{t.duration_minutes}min",
                "Priority": t.priority,
                "Frequency": t.frequency,
            }
            for p, t in schedule
        ]
        st.table(rows)

        # Conflict warnings
        if conflicts:
            for c in conflicts:
                st.warning(f"⚠ {c}")
        else:
            st.success("No scheduling conflicts detected.")

        # ── AI Explanation (Claude) ────────────────────────────────────────────
        st.subheader("AI Schedule Explanation")
        plan_text = scheduler.generate_plan_text()

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.info(
                "Set the `ANTHROPIC_API_KEY` environment variable to enable "
                "AI-powered schedule explanations."
            )
        else:
            with st.spinner("Asking Claude to explain the schedule..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    message = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=512,
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    f"You are a helpful pet care assistant. "
                                    f"Here is today's schedule for a pet owner:\n\n"
                                    f"{plan_text}\n\n"
                                    f"In 3–5 sentences, explain why this ordering makes sense "
                                    f"for the pets' wellbeing, and flag any concerns you notice."
                                ),
                            }
                        ],
                    )
                    explanation = message.content[0].text
                    st.markdown("**Claude's take:**")
                    st.info(explanation)
                except anthropic.AuthenticationError:
                    st.error("Invalid API key. Check your ANTHROPIC_API_KEY.")
                except Exception as e:
                    st.error(f"AI explanation failed: {e}")
