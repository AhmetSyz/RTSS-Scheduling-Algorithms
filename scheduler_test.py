from scheduler import run_scheduler, Task
import pandas as pd

def print_result(test_name, success, message):
    icon = "✅" if success else "❌"
    print(f"{icon} {test_name}: {message}")

print("--- 🚀 STARTING AUTOMATED SCHEDULER TESTS ---")

# ==========================================
# TEST 1: Polling Server "Use it or Lose it"
# ==========================================
# Scenario: Server (Budget=2, Period=5). Job J1 Arrives at t=2.
# Polling: Should LOSE budget at t=0 (empty queue), so J1 waits until t=5.
# Deferrable: Should KEEP budget, so J1 runs immediately at t=2.

# 1A. Run Polling
server_type = "Polling Server"
j1 = Task("J1", "Aperiodic", 1, 0, 0, arrival=2)
res_poll, _ = run_scheduler([], [j1], "Rate Monotonic", 1, "Polling Server", 2, 5)

# Find when J1 started
start_poll = next((x['Start'] for x in res_poll if x['Task'] == 'J1'), -1)

# 1B. Run Deferrable
j1 = Task("J1", "Aperiodic", 1, 0, 0, arrival=2)
res_def, _ = run_scheduler([], [j1], "Rate Monotonic", 1, "Deferrable Server", 2, 5)
start_def = next((x['Start'] for x in res_def if x['Task'] == 'J1'), -1)

if start_poll >= 5 and start_def == 2:
    print_result("Polling vs Deferrable", True, f"Polling delayed to {start_poll}, Deferrable ran at {start_def}")
else:
    print_result("Polling vs Deferrable", False, f"Logic failed. Polling Start: {start_poll}, Deferrable Start: {start_def}")


# ==========================================
# TEST 2: Deadline Monotonic (Early Deadline)
# ==========================================
# Scenario: T1 (T=10, D=10, C=4), T2 (T=12, D=4, C=2).
# Algorithm: Rate Monotonic (T1 has higher priority because 10 < 12).
# Result: T1 runs 0-4. T2 starts 4. T2 Deadline is 4. T2 should MISS immediately.

t1 = Task("T1", "Periodic", 4, 10, 10, 0)
t2 = Task("T2", "Periodic", 2, 12, 4, 0)

res_dm, _ = run_scheduler([t1, t2], [], "Rate Monotonic", 1)

# Check for "Missed" status
missed_tasks = [x['Task'] for x in res_dm if x['Status'] == 'Missed']

if "T2" in missed_tasks:
    print_result("Deadline Miss Detection", True, "Detected T2 miss correctly.")
else:
    print_result("Deadline Miss Detection", False, "Failed to detect T2 deadline miss! (Likely checking at Period instead of Deadline)")

# ==========================================
# TEST 3: Multiprocessor Load Balancing
# ==========================================
# Scenario: 2 CPUs. 3 Tasks (C=2, T=10). All ready at 0.
# Expect: T1 on CPU1, T2 on CPU2, T3 waits.

t1 = Task("T1", "Periodic", 2, 10)
t2 = Task("T2", "Periodic", 2, 10)
t3 = Task("T3", "Periodic", 2, 10)

res_multi, logs = run_scheduler([t1, t2, t3], [], "Rate Monotonic", 2)

# Check Time 0
time_0_log = next((l for l in logs if l['Time'] == 0), {})
waiting = time_0_log.get("Waiting Queue", "")

if "T3" in waiting or "['T3']" in str(waiting):
    print_result("Multiprocessor Queue", True, "T3 correctly waited while CPUs were busy.")
else:
    print_result("Multiprocessor Queue", False, f"Queue logic error. Waiting: {waiting}")

print("\n--- TESTS COMPLETE ---")