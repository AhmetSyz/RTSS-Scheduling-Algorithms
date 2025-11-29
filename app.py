import streamlit as st
import pandas as pd
import plotly.express as px
from scheduler import run_scheduler, Task

# 1. SETUP PAGE
st.set_page_config(page_title="RTOS Simulator", layout="wide")

# Initialize Session State
if 'task_list' not in st.session_state:
    st.session_state.task_list = []

st.title("⚡ Real-Time Scheduling Simulator")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("⚙️ Configuration")
    algorithm = st.selectbox("Scheduling Algorithm", ["Rate Monotonic", "EDF"])
    
    st.divider()
    st.subheader("Add Task")
    col1, col2 = st.columns(2)
    t_name = col1.text_input("Name", f"T{len(st.session_state.task_list)+1}")
    t_cost = col2.number_input("Cost (C)", min_value=1, value=1)
    t_period = col1.number_input("Period (T)", min_value=1, value=4)
    t_deadline = col2.number_input("Deadline (D)", min_value=1, value=4)
    
    if st.button("➕ Add Task", use_container_width=True):
        st.session_state.task_list.append(Task(t_name, 0, t_cost, t_period, t_deadline))
        st.success(f"Added {t_name}")

    # Task List Display
    if st.session_state.task_list:
        st.divider()
        st.write("### Current Tasks")
        for i, t in enumerate(st.session_state.task_list):
            st.info(f"**{t.name}**: C={t.cost}, T={t.period}, D={t.deadline}")
        
        if st.button("Clear All Tasks", type="primary"):
            st.session_state.task_list = []
            st.rerun()

# --- HELPER: UTILIZATION CALC ---
def calculate_utilization(tasks):
    u = sum([t.cost / t.period for t in tasks])
    return u

# --- MAIN PAGE: SIMULATION ---
if st.button("🚀 RUN SIMULATION", type="primary", use_container_width=True):
    if not st.session_state.task_list:
        st.warning("Please add at least one task to the sidebar.")
    else:
        # 1. Run Logic
        tasks = st.session_state.task_list
        results = run_scheduler(tasks, algorithm)
        df = pd.DataFrame(results)
        
        # 2. ANALYSIS SECTION (The "Is it Schedulable?" part)
        st.divider()
        st.subheader("📊 Analysis Report")
        
        col1, col2, col3 = st.columns(3)
        
        # Metric A: CPU Utilization
        utilization = calculate_utilization(tasks)
        col1.metric("CPU Utilization (U)", f"{utilization:.2%}")
        
        # Metric B: Theoretical Check
        is_schedulable_theory = False
        n = len(tasks)
        if algorithm == "Rate Monotonic":
            # Liu & Layland Bound: n(2^(1/n) - 1)
            ll_bound = n * (2**(1/n) - 1)
            col2.metric("RM Bound (Liu & Layland)", f"{ll_bound:.2%}")
            if utilization <= ll_bound:
                is_schedulable_theory = True
                col2.success(" theoretically schedulable")
            else:
                col2.warning("Bound exceeded (Simulate to check)")
        elif algorithm == "EDF":
            col2.metric("EDF Bound", "100%")
            if utilization <= 1.0:
                is_schedulable_theory = True
                col2.success("Condition Met (U ≤ 1)")
            else:
                col2.error("Overloaded (U > 1)")

        # Metric C: Actual Simulation Result
        missed_deadlines = df[df['Status'] == 'Missed']
        if not missed_deadlines.empty:
            col3.error(f"❌ DEADLINE MISSED!")
            st.error(f"Simulation failed! Task(s) {missed_deadlines['Task'].unique()} missed a deadline.")
        else:
            col3.success("✅ SCHEDULE SUCCESSFUL")

        # 3. GANTT CHART (The "Visuals" part)
        st.subheader("📅 Schedule Timeline")
        
        if not df.empty:
            # Create Chart
            fig = px.timeline(
                df, 
                x_start="Start", 
                x_end="Finish", 
                y="Task", 
                color="Status",
                # Specific colors: Green for Run, Red for Miss, Grey for Idle
                color_discrete_map={
                    "Running": "#4CAF50", 
                    "Idle": "#D3D3D3", 
                    "Missed": "#FF5252"
                },
                hover_data=["Start", "Finish", "Status"]
            )
            
            # --- CRITICAL FIX FOR X-AXIS ---
            # This forces the chart to show numbers 0, 1, 2, 3...
            max_time = df['Finish'].max()
            fig.update_layout(
                xaxis=dict(
                    title="Time (Ticks)",
                    tickmode='linear', # Force linear steps
                    dtick=1,           # Step size of 1
                    range=[0, max_time],
                    showgrid=True
                ),
                yaxis=dict(title="Tasks", autorange="reversed"), # Top task is T1
                height=300,
                bargap=0.2
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 4. STEP-BY-STEP LOG
            with st.expander("Show Detailed Execution Log"):
                st.write("This table shows exactly which task occupied the CPU at each step.")
                st.dataframe(df, use_container_width=True)