import os
import sys
import glob

# --- BOOTSTRAP FIX FOR TCL/TK ERROR ---
# This must run BEFORE importing tkinter
def fix_tcl_tk_path():
    # This function tries multiple heuristics to set TCL/TK env vars so
    # Tkinter can find its runtime files both when running normally and
    # when bundled by PyInstaller (extracted to sys._MEIPASS).
    if sys.platform != "win32":
        return

    # 1) If running from a PyInstaller bundle, prefer the extracted _MEIPASS path
    meipass = getattr(sys, '_MEIPASS', None)
    candidates = []
    if meipass:
        candidates.append(os.path.join(meipass, 'tcl', 'tcl8.6'))
        candidates.append(os.path.join(meipass, 'tcl', 'tk8.6'))

    # 2) Check the Python installation directory used by this interpreter
    python_dir = os.path.dirname(sys.executable)
    candidates.append(os.path.join(python_dir, 'tcl', 'tcl8.6'))
    candidates.append(os.path.join(python_dir, 'tcl', 'tk8.6'))
    candidates.append(os.path.join(python_dir, 'Lib', 'tcl8.6'))
    candidates.append(os.path.join(python_dir, 'Lib', 'tk8.6'))

    # 3) Common fallback locations (user-local Python installs)
    local_python = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python')
    if os.path.exists(local_python):
        for root, dirs, _ in os.walk(local_python):
            if 'tcl' in dirs:
                candidates.append(os.path.join(root, 'tcl', 'tcl8.6'))
                candidates.append(os.path.join(root, 'tcl', 'tk8.6'))

    # Find the first pair that exists and set env vars accordingly
    found_tcl = None
    found_tk = None
    for path in candidates:
        if path.endswith('tcl8.6') and os.path.exists(path):
            found_tcl = path
        if path.endswith('tk8.6') and os.path.exists(path):
            found_tk = path
        if found_tcl and found_tk:
            break

    if found_tcl and found_tk:
        os.environ['TCL_LIBRARY'] = found_tcl
        os.environ['TK_LIBRARY'] = found_tk
        # Helpful message when running locally
        try:
            print(f"Fixed Tcl/Tk paths:\n TCL: {found_tcl}\n TK:  {found_tk}")
        except Exception:
            pass
    else:
        # Best-effort: fall back to standard behavior and let import fail visibly
        print('Warning: Could not auto-detect Tcl/Tk paths. Tkinter may fail when bundled.')

fix_tcl_tk_path()
# --------------------------------------

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scheduler import run_scheduler, Task

# --- MAIN APPLICATION CLASS ---
class RTOSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RTOS Scheduler (Desktop Edition)")
        self.root.geometry("1000x800")

        # Data Stores
        self.periodic_tasks = []
        self.aperiodic_tasks = []

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        # Create Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Configuration & Inputs
        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="Configuration & Tasks")
        self.setup_config_tab()

        # Tab 2: Results & Chart
        self.tab_results = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_results, text="Simulation Results")
        self.setup_results_tab()

    def setup_config_tab(self):
        # --- LEFT PANEL: SETTINGS ---
        left_frame = ttk.LabelFrame(self.tab_config, text="System Settings")
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        # Algorithm
        ttk.Label(left_frame, text="Algorithm:").pack(anchor="w", padx=5)
        self.algo_var = tk.StringVar(value="Rate Monotonic")
        algo_combo = ttk.Combobox(left_frame, textvariable=self.algo_var, state="readonly")
        algo_combo['values'] = ("Rate Monotonic", "Deadline Monotonic", "EDF", "Least Laxity First")
        algo_combo.pack(fill="x", padx=5, pady=5)

        # CPUs
        ttk.Label(left_frame, text="CPUs:").pack(anchor="w", padx=5)
        self.cpu_var = tk.IntVar(value=1)
        ttk.Spinbox(left_frame, from_=1, to=4, textvariable=self.cpu_var).pack(fill="x", padx=5, pady=5)

        # Server Settings
        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(left_frame, text="Server Mode:").pack(anchor="w", padx=5)
        self.server_var = tk.StringVar(value="None")
        server_combo = ttk.Combobox(left_frame, textvariable=self.server_var, state="readonly")
        server_combo['values'] = ("None", "Background", "Deferrable Server", "Polling Server")
        server_combo.pack(fill="x", padx=5, pady=5)
        server_combo.bind("<<ComboboxSelected>>", self.toggle_server_inputs)

        self.server_frame = ttk.Frame(left_frame)
        self.server_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(self.server_frame, text="Budget (Cs):").grid(row=0, column=0)
        self.budget_var = tk.IntVar(value=2)
        ttk.Entry(self.server_frame, textvariable=self.budget_var, width=5).grid(row=0, column=1)
        
        ttk.Label(self.server_frame, text="Period (Ts):").grid(row=1, column=0)
        self.period_var = tk.IntVar(value=5)
        ttk.Entry(self.server_frame, textvariable=self.period_var, width=5).grid(row=1, column=1)
        
        self.toggle_server_inputs() # Hide initially if None

        # --- RIGHT PANEL: TASKS ---
        right_frame = ttk.Frame(self.tab_config)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # File Operations
        file_frame = ttk.LabelFrame(right_frame, text="File Operations")
        file_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(file_frame, text="📂 Load Task File (.txt)", command=self.load_file).pack(side="left", padx=5, pady=5)
        ttk.Button(file_frame, text="❌ Clear All Tasks", command=self.clear_tasks).pack(side="right", padx=5, pady=5)

        # Task Lists
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill="both", expand=True)

        # Periodic List
        p_frame = ttk.LabelFrame(list_frame, text="Periodic Tasks")
        p_frame.pack(side="left", fill="both", expand=True, padx=5)
        self.p_listbox = tk.Listbox(p_frame)
        self.p_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Aperiodic List
        a_frame = ttk.LabelFrame(list_frame, text="Aperiodic Tasks")
        a_frame.pack(side="right", fill="both", expand=True, padx=5)
        self.a_listbox = tk.Listbox(a_frame)
        self.a_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Manual Add Frame
        add_frame = ttk.LabelFrame(right_frame, text="Manual Add Task")
        add_frame.pack(fill="x", padx=5, pady=5)
        
        # Grid Layout for Inputs
        input_grid = ttk.Frame(add_frame)
        input_grid.pack(fill="x", padx=5, pady=5)
        
        # Row 1: Labels
        ttk.Label(input_grid, text="Name").grid(row=0, column=0, padx=2)
        ttk.Label(input_grid, text="Cost (C)").grid(row=0, column=1, padx=2)
        ttk.Label(input_grid, text="Period (T)").grid(row=0, column=2, padx=2)
        ttk.Label(input_grid, text="Deadline (D)").grid(row=0, column=3, padx=2)
        ttk.Label(input_grid, text="Arrival (R)").grid(row=0, column=4, padx=2)
        
        # Row 2: Entries
        self.ent_name = ttk.Entry(input_grid, width=8)
        self.ent_name.grid(row=1, column=0, padx=2)
        
        self.ent_cost = ttk.Entry(input_grid, width=5)
        self.ent_cost.grid(row=1, column=1, padx=2)
        
        self.ent_period = ttk.Entry(input_grid, width=5)
        self.ent_period.grid(row=1, column=2, padx=2)
        
        self.ent_deadline = ttk.Entry(input_grid, width=5)
        self.ent_deadline.grid(row=1, column=3, padx=2)
        
        self.ent_arrival = ttk.Entry(input_grid, width=5)
        self.ent_arrival.grid(row=1, column=4, padx=2)
        self.ent_arrival.insert(0, "0") # Default arrival 0

        # Buttons
        btn_frame = ttk.Frame(add_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Add Periodic", command=lambda: self.add_manual("P")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Add Aperiodic", command=lambda: self.add_manual("A")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Inputs", command=self.clear_inputs).pack(side="right", padx=5)

    def setup_results_tab(self):
        # Controls at top
        top_frame = ttk.Frame(self.tab_results)
        top_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(top_frame, text="🚀 RUN SIMULATION", command=self.run_simulation).pack(fill="x", pady=5)

        # Matplotlib Figure
        self.fig, (self.ax_gantt, self.ax_budget) = plt.subplots(2, 1, figsize=(8, 6), gridspec_kw={'height_ratios': [3, 1]})
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_results)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Log Area
        self.log_text = tk.Text(self.tab_results, height=8)
        self.log_text.pack(fill="x", padx=5, pady=5)

    # --- LOGIC FUNCTIONS ---

    def toggle_server_inputs(self, event=None):
        if self.server_var.get() in ["Deferrable Server", "Polling Server"]:
            for child in self.server_frame.winfo_children():
                child.configure(state='normal')
        else:
            for child in self.server_frame.winfo_children():
                child.configure(state='disabled')

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Task Files", "*.txt *.csv"), ("Text Files", "*.txt"), ("CSV Files", "*.csv")])
        if not filepath: return

        try:
            self.clear_tasks()
            if filepath.lower().endswith('.csv'):
                self.load_csv(filepath)
            else:
                self.load_txt(filepath)
            
            messagebox.showinfo("Success", f"Loaded {len(self.periodic_tasks)} Periodic and {len(self.aperiodic_tasks)} Aperiodic tasks.")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_txt(self, filepath):
        with open(filepath, 'r') as f:
            p_count = 1
            a_count = 1
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                
                parts = line.split()
                code = parts[0].upper()
                
                try:
                    vals = [int(x) for x in parts[1:]]
                    
                    if code.startswith("P"):
                        if len(vals) == 4: r, c, p, d = vals
                        elif len(vals) == 3: r, c, p = vals; d = p
                        elif len(vals) == 2: c, p = vals; r = 0; d = p
                        else: continue
                        
                        t = Task(f"T{p_count}", "Periodic", c, p, d, r)
                        self.periodic_tasks.append(t)
                        self.p_listbox.insert(tk.END, f"{t.name}: C={c} T={p} D={d} R={r}")
                        p_count += 1
                        
                    elif code.startswith("A"):
                        if len(vals) == 2: r, c = vals
                        else: continue
                        
                        t = Task(f"J{a_count}", "Aperiodic", c, 0, 0, r)
                        self.aperiodic_tasks.append(t)
                        self.a_listbox.insert(tk.END, f"{t.name}: Arrival={r} Cost={c}")
                        a_count += 1
                        
                except ValueError:
                    continue

    def load_csv(self, filepath):
        import csv
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            # Normalize headers to lower case strip
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
            
            p_count = 1
            a_count = 1
            
            for row in reader:
                try:
                    # Type,Name,Cost,Period,Arrival,Deadline
                    r_type = row.get('type', '').strip().title()
                    r_name = row.get('name', '').strip()
                    r_cost = int(row.get('cost', 0))
                    r_period = int(row.get('period', 0))
                    r_arrival = int(row.get('arrival', 0))
                    r_deadline = int(row.get('deadline', 0))
                    
                    if r_type == "Periodic":
                        if not r_name: r_name = f"T{p_count}"
                        if r_deadline == 0 and r_period > 0: r_deadline = r_period
                        
                        t = Task(r_name, "Periodic", r_cost, r_period, r_deadline, r_arrival)
                        self.periodic_tasks.append(t)
                        self.p_listbox.insert(tk.END, f"{t.name}: C={r_cost} T={r_period} D={r_deadline} R={r_arrival}")
                        p_count += 1
                        
                    elif r_type == "Aperiodic":
                        if not r_name: r_name = f"J{a_count}"
                        
                        t = Task(r_name, "Aperiodic", r_cost, 0, 0, r_arrival)
                        self.aperiodic_tasks.append(t)
                        self.a_listbox.insert(tk.END, f"{t.name}: Arrival={r_arrival} Cost={r_cost}")
                        a_count += 1
                except ValueError:
                    continue

    def clear_tasks(self):
        self.periodic_tasks = []
        self.aperiodic_tasks = []
        self.p_listbox.delete(0, tk.END)
        self.a_listbox.delete(0, tk.END)

    def clear_inputs(self):
        self.ent_name.delete(0, tk.END)
        self.ent_cost.delete(0, tk.END)
        self.ent_period.delete(0, tk.END)
        self.ent_deadline.delete(0, tk.END)
        self.ent_arrival.delete(0, tk.END)
        self.ent_arrival.insert(0, "0")

    def add_manual(self, type_char):
        try:
            name = self.ent_name.get().strip()
            if not name:
                messagebox.showwarning("Input Error", "Task Name is required.")
                return

            try:
                cost = int(self.ent_cost.get())
            except ValueError:
                messagebox.showwarning("Input Error", "Cost must be an integer.")
                return

            arrival = 0
            if self.ent_arrival.get().strip():
                try:
                    arrival = int(self.ent_arrival.get())
                except ValueError:
                    messagebox.showwarning("Input Error", "Arrival must be an integer.")
                    return

            if type_char == "P":
                try:
                    period = int(self.ent_period.get())
                except ValueError:
                    messagebox.showwarning("Input Error", "Period is required for Periodic tasks.")
                    return
                
                deadline = period
                if self.ent_deadline.get().strip():
                    try:
                        deadline = int(self.ent_deadline.get())
                    except ValueError:
                        pass # Keep default

                t = Task(name, "Periodic", cost, period, deadline, arrival)
                self.periodic_tasks.append(t)
                self.p_listbox.insert(tk.END, f"{t.name}: C={cost} T={period} D={deadline} R={arrival}")
            
            else: # Aperiodic
                t = Task(name, "Aperiodic", cost, 0, 0, arrival)
                self.aperiodic_tasks.append(t)
                self.a_listbox.insert(tk.END, f"{t.name}: Arrival={arrival} Cost={cost}")
                
            # Clear Name and Cost for next entry, keep others potentially
            self.ent_name.delete(0, tk.END)
            self.ent_cost.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def run_simulation(self):
        if not self.periodic_tasks and not self.aperiodic_tasks:
            messagebox.showwarning("Warning", "No tasks defined!")
            return

        try:
            results, queue_log = run_scheduler(
                self.periodic_tasks,
                self.aperiodic_tasks,
                self.algo_var.get(),
                self.cpu_var.get(),
                self.server_var.get(),
                self.budget_var.get(),
                self.period_var.get()
            )
            
            self.notebook.select(self.tab_results)
            
            self.ax_gantt.clear()
            self.ax_budget.clear()
            
            colors = {'Running': 'tab:blue', 'Server Exec': 'tab:green', 'Background': 'tab:purple', 'Missed': 'red', 'Idle': 'lightgrey'}
            
            task_names = []
            for item in results:
                if item['Task'] not in task_names and item['Task'] != 'IDLE':
                    task_names.append(item['Task'])
            task_names.sort()
            
            y_map = {name: i for i, name in enumerate(task_names)}
            y_map['IDLE'] = -1 
            
            for item in results:
                t_name = item['Task']
                if t_name == 'IDLE': continue
                
                start = item['Start']
                dur = item['Finish'] - start
                status = item['Status']
                
                self.ax_gantt.barh(y_map[t_name], dur, left=start, height=0.6, 
                                   color=colors.get(status, 'gray'), edgecolor='black')
                
                self.ax_gantt.text(start + dur/2, y_map[t_name], item['CPU'], 
                                   ha='center', va='center', color='white', fontsize=8)

            max_time = results[-1]['Finish'] if results else 20
            
            for t in self.periodic_tasks:
                if t.name in y_map:
                    arr = t.arrival_time
                    while arr <= max_time:
                        self.ax_gantt.plot(arr, y_map[t.name] + 0.4, marker='v', color='black', markersize=8)
                        arr += t.period
                        
            for t in self.aperiodic_tasks:
                if t.name in y_map and t.arrival_time <= max_time:
                    self.ax_gantt.plot(t.arrival_time, y_map[t.name] + 0.4, marker='v', color='red', markersize=8)

            self.ax_gantt.set_yticks(range(len(task_names)))
            self.ax_gantt.set_yticklabels(task_names)
            self.ax_gantt.set_xlabel("Time")
            self.ax_gantt.set_title("Task Execution Gantt Chart")
            self.ax_gantt.grid(True, axis='x', linestyle='--', alpha=0.7)
            self.ax_gantt.set_xlim(0, max_time)

            if self.server_var.get() in ["Deferrable Server", "Polling Server"]:
                times = [log['Time'] for log in queue_log]
                budgets = [log['Server Budget'] for log in queue_log]
                
                self.ax_budget.step(times, budgets, where='post', color='green')
                self.ax_budget.set_ylabel("Budget")
                self.ax_budget.set_ylim(-0.5, self.budget_var.get() + 0.5)
                self.ax_budget.grid(True)
                self.ax_budget.set_title("Server Budget Monitor")
            else:
                self.ax_budget.text(0.5, 0.5, "No Server Active", ha='center', va='center')

            self.fig.tight_layout()
            self.canvas.draw()

            self.log_text.delete(1.0, tk.END)
            header = f"{'Time':<5} | {'Running':<20} | {'Budget':<8} | {'Queue'}\n"
            self.log_text.insert(tk.END, header)
            self.log_text.insert(tk.END, "-"*60 + "\n")
            
            for log in queue_log:
                run_str = ""
                for k, v in log.items():
                    if k.startswith("CPU"): run_str += f"{v} "
                
                line = f"{log['Time']:<5} | {run_str:<20} | {log.get('Server Budget', '-'):<8} | {log['Waiting Queue']}\n"
                self.log_text.insert(tk.END, line)

        except Exception as e:
            messagebox.showerror("Simulation Error", str(e))
            raise e

if __name__ == "__main__":
    root = tk.Tk()
    app = RTOSApp(root)
    root.mainloop()