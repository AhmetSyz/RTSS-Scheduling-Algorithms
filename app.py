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
    server_mode = st.selectbox("Aperiodic Handling", ["None", "Background", "Deferrable Server"," Polling Server"])
    
    s_cap = 0
    s_period = 0
    if server_mode == "Deferrable Server":
        col1, col2 = st.columns(2)
        s_cap = col1.number_input("Server Budget (Cs)", 1, 10, 2)
        s_period = col2.number_input("Server Period (Ts)", 2, 20, 5)
# ... (Keep your existing System and Server Config code above this) ...

    st.divider()
    st.header("3. Data Import")
    
    # 1. Template Download (Helps the user know the format)
    # We create a sample CSV structure for the user to download
    sample_csv = """Type,Name,Cost,Period,Arrival,Deadline
                    Periodic,T1,2,10,0,10
                    Periodic,T2,3,15,0,15
                    Aperiodic,J1,1,0,4,0"""
                        
    st.download_button(
        label="📥 Download CSV Template",
        data=sample_csv,
        file_name="task_template.csv",
        mime="text/csv"
    )

    # 2. File Uploader
    uploaded_file = st.file_uploader("Upload Task CSV", type=["csv", "txt"])

    if uploaded_file is not None:
        try:
            # Read the file
            df_upload = pd.read_csv(uploaded_file)
            
            # Normalize column names (strip whitespace and lower case for safety)
            df_upload.columns = df_upload.columns.str.strip().str.lower()
            
            # Required columns
            required_cols = {'type', 'name', 'cost', 'period', 'arrival', 'deadline'}
            
            if not required_cols.issubset(df_upload.columns):
                st.error(f"CSV missing columns. Required: {required_cols}")
            else:
                if st.button("🚨 Overwrite & Load Tasks"):
                    # Clear existing lists
                    st.session_state.periodic_list = []
                    st.session_state.aperiodic_list = []
                    
                    # Iterate and Add
                    count_p = 0
                    count_a = 0
                    
                    for _, row in df_upload.iterrows():
                        # Handle missing values safely using fillna logic or 0 defaults
                        r_type = str(row['type']).strip().title() # Ensures "periodic" becomes "Periodic"
                        r_name = str(row['name'])
                        r_cost = int(row['cost'])
                        r_period = int(row['period']) if not pd.isna(row['period']) else 0
                        r_arrival = int(row['arrival']) if not pd.isna(row['arrival']) else 0
                        r_deadline = int(row['deadline']) if not pd.isna(row['deadline']) else 0
                        
                        new_task = Task(
                            name=r_name,
                            task_type=r_type,
                            cost=r_cost,
                            period=r_period,
                            deadline=r_deadline,
                            arrival=r_arrival
                        )
                        
                        if r_type == "Periodic":
                            st.session_state.periodic_list.append(new_task)
                            count_p += 1
                        else:
                            st.session_state.aperiodic_list.append(new_task)
                            count_a += 1
                            
                    st.success(f"Loaded {count_p} Periodic and {count_a} Aperiodic tasks!")
                    st.rerun() # Refresh page to show data in tables
                    
        except Exception as e:
            st.error(f"Error parsing file: {e}")
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

# --- 5. RUN SIMULATION ---
st.divider()
if st.button("🚀 RUN SIMULATION", type="primary", use_container_width=True):
    
    # 1. EXECUTE SCHEDULER
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
        df['Duration'] = df['Finish'] - df['Start']
        max_time = df["Finish"].max()
        
        # --- 2. DATA PREPARATION ---
        
        # PART A: THE TOP ROWS (PLANNED ARRIVALS)
        # We generate this from INPUTS, not results. This ensures J1 appears.
        planned_data = []
        
        # 1. Generate Periodic Arrivals
        for p_task in st.session_state.periodic_list:
            t = p_task.arrival_time
            while t < max_time:
                planned_data.append({
                    "Task": p_task.name,
                    "Start": t,
                    "Finish": t + p_task.cost, # Visualize the Workload Size
                    "Duration": p_task.cost,
                    "Status": "Arrival",       # Mark as Arrival
                    "Row": p_task.name         # Put on its own row
                })
                t += p_task.period
                
        # 2. Generate Aperiodic Arrivals (Fixes J1 invisibility)
        for a_task in st.session_state.aperiodic_list:
            if a_task.arrival_time <= max_time:
                planned_data.append({
                    "Task": a_task.name,
                    "Start": a_task.arrival_time,
                    "Finish": a_task.arrival_time + a_task.cost,
                    "Duration": a_task.cost,
                    "Status": "Arrival",
                    "Row": a_task.name
                })
        
        planned_df = pd.DataFrame(planned_data)

        # PART B: THE BOTTOM ROW (ACTUAL CPU EXECUTION)
        # We keep your existing correct CPU logic
        cpu_summary_df = df.copy()
        cpu_summary_df["Row"] = " TOTAL CPU" 
        # We filter out IDLE for the CPU row to keep it clean, or keep it if you prefer
        # cpu_summary_df = cpu_summary_df[cpu_summary_df["Task"] != "IDLE"] 
        
        # PART C: COMBINE
        # We might have column mismatches, so we ensure we only concat relevant cols
        common_cols = ["Task", "Start", "Finish", "Duration", "Row", "Status"]
        final_df = pd.concat([planned_df[common_cols], cpu_summary_df[common_cols]], ignore_index=True)
        
        # --- 3. COLORS ---
        # Define colors so "T1 Arrival" matches "T1 Execution"
        unique_tasks = [t for t in final_df["Task"].unique() if t not in ["IDLE", " TOTAL CPU"]]
        colors = px.colors.qualitative.Plotly
        color_map = {"IDLE": "#E0E0E0"}
        
        for i, task in enumerate(unique_tasks):
            # Both the task itself and its arrival block get the same color
            color_map[task] = colors[i % len(colors)]
        
        # --- 4. MASTER CHART ---
        st.subheader("Master Schedule View")
        
        # Dynamic Height
        unique_rows = [r for r in final_df["Row"].unique() if r != " TOTAL CPU"]
        
        fig = px.bar(
            final_df, 
            x="Duration", 
            y="Row", 
            base="Start",
            color="Task", 
            text="Task", 
            orientation='h',
            color_discrete_map=color_map,
            height=150 + (50 * len(unique_rows)),
            # Use distinct opacity to distinguish "Plan" from "Action" if desired, 
            # but standard solid bars are clearest for "Arrival"
            opacity=0.9 
        )
        
        # --- 5. LAYOUT AND ORDERING ---
        preferred_order = sorted(unique_rows) + [" TOTAL CPU"]
        
        fig.update_layout(
            xaxis_title="Time (Ticks)", 
            yaxis_title="",
            showlegend=True, 
            bargap=0.4,
            yaxis={'categoryorder': 'array', 'categoryarray': preferred_order}
        )
        
        fig.update_xaxes(type='linear', dtick=1, showgrid=True, gridwidth=1, gridcolor='LightGrey')
        fig.update_yaxes(autorange="reversed")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- 6. LOGS ---
        st.divider()
        st.subheader("📋 Detailed Queue Log")
        queue_df = pd.DataFrame(queue_log)
        cols = ["Time"] + [f"CPU {i+1}" for i in range(num_cpus)] + ["Waiting Queue"]
        final_cols = [c for c in cols if c in queue_df.columns]
        st.dataframe(queue_df[final_cols], use_container_width=True, hide_index=True)

        # --- 7. BUDGET ---
        if server_mode in ["Deferrable Server", "Polling Server"]:
            st.divider()
            st.subheader("🔋 Server Budget Monitor")
            fig_budget = px.line(
                queue_df, x="Time", y="Server Budget", 
                title=f"{server_mode} Budget (Cap={s_cap})",
                line_shape="hv", markers=True
            )
            t_replenish = 0
            while t_replenish <= max_time:
                fig_budget.add_vline(x=t_replenish, line_width=1, line_dash="dash", line_color="green")
                t_replenish += s_period
            fig_budget.update_layout(yaxis_range=[-0.5, s_cap + 0.5], showlegend=False, height=300)
            fig_budget.update_xaxes(type='linear', dtick=1)
            st.plotly_chart(fig_budget, use_container_width=True)