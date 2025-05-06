import streamlit as st
import pandas as pd

# Setup
st.set_page_config(
   page_title="WILL-E",
   page_icon="😑",
)

# HEADER
st.title("WILL-E")
st.subheader("Kelola iklan tv mu bersama William Analis")
st.divider()

# Initialize DataFrame (resets on refresh)
df = pd.DataFrame(columns=["Program", "Nett/Spot", "TV Rating", "Prime Time", "PIB"])

# Use session state to hold the input data for the current session
if "df_data" not in st.session_state:
    st.session_state.df_data = df

# Display the current data table
st.subheader("Data Iklan")
st.dataframe(st.session_state.df_data, use_container_width=True)

# Form for entering ad data
with st.expander("Input Program"):
    program = st.text_input("Program")
    nett_spot = st.number_input("Nett/Spot", min_value=0, step=1)
    tv_rating = st.number_input("TV Rating", min_value=0.0, step=0.1)
    prime_time = st.checkbox("Prime Time?")
    pib = st.checkbox("PIB?")
    
    if st.button("Simpan"):
        new_row = pd.DataFrame([{
            "Program": program,
            "Nett/Spot": nett_spot,
            "TV Rating": tv_rating,
            "Prime Time": prime_time,
            "PIB": pib
        }])
        st.session_state.df_data = pd.concat([st.session_state.df_data, new_row], ignore_index=True)
        st.rerun()  # Refresh the app to update the table

st.divider()

st.subheader("Penempatan Iklan")

# Form for entering optimization parameters
with st.expander("Syarat Penempatan Iklan"):
    budget = st.number_input("Budget", min_value=0, value=0, step=1000000, format="%d")
    ptCap = st.number_input("Minimal Prime Time (desimal)", min_value=0.0, max_value=1.0,
                            value=0.0, step=0.01, format="%.2f")
    pibCap = st.number_input("Minimal PIB (desimal)", min_value=0.0, max_value=1.0,
                             value=0.00, step=0.01, format="%.2f")
st.write(' ')
if st.button("Run Solver"):
    if st.session_state.df_data.empty:
        st.error("Data Iklan kosong. Silakan masukkan data iklan terlebih dahulu.")
    else:
        from ortools.linear_solver import pywraplp
        
        # Create the solver using CBC
        solver = pywraplp.Solver.CreateSolver('CBC')
        
        # Get the number of programs
        n = len(st.session_state.df_data)
        # Create decision variables (one per program)
        x = [solver.IntVar(0, solver.infinity(), f'x{i}') for i in range(n)]
        
        # Retrieve parameter lists from the DataFrame.
        # Convert boolean flags into integers (1 if True; 0 if False).
        nett_list = st.session_state.df_data["Nett/Spot"].tolist()
        tvr_list = st.session_state.df_data["TV Rating"].tolist()
        pt_list = st.session_state.df_data["Prime Time"].apply(lambda flag: 1 if flag else 0).tolist()
        pib_list = st.session_state.df_data["PIB"].apply(lambda flag: 1 if flag else 0).tolist()
        
        # Objective: Maximize total GRP = sum(TV Rating × spots)
        solver.Maximize(solver.Sum(tvr_list[i] * x[i] for i in range(n)))
        
        # Budget Constraint: Total cost must be within the budget
        solver.Add(solver.Sum(nett_list[i] * x[i] for i in range(n)) <= budget)
        
        # Define expressions for total GRP, prime time GRP, and PIB GRP
        totGRP_expr = solver.Sum(tvr_list[i] * x[i] for i in range(n))
        ptGRP_expr  = solver.Sum(pt_list[i] * tvr_list[i] * x[i] for i in range(n))
        pibGRP_expr = solver.Sum(pib_list[i] * tvr_list[i] * x[i] for i in range(n))
        
        # Constraints: ensure prime time GRP and PIB GRP ratios meet their caps
        solver.Add(ptGRP_expr >= ptCap * totGRP_expr)
        solver.Add(pibGRP_expr >= pibCap * totGRP_expr)
        
        status = solver.Solve()
        
        if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            # Retrieve decision variable solutions for each program (number of spots)
            solution_spots = [x[i].solution_value() for i in range(n)]
 
            # Build per-program results: Cost and GRP for each row.
            cost_list = [nett_list[i] * solution_spots[i] for i in range(n)]
            grp_list  = [tvr_list[i] * solution_spots[i] for i in range(n)]
            
            # Compute overall totals.
            total_cost = sum(cost_list)
            total_grp  = sum(grp_list)
            pt_total   = sum(pt_list[i] * tvr_list[i] * solution_spots[i] for i in range(n))
            pib_total  = sum(pib_list[i] * tvr_list[i] * solution_spots[i] for i in range(n))
            
            # Round total GRP to two decimals.
            total_grp = round(total_grp, 2)
            
            # Compute overall percentages (in % form)
            pt_percent  = (pt_total / total_grp * 100) if total_grp != 0 else 0
            pib_percent = (pib_total / total_grp * 100) if total_grp != 0 else 0
            
            # Round the percentages to 2 decimal places.
            pt_percent = round(pt_percent, 2)
            pib_percent = round(pib_percent, 2)
            
            # Create formatted percentage strings with the '%' symbol.
            pt_percent_str  = f"{pt_percent:.2f}%"
            pib_percent_str = f"{pib_percent:.2f}%"
            
            # Update the results DataFrame with program-level columns.
            result_df = st.session_state.df_data.copy()
            result_df["Spot"] = solution_spots
            result_df["Cost"] = cost_list
            result_df["GRP"]  = grp_list
            
            st.subheader("Solver Results")
            st.dataframe(result_df, use_container_width=True)
            
            # Create a summary DataFrame with overall metrics.
            summary_data = {
                "Metrik": ["Total Cost", "Total GRP", "Prime Time %", "PIB %"],
                "Nilai": [f"{int(total_cost):,}", f"{total_grp:,.2f}", pt_percent_str, pib_percent_str]
            }
            summary_df = pd.DataFrame(summary_data)
            
            st.subheader("Metrik")
            st.dataframe(summary_df, hide_index=True, use_container_width=True)
        else:
            st.error("Solver did not find an optimal solution.")
