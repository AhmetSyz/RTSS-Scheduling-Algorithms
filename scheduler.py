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
        
        if deadline == 0 and period > 0:
            self.deadline = period
        else:
            self.deadline = deadline

        # Runtime State
        self.remaining_time = 0     
        self.abs_deadline = 0      

def _lcm(a, b):
    if a == 0 or b == 0: return 0
    return abs(a * b) // math.gcd(a, b)

def calculate_hyperperiod(tasks):
    periodic_tasks = [t for t in tasks if t.type == "Periodic"]
    if not periodic_tasks: return 20
    periods = [t.period for t in periodic_tasks]
    if not periods: return 20
    h = reduce(_lcm, periods)
    max_offset = max([t.arrival_time for t in tasks]) if tasks else 0
    return max_offset + h

def run_scheduler(periodic_tasks, aperiodic_tasks, algorithm, num_cpus, server_type=None, server_capacity=0, server_period=0):
    
    # 1. SETUP
    hyperperiod = calculate_hyperperiod(periodic_tasks)
    # Ensure hyperperiod is reasonable for visualization
    if hyperperiod > 100: hyperperiod = 100 
    
    active_periodic = copy.deepcopy(periodic_tasks)
    aperiodic_queue = copy.deepcopy(aperiodic_tasks)
    
    # Init Aperiodic Tasks
    for ap_task in aperiodic_queue:
        ap_task.remaining_time = ap_task.cost
    
    server_budget = server_capacity
    server_deadline = server_period
    
    timeline = [] 
    queue_log = [] 

    # 2. SIMULATION LOOP
    for t in range(hyperperiod):
        
        # --- A. DEADLINE CHECK ---
        for task in active_periodic:
            if task.remaining_time > 0 and t >= task.abs_deadline and task.abs_deadline > 0:
                timeline.append(dict(Task=task.name, Start=t, Finish=t,
                         Status="Missed", CPU="Err"))
                task.remaining_time = 0  # Drop job

        # --- B. PERIODIC ARRIVALS ---
        for task in active_periodic:
            time_since_release = t - task.arrival_time
            # Check if it's an arrival time (start of period)
            if t >= task.arrival_time and ((t - task.arrival_time) % task.period == 0):
                task.remaining_time = task.cost
                task.abs_deadline = t + task.deadline

        # --- C. APERIODIC ARRIVALS & SERVER REPLENISHMENT ---
        
        # Replenish Server at start of its period
        if server_type in ["Deferrable Server", "Polling Server"]:
            if t % server_period == 0:
                server_budget = server_capacity
                server_deadline = t + server_period

        # Identify Ready Aperiodic Tasks
        ready_aperiodic = [at for at in aperiodic_queue if at.arrival_time <= t and at.remaining_time > 0]

        # --- POLLING SERVER LOGIC ---
        # Polling Server: Capacity is lost if no tasks are ready when the server is polled (or if queue becomes empty).
        if server_type == "Polling Server":
            if server_budget > 0 and not ready_aperiodic:
                server_budget = 0 

        # --- D. BUILD READY QUEUE ---
        global_ready_queue = []
        
        # 1. Add Periodic Tasks
        for pt in active_periodic:
            if pt.remaining_time > 0:
                global_ready_queue.append(pt)
        
        # 2. Add Server Task (if applicable)
        # We only add the server if it has budget AND there is work to do.
        # For Deferrable Server, it preserves budget, so we only schedule it when needed.
        if server_type in ["Deferrable Server", "Polling Server"]:
            if server_budget > 0 and ready_aperiodic:
                # Create a virtual server task for this tick
                # It has the priority properties defined by the algorithm
                server_task = Task("Server", "Server", 1, server_period, server_period)
                server_task.abs_deadline = server_deadline 
                global_ready_queue.append(server_task)

        # --- E. SORTING (SCHEDULING ALGORITHM) ---
        if algorithm == "Rate Monotonic":
            # Static Priority: Shorter Period = Higher Priority
            global_ready_queue.sort(key=lambda x: x.period)
            
        elif algorithm == "Deadline Monotonic":
            # Static Priority: Shorter Relative Deadline = Higher Priority
            global_ready_queue.sort(key=lambda x: x.deadline)
            
        elif algorithm == "EDF":
            # Dynamic Priority: Earlier Absolute Deadline = Higher Priority
            global_ready_queue.sort(key=lambda x: x.abs_deadline)
            
        elif algorithm == "Least Laxity First":
            # Dynamic Priority: Least Laxity = Higher Priority
            # Laxity = (Absolute Deadline - Current Time) - Remaining Time
            # Note: For the Server Task, remaining time is 1 (chunk), but effectively it represents the aperiodic task.
            # We use the calculated laxity for the current chunk.
            global_ready_queue.sort(key=lambda x: (x.abs_deadline - t - x.remaining_time))

        # --- F. EXECUTION ---
        cpus_assigned = 0
        execution_candidates = global_ready_queue[:]
        
        log_entry = {"Time": t}
        running_tasks_this_tick = []

        while cpus_assigned < num_cpus:
            cpu_label = f"CPU {cpus_assigned + 1}"
            
            if execution_candidates:
                task_to_run = execution_candidates.pop(0)
                
                # --- CASE 1: SERVER EXECUTION ---
                if task_to_run.name == "Server":
                    target_aperiodic = ready_aperiodic[0] # FIFO for aperiodic
                    
                    timeline.append(dict(Task=target_aperiodic.name, Start=t, Finish=t+1, Status="Server Exec", CPU=cpu_label))
                    log_entry[cpu_label] = f"Server({target_aperiodic.name})"
                    running_tasks_this_tick.append(target_aperiodic.name)
                    
                    target_aperiodic.remaining_time -= 1
                    if server_budget > 0:
                        server_budget -= 1
                        
                # --- CASE 2: PERIODIC TASK EXECUTION ---
                else:
                    timeline.append(dict(Task=task_to_run.name, Start=t, Finish=t+1, Status="Running", CPU=cpu_label))
                    log_entry[cpu_label] = task_to_run.name
                    running_tasks_this_tick.append(task_to_run.name)
                    task_to_run.remaining_time -= 1
            else:
                # --- CASE 3: BACKGROUND EXECUTION (Idle CPU) ---
                if server_type == "Background" and ready_aperiodic:
                    # Find an aperiodic task that isn't already running (if multiple CPUs)
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

        # --- G. LOGGING ---
        waiting_list = []
        # Log periodic tasks waiting
        for pt in active_periodic:
            if pt.remaining_time > 0 and pt.name not in running_tasks_this_tick:
                waiting_list.append(pt.name)
        # Log aperiodic tasks waiting
        for ap in ready_aperiodic:
            if ap.name not in running_tasks_this_tick:
                waiting_list.append(f"{ap.name}(AP)")
        
        log_entry["Waiting Queue"] = str(waiting_list) if waiting_list else "Empty"
        log_entry["Server Budget"] = server_budget
        queue_log.append(log_entry)

    return timeline, queue_log