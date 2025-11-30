import streamlit as st
import pandas as pd
import plotly.express as px
from scheduler import run_scheduler, Task

st.set_page_config(page_title="RTOS Simulator Pro", layout="wide")

# Session State Init
if 'periodic_list' not in st.session_state: st.session_state.periodic_list = []
if 'aperiodic_list' not in st.session_state: st.session_state.aperiodic_list = []

st.title("⚡ Advanced RTOS Simulator")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("1. System Config")
    num_cpus = st.slider("Number of Processors", 1, 4, 1)
    # --- Algorithm Selection ---
    algorithm = st.selectbox("Algorithm", [
        "Rate Monotonic", 
        "Deadline Monotonic", 
        "EDF", 
        "Least Laxity First"
    ])
    
    st.divider()
    st.header("2. Server Config")
    server_mode = st.selectbox("Aperiodic Handling", ["None", "Background", "Deferrable Server"])
    
    s_cap = 0
    s_period = 0
    if server_mode == "Deferrable Server":
        col1, col2 = st.columns(2)
        s_cap = col1.number_input("Server Budget (Cs)", 1, 10, 2)
        s_period = col2.number_input("Server Period (Ts)", 2, 20, 5)

# --- MAIN INPUT AREA (TABS) ---
tab1, tab2 = st.tabs(["🔄 Periodic Tasks", "⚡ Aperiodic Tasks"])

with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    p_name = c1.text_input("Task Name", f"T{len(st.session_state.periodic_list)+1}")
    p_cost = c2.number_input("Exec Time (C)", 1, 20, 1, key="pc")
    p_period = c3.number_input("Period (T)", 2, 50, 5, key="pp")
    
    # Optional Inputs
    use_custom_r = c4.checkbox("Release Time?", value=False)
    p_release = c4.number_input("Release (r)", 0, 50, 0, disabled=not use_custom_r, key="pr")
    
    use_custom_d = c5.checkbox("Deadline?", value=False)
    p_deadline = c5.number_input("Deadline (D)", 1, 50, 5, disabled=not use_custom_d, key="pd")
    
    if st.button("Add Periodic Task"):
        # Handle defaults
        final_deadline = p_deadline if use_custom_d else 0 # 0 tells scheduler to use Period
        final_release = p_release if use_custom_r else 0
        
        # CORRECTED CALL
        new_task = Task(
            name=p_name, 
            task_type="Periodic", 
            cost=p_cost, 
            period=p_period, 
            deadline=final_deadline, 
            arrival=final_release
        )
        st.session_state.periodic_list.append(new_task)
        st.success(f"Added {p_name}")

    if st.session_state.periodic_list:
        st.write("---")
        # Display as a clean table
        display_data = []
        for t in st.session_state.periodic_list:
            display_data.append({
                "Name": t.name, "Cost": t.cost, "Period": t.period, 
                "Release": t.arrival_time, "Deadline": t.deadline if t.deadline > 0 else t.period
            })
        st.dataframe(display_data)
        
        if st.button("Clear Periodic"):
            st.session_state.periodic_list = []
            st.rerun()

with tab2:
    c1, c2, c3 = st.columns(3)
    a_name = c1.text_input("Job Name", f"J{len(st.session_state.aperiodic_list)+1}")
    a_arrival = c2.number_input("Arrival Time (r)", 0, 50, 2)
    a_cost = c3.number_input("Exec Time (C)", 1, 10, 1, key="ac")
    
    if st.button("Add Aperiodic Job"):
        # CORRECTED CALL
        new_job = Task(
            name=a_name, 
            task_type="Aperiodic", 
            cost=a_cost, 
            period=0, 
            deadline=0, 
            arrival=a_arrival
        )
        st.session_state.aperiodic_list.append(new_job)
        st.success(f"Added {a_name}")

    if st.session_state.aperiodic_list:
        st.write("---")
        display_data_ap = []
        for t in st.session_state.aperiodic_list:
            display_data_ap.append({"Name": t.name, "Arrival": t.arrival_time, "Cost": t.cost})
        st.dataframe(display_data_ap)
        
        if st.button("Clear Aperiodic"):
            st.session_state.aperiodic_list = []
            st.rerun()

# --- SIMULATION TRIGGER ---
st.divider()
# app.py (Replace the bottom "if st.button..." block)

# app.py (Bottom Section)

if st.button("🚀 RUN SIMULATION", type="primary", use_container_width=True):
    
    results, queue_log = run_scheduler(
        st.session_state.periodic_list,
        st.session_state.aperiodic_list,
        algorithm,
        num_cpus,
        server_mode,
        s_cap,
        s_period
    )
    
    if results:
        df = pd.DataFrame(results)
        
        # --- CHART FIX: Use px.bar instead of px.timeline ---
        st.subheader("Gantt Chart")
        
        # 1. Calculate Duration (Required for px.bar)
        df['Duration'] = df['Finish'] - df['Start']
        
        color_map = {
            "Running": "#4CAF50",   # Green
            "Idle": "#EEEEEE",      # Light Grey
            "Missed": "#FF5252",    # Red
            "Server Exec": "#2196F3", # Blue
            "Background": "#9C27B0"   # Purple
        }
        
        # 2. Draw using Horizontal Bar Chart
        fig = px.bar(
            df, 
            x="Duration", 
            y="CPU",          # Puts the bar on the correct CPU row
            base="Start",     # Tells Plotly where to start the bar
            color="Status", 
            text="Task",      # Show Task Name inside the bar
            facet_row="CPU",  # Splits the chart into rows (CPU 1, CPU 2)
            orientation='h',  # Horizontal
            color_discrete_map=color_map,
            height=200 * num_cpus if num_cpus > 1 else 300
        )
        
        # 3. Clean up Layout
        fig.update_layout(
            xaxis_title="Time (Ticks)",
            yaxis_title="",
            showlegend=True,
            bargap=0.1 # Make bars thicker
        )
        
        # Force X-axis to show every single integer tick
        fig.update_xaxes(type='linear', dtick=1)
        
        # Ensure Y-axes across all facets share the same category order
        fig.update_yaxes(matches=None, showticklabels=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- LOG TABLE ---
        st.divider()
        st.subheader("📋 Step-by-Step Queue Log")
        
        queue_df = pd.DataFrame(queue_log)
        
        # Reorder columns to ensure Time is first, then CPUs, then Queue
        cols = ["Time"] + [f"CPU {i+1}" for i in range(num_cpus)] + ["Waiting Queue"]
        # Filter to make sure we only grab columns that actually exist
        final_cols = [c for c in cols if c in queue_df.columns]
        
        st.dataframe(
            queue_df[final_cols], 
            use_container_width=True,
            hide_index=True
        )