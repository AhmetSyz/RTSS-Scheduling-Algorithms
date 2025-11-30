import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from scheduler import Task,run_scheduler

tasks = []

def add_task():
    try:
        n = name_entry.get()
        c = int(cost_entry.get())
        p = int(period_entry.get())
        d = int(deadline_entry.get())
        
        # Create Task and add to list
        new_task = Task(n, 0, c, p, d)
        tasks.append(new_task)
        
        # Update listbox
        task_listbox.insert(tk.END, f"{n}: Cost={c}, Period={p}, Deadline={d}")
        
        # Clear inputs
        name_entry.delete(0, tk.END)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers for Cost/Period/Deadline")

def clear_tasks():
    tasks.clear()
    task_listbox.delete(0, tk.END)

def run_simulation():
    if not tasks:
        messagebox.showwarning("No Tasks", "Please add at least one task.")
        return

    algo = algo_combo.get()
    
    # 1. Run the Scheduler Logic
    timeline = run_scheduler(tasks, algo)
    
    # 2. Draw with Matplotlib
    draw_gantt_chart(timeline)

def draw_gantt_chart(timeline):
    """
    Draws a Gantt chart using Matplotlib in a new popup window
    """
    if not timeline:
        messagebox.showinfo("Result", "No timeline generated.")
        return

    fig, gnt = plt.subplots(figsize=(10, 5))
    
    # Setup X and Y axes
    simulation_time = timeline[-1]['Finish'] # Get last finish time
    gnt.set_xlim(0, simulation_time)
    gnt.set_xlabel('Time')
    gnt.set_ylabel('Tasks')
    
    # Set Y-ticks to show Task Names
    # Get unique task names from the timeline
    task_names = sorted(list(set(item['Task'] for item in timeline if item['Task'] != 'System')))
    yticks = [15 + 10 * i for i in range(len(task_names))]
    gnt.set_yticks(yticks)
    gnt.set_yticklabels(task_names)
    gnt.grid(True)
    
    # Colors for different statuses
    colors = {'Running': 'tab:blue', 'Idle': 'tab:gray', 'Missed': 'tab:red'}

    # Draw the bars
    for item in timeline:
        task_name = item['Task']
        start = item['Start']
        duration = item['Finish'] - item['Start']
        status = item['Status']
        
        if task_name == 'System': continue # Skip the dummy system block if present

        # Calculate Y position based on task name index
        y_pos = 10 + 10 * task_names.index(task_name)
        
        gnt.broken_barh([(start, duration)], (y_pos, 9), facecolors=colors.get(status, 'blue'))
        
        # Add text label inside the bar
        gnt.text(start + duration/2, y_pos + 4.5, str(duration), color='white', ha='center', va='center')

    plt.title(f"Scheduling Schedule")
    plt.show()

# --- MAIN WINDOW SETUP ---
root = tk.Tk()
root.title("RTOS Scheduler (Tkinter)")
root.geometry("400x500")

# Input Frame
input_frame = ttk.LabelFrame(root, text="New Task")
input_frame.pack(padx=10, pady=10, fill="x")

ttk.Label(input_frame, text="Name:").grid(row=0, column=0)
name_entry = ttk.Entry(input_frame, width=10)
name_entry.grid(row=0, column=1)

ttk.Label(input_frame, text="Cost (C):").grid(row=0, column=2)
cost_entry = ttk.Entry(input_frame, width=5)
cost_entry.grid(row=0, column=3)

ttk.Label(input_frame, text="Period (T):").grid(row=1, column=0)
period_entry = ttk.Entry(input_frame, width=5)
period_entry.grid(row=1, column=1)

ttk.Label(input_frame, text="Deadline (D):").grid(row=1, column=2)
deadline_entry = ttk.Entry(input_frame, width=5)
deadline_entry.grid(row=1, column=3)

add_btn = ttk.Button(input_frame, text="Add Task", command=add_task)
add_btn.grid(row=2, column=0, columnspan=4, pady=5)

# Task List
list_frame = ttk.LabelFrame(root, text="Current Tasks")
list_frame.pack(padx=10, pady=5, fill="both", expand=True)

task_listbox = tk.Listbox(list_frame, height=10)
task_listbox.pack(fill="both", expand=True, padx=5, pady=5)

clear_btn = ttk.Button(list_frame, text="Clear All", command=clear_tasks)
clear_btn.pack(pady=5)

# Control Frame
control_frame = ttk.Frame(root)
control_frame.pack(fill="x", padx=10, pady=10)

ttk.Label(control_frame, text="Algorithm:").pack(side="left")
algo_combo = ttk.Combobox(control_frame, values=["Rate Monotonic", "EDF"])
algo_combo.current(0)
algo_combo.pack(side="left", padx=5)

run_btn = ttk.Button(control_frame, text="RUN SIMULATION", command=run_simulation)
run_btn.pack(side="right")

root.mainloop()