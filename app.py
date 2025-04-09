import io
import streamlit as st
import pandas as pd
import altair as alt

st.title("Grid Expansion Impact Calculator")
st.markdown(
    """
    This application allows you to define a grid expansion plan and calculate its environmental impact.
    You can either input data manually or upload a CSV file. The application will compute the CO₂ impact based on the defined multipliers.
    """
)

if "calculated_df" not in st.session_state:
    st.session_state.calculated_df = None

with st.container(border=True):
    st.markdown("### Expansion Plan Definition")
    
    # Dummy CSV data as default input
    dummy_csv = """
    year,component_type,component_subtype,unit_count
    2020,cable,underground,65
    2020,cable,overhead,50
    2020,transformer,step-up,30
    2020,transformer,step-down,25
    2020,substation,,23
    2025,cable,underground,35
    2025,cable,overhead,40
    2025,transformer,step-up,12
    2025,transformer,step-down,6
    2025,substation,,4
    2030,cable,underground,21
    2030,cable,overhead,50
    2030,transformer,step-up,14
    2030,transformer,step-down,7
    2030,substation,,5
    2035,cable,underground,20
    2035,cable,overhead,60
    2035,transformer,step-up,8
    2035,transformer,step-down,8
    2035,substation,,6
    2040,cable,underground,28
    2040,cable,overhead,70
    2040,transformer,step-up,12
    2040,transformer,step-down,9
    2040,substation,,7
    """

    # Create tabs for manual input and CSV upload
    tab1, tab2 = st.tabs(["Manual Input", "CSV Upload"])

    with tab1:
        df = st.data_editor(
            pd.read_csv(io.StringIO(dummy_csv.strip())),
            num_rows="dynamic",
            use_container_width=True,
        )

    with tab2:
        uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write("Data preview:", df.head())

    st.markdown("### Calculation Setup")
    
    impact_category_units = {
        "Climate Change": "kg CO₂-eq",
        "Acidification": "mol H⁺-eq",
        "Ecotoxicity: Freshwater": "CTUe",
        "Energy Resources: Non-Renewable": "MJ",
        "Eutrophication: Freshwater": "kg P-eq",
        "Eutrophication: Marine": "kg N-eq",
        "Eutrophication: Terrestrial": "mol N-eq",
        "Human Toxicity: Carcinogenic": "CTUh",
        "Human Toxicity: Non-Carcinogenic": "CTUh",
        "Ionising Radiation: Human Health": "kBq U235-eq",
        "Land Use": "-",
        "Material Resources: Metals/Minerals": "kg Sb-eq",
        "Ozone Depletion": "kg CFC-11-eq",
        "Particulate Matter Formation": "[-]",
        "Photochemical Oxidant Formation: Human Health": "kg NMVOC-eq",
        "Water Use": "m³"
    }
    
    setup_col1, setup_col2 = st.columns([1, 1])
    with setup_col1:
        impact_category = st.selectbox(
            "Impact Category",
            options=impact_category_units.keys(),
        )
    with setup_col2:
        scenario = st.selectbox(
            "Scenario",
            options=["1.5 °C", "2 °C", "3.5 °C"],
        )
    
    calculated_df = st.session_state.calculated_df
    # Define carbon multipliers (tons CO₂ per unit)
    co2_factors = {
        ("cable", "underground"): 3.12,
        ("cable", "overhead"): 2.08,
        ("transformer", "step-up"): 2.5,
        ("transformer", "step-down"): 1.5,
        ("substation", "unspecified"): 5,
    }
    if "component_subtype" in df.columns:
        df["component_subtype"] = df["component_subtype"].fillna("unspecified")
    else:
        df["component_subtype"] = "unspecified"
        
    df["component"] = df["component_subtype"] + " " + df["component_type"]
    if st.button("Calculate Impact", type="primary", use_container_width=True):
        st.toast("Calculating impacts...", icon="🧮")
        df["CO2"] = df.apply(
            lambda row: row["unit_count"]
            * co2_factors.get((row["component_type"], row["component_subtype"]), 0),
            axis=1,
        )
        df["component"] = df["component_subtype"] + " " + df["component_type"]
        df["component"] = df["component"].str.strip()
        st.session_state.calculated_df = df
        calculated_df = df
        st.toast("Calculation complete!", icon="✅")
            
if calculated_df is not None:
    with st.container(border=True):
        st.markdown("### Results")
        
        default_colors = [
            "#00549F",
            "#F6A800",
            "#57AB27",
            "#CC071E",
            "#7A6FAC",
            "#0098A1",
            "#BDCD00",
            "#006165",
        ]

        components = df["component"].unique().tolist()
        color_map = {
            comp: default_colors[i % len(default_colors)] for i, comp in enumerate(components)
        }
        all_groups = calculated_df["component_type"].unique().tolist()
        selected_group = st.segmented_control(
            "Filter by component group", options=["All"] + all_groups, default="All"
        )
        cumulative = st.checkbox("Cumulative", key="cumulative_all")
        df_filtered = (
            calculated_df if selected_group == "All" else calculated_df[calculated_df["component_type"] == selected_group]
        )
        df_grouped = df_filtered.groupby(["year", "component"], as_index=False)["CO2"].sum()
        df_pivot = df_grouped.pivot(index="year", columns="component", values="CO2").fillna(
            0
        )
        if cumulative:
            df_pivot = df_pivot.cumsum()
        df_long = df_pivot.reset_index().melt(
            id_vars="year", var_name="component", value_name="CO2"
        )
        chart = (
            alt.Chart(df_long)
            .mark_bar()
            .encode(
                x=alt.X("year:O", title=None),
                y=alt.Y("CO2:Q", title=f"{impact_category} Impact ({impact_category_units[impact_category]})"),
                color=alt.Color(
                    "component:N",
                    scale=alt.Scale(
                        domain=list(color_map.keys()), range=list(color_map.values())
                    ),
                ),
                tooltip=["year", "component", "CO2"],
            )
            .properties(height=600)
            .configure_axisX(labelAngle=0)
            .configure_legend(orient="bottom", columns=3, labelLimit=200)
        )
        st.altair_chart(chart, use_container_width=True)
