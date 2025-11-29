import math
import copy
from functools import reduce

class Task:
    def __init__(self, name, arrival, cost, period, deadline):
        self.name = name
        self.arrival = arrival
        self.cost = cost
        self.period = period
        self.deadline = deadline
        
        # Simulation state
        self.remaining_time = 0
        self.abs_deadline = 0

def _lcm(a, b):
    return abs(a * b) // math.gcd(a, b)

def calculate_hyperperiod(tasks):
    if not tasks: return 20 
    periods = [task.period for task in tasks]
    return reduce(_lcm, periods)

def run_scheduler(tasks, algorithm):
    # 1. Setup Simulation
    hyperperiod = calculate_hyperperiod(tasks)
    
    # Create a deep copy so we don't mess up the UI's task list
    active_tasks = copy.deepcopy(tasks)
    
    # SORTING LOGIC (The Core Difference)
    if algorithm == "Rate Monotonic":
        # RM: Sort by Period (Smallest Period first)
        active_tasks.sort(key=lambda x: x.period)
    elif algorithm == "EDF":
        # EDF is dynamic, we sort inside the loop
        pass 

    timeline = []
    
    # 2. The Clock Loop (0 to Hyperperiod)
    for t in range(hyperperiod):
        
        # A. Check for Task Arrivals
        for task in active_tasks:
            # If time is a multiple of period, a new instance arrives
            if t % task.period == 0:
                # Check if previous instance failed (Deadline Miss)
                if task.remaining_time > 0:
                    timeline.append(dict(Task=task.name, Start=t, Finish=t, Status="Missed"))
                
                # Reset for new instance
                task.remaining_time = task.cost
                task.abs_deadline = t + task.deadline

        # B. Select High Priority Task
        # Filter tasks that are ready (have work to do)
        ready_queue = [task for task in active_tasks if task.remaining_time > 0]
        
        if algorithm == "EDF":
            # EDF: Sort ready queue by Absolute Deadline
            ready_queue.sort(key=lambda x: x.abs_deadline)
        
        # C. Execute
        if ready_queue:
            current_task = ready_queue[0] # Pick the first one (Highest Priority)
            
            # Record execution (1 tick)
            # Optimization: Try to merge with previous block if same task
            if timeline and timeline[-1]['Task'] == current_task.name and timeline[-1]['Finish'] == t:
                timeline[-1]['Finish'] += 1
            else:
                timeline.append(dict(Task=current_task.name, Start=t, Finish=t+1, Status="Running"))
            
            current_task.remaining_time -= 1
        else:
            # CPU is Idle
            if timeline and timeline[-1]['Task'] == "IDLE" and timeline[-1]['Finish'] == t:
                timeline[-1]['Finish'] += 1
            else:
                timeline.append(dict(Task="IDLE", Start=t, Finish=t+1, Status="Idle"))

    return timeline