# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from scheduler import run_scheduler, Task # Import your logic

st.set_page_config(page_title="RTOS Simulator", layout="wide")

st.title("Real-Time Scheduling Simulator")

# --- SIDEBAR: INPUTS ---
st.sidebar.header("Configuration")
algorithm = st.sidebar.selectbox("Select Algorithm", ["Rate Monotonic", "EDF"])

# Simple way to add tasks for now
st.sidebar.subheader("Add Task")
name = st.sidebar.text_input("Task Name", "T1")
cost = st.sidebar.number_input("Computation Cost (Ci)", min_value=1, value=2)
period = st.sidebar.number_input("Period (Ti)", min_value=1, value=10)

if st.sidebar.button("Add Task"):
    # We will use Streamlit Session State to store tasks later
    st.write(f"Task {name} added!")

# --- MAIN AREA: VISUALIZATION ---
st.subheader("Gantt Chart")

# Run the dummy simulation
if st.button("Run Simulation"):
    # 1. Get results from the scheduler
    results = run_scheduler([], algorithm) 
    
    # 2. Convert to DataFrame for Plotly
    df = pd.DataFrame(results)
    
    # 3. Draw the chart
    fig = px.timeline(
        df, 
        x_start="Start", 
        x_end="Finish", 
        y="Task", 
        color="Status",
        title=f"Schedule using {algorithm}"
    )
    
    # Update layout to show the whole timeline clearly
    fig.update_yaxes(autorange="reversed") # T1 at top
    fig.layout.xaxis.type = 'linear' 
    st.plotly_chart(fig, use_container_width=True)

def _lcm(a, b):
    """
    Helper function to calculate LCM of two numbers.
    Formula: (a * b) // gcd(a, b)
    """
    return abs(a * b) // math.gcd(a, b)

def calculate_hyperperiod(tasks):
    """
    Calculates the Hyperperiod (LCM of all task periods).
    If no tasks are present, returns a default value (e.g., 10).
    """
    if not tasks:
        return 20 # Default simulation time if list is empty

    # Extract all periods from the task list
    periods = [task.period for task in tasks]
    
    # Calculate LCM over the list of periods
    # reduce() applies the _lcm function cumulatively to the items
    hyperperiod = reduce(_lcm, periods)
    
    return hyperperiod

def run_scheduler(tasks, algorithm):
    """
    Main engine. 
    1. Calculates simulation duration (Hyperperiod).
    2. Runs the simulation loop (To be implemented next).
    """
    
    # 1. Determine how long to run
    simulation_limit = calculate_hyperperiod(tasks)
    
    # Debug print to check if logic works (check your terminal when you run it)
    print(f"Calculated Hyperperiod: {simulation_limit}")

    # --- TEMP: Return dummy data just to show the timeline length ---
    # We will delete this part when we write the real loop next.
    timeline_data = []
    
    # Create a dummy 'Idle' block just to stretch the chart to the limit
    timeline_data.append(
        dict(Task="System", Start=0, Finish=simulation_limit, Status="Simulation Scope")
    )
    
    return timeline_data    
