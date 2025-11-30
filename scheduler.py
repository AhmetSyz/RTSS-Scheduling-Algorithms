import math
import copy
from functools import reduce

class Task:
    def __init__(self, name, task_type, cost, period=0, deadline=0, arrival=0):
        self.name = name
        self.type = task_type  # "Periodic" or "Aperiodic"
        self.arrival_time = arrival
        self.cost = cost
        self.period = period if period > 0 else 0
        
        # Default Deadline logic
        if deadline == 0 and period > 0:
            self.deadline = period
        else:
            self.deadline = deadline

        # Runtime State
        self.remaining_time = 0     
        self.abs_deadline = 0      

def _lcm(a, b):
    return abs(a * b) // math.gcd(a, b)

def calculate_hyperperiod(tasks):
    periodic_tasks = [t for t in tasks if t.type == "Periodic"]
    if not periodic_tasks: return 20
    periods = [t.period for t in periodic_tasks]
    h = reduce(_lcm, periods)
    max_offset = max([t.arrival_time for t in tasks]) if tasks else 0
    return max_offset + h

def run_scheduler(periodic_tasks, aperiodic_tasks, algorithm, num_cpus, server_type=None, server_capacity=0, server_period=0):
    
    # 1. SETUP
    hyperperiod = calculate_hyperperiod(periodic_tasks)
    active_periodic = copy.deepcopy(periodic_tasks)
    aperiodic_queue = copy.deepcopy(aperiodic_tasks)
    
    server_budget = server_capacity
    server_deadline = server_period
    
    timeline = [] 
    queue_log = [] # <--- Stores row-by-row data for the table

    # 2. SIMULATION LOOP
    for t in range(hyperperiod):
        
        # --- A. SERVER REPLENISHMENT ---
        if server_type == "Deferrable Server":
            if t % server_period == 0:
                server_budget = server_capacity
                server_deadline = t + server_period

        # --- B. PERIODIC ARRIVALS ---
        for task in active_periodic:
            time_since_release = t - task.arrival_time
            if t >= task.arrival_time and (time_since_release % task.period == 0):
                if task.remaining_time > 0 and t > task.arrival_time:
                    timeline.append(dict(Task=task.name, Start=t, Finish=t, Status="Missed", CPU="Err"))
                task.remaining_time = task.cost
                task.abs_deadline = t + task.deadline

        # --- C. APERIODIC ARRIVALS ---
        # Get tasks that have arrived (Arrival <= t) and are not finished
        ready_aperiodic = [at for at in aperiodic_queue if at.arrival_time <= t and at.remaining_time > 0]

        # --- D. BUILD GLOBAL READY QUEUE (Periodic + Server) ---
        global_ready_queue = []
        for pt in active_periodic:
            if pt.remaining_time > 0:
                global_ready_queue.append(pt)
        
        if server_type == "Deferrable Server":
            if server_budget > 0 and ready_aperiodic:
                server_task = Task("Server", "Server", 1, server_period, server_period)
                server_task.abs_deadline = server_deadline 
                global_ready_queue.append(server_task)

        # --- E. SORTING ---
        if algorithm == "Rate Monotonic":
            global_ready_queue.sort(key=lambda x: x.period)
            
        elif algorithm == "Deadline Monotonic":
            # Priority: Shortest Relative Deadline (D)
            # This uses the static 'deadline' attribute, not the calculated 'abs_deadline'
            global_ready_queue.sort(key=lambda x: x.deadline)

        elif algorithm == "EDF":
            # Priority: Earliest Absolute Deadline (d)
            global_ready_queue.sort(key=lambda x: x.abs_deadline)
            
        elif algorithm == "Least Laxity First":
            # Priority: Least Laxity
            # Laxity = (Time until deadline) - (Work remaining)
            # Formula: (x.abs_deadline - t) - x.remaining_time
            global_ready_queue.sort(key=lambda x: (x.abs_deadline - t - x.remaining_time))

        # --- F. EXECUTION & LOGGING PREP ---
        cpus_assigned = 0
        execution_candidates = global_ready_queue[:]
        
        # Create a log entry for this timestamp
        log_entry = {"Time": t}
        running_tasks_this_tick = []

        while cpus_assigned < num_cpus:
            cpu_label = f"CPU {cpus_assigned + 1}"
            
            if execution_candidates:
                task_to_run = execution_candidates.pop(0)
                
                # Logic for Server Execution
                if task_to_run.name == "Server":
                    target_aperiodic = ready_aperiodic[0]
                    timeline.append(dict(Task=target_aperiodic.name, Start=t, Finish=t+1, Status="Server Exec", CPU=cpu_label))
                    
                    # Log real name
                    log_entry[cpu_label] = f"Server({target_aperiodic.name})"
                    running_tasks_this_tick.append(target_aperiodic.name)
                    
                    target_aperiodic.remaining_time -= 1
                    server_budget -= 1
                else:
                    # Logic for Periodic Execution
                    timeline.append(dict(Task=task_to_run.name, Start=t, Finish=t+1, Status="Running", CPU=cpu_label))
                    
                    log_entry[cpu_label] = task_to_run.name
                    running_tasks_this_tick.append(task_to_run.name)
                    
                    task_to_run.remaining_time -= 1
            else:
                # Logic for Background Execution
                if server_type == "Background" and ready_aperiodic:
                    # Find first aperiodic task that is NOT already running on another CPU
                    available_ap = [ap for ap in ready_aperiodic if ap.name not in running_tasks_this_tick]
                    
                    if available_ap:
                        bg_task = available_ap[0]
                        timeline.append(dict(Task=bg_task.name, Start=t, Finish=t+1, Status="Background", CPU=cpu_label))
                        
                        log_entry[cpu_label] = f"{bg_task.name}(BG)"
                        running_tasks_this_tick.append(bg_task.name)
                        
                        bg_task.remaining_time -= 1
                    else:
                        timeline.append(dict(Task="IDLE", Start=t, Finish=t+1, Status="Idle", CPU=cpu_label))
                        log_entry[cpu_label] = "IDLE"
                else:
                    timeline.append(dict(Task="IDLE", Start=t, Finish=t+1, Status="Idle", CPU=cpu_label))
                    log_entry[cpu_label] = "IDLE"
            
            cpus_assigned += 1

        # --- G. CALCULATE WAITING QUEUE ---
        waiting_list = []
        
        # 1. Periodic tasks still in execution_candidates (not picked by any CPU)
        for tsk in execution_candidates:
            waiting_list.append(tsk.name)
            
        # 2. Aperiodic tasks that are ready but NOT in the running list
        for ap in ready_aperiodic:
            if ap.name not in running_tasks_this_tick:
                waiting_list.append(f"{ap.name}(AP)")
        
        log_entry["Waiting Queue"] = str(waiting_list) if waiting_list else "Empty"
        
        queue_log.append(log_entry)

    return timeline, queue_log