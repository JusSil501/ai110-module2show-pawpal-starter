"""
CLI demo — run with: python main.py
Verifies sorting, filtering, recurrence, and conflict detection in the terminal.
"""
from datetime import date
from pawpal_system import Task, Pet, Owner, Scheduler


def main():
    owner = Owner(name="Jordan")

    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")

    # Tasks added OUT OF ORDER to exercise sorting
    mochi.add_task(Task("Evening walk",   "18:00", 30, "high",   "daily"))
    mochi.add_task(Task("Morning walk",   "08:00", 20, "high",   "daily"))
    mochi.add_task(Task("Lunch feeding",  "12:00",  5, "medium", "daily"))
    mochi.add_task(Task("Morning feeding","07:30",  5, "high",   "daily"))

    luna.add_task(Task("Grooming",  "10:00", 15, "medium", "weekly"))
    luna.add_task(Task("Playtime",  "16:00", 20, "low",    "daily"))
    # Same time as Mochi's morning walk → conflict
    luna.add_task(Task("Medicine",  "08:00",  5, "high",   "daily"))

    owner.add_pet(mochi)
    owner.add_pet(luna)

    scheduler = Scheduler(owner)

    # ── Today's sorted schedule (includes conflict warning) ────────────────────
    print(scheduler.generate_plan_text())
    print()

    # ── Filter: Mochi only ─────────────────────────────────────────────────────
    print("Mochi's tasks (sorted):")
    for _, task in scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi")):
        print(f"  {task.time}  {task.description}  [{task.frequency}]")
    print()

    # ── Recurrence: complete Mochi's morning walk ──────────────────────────────
    morning_walk = mochi.tasks[1]   # "Morning walk" at 08:00
    scheduler.mark_task_complete("Mochi", morning_walk)
    print(f"Marked '{morning_walk.description}' complete.")
    print("Mochi's pending tasks after completion:")
    for _, task in scheduler.filter_tasks(pet_name="Mochi", completed=False):
        print(f"  {task.time}  {task.description}  due:{task.due_date}")


if __name__ == "__main__":
    main()
