
# ============================================================
# STREAMLIT APPLICATION: SALES DASHBOARD
# Complete Sales Data Analysis
# Dataset: sales.csv
# File: Tableau.py
# ============================================================

# ============================================================
# DEPENDENCY CHECK
# ============================================================
import sys

REQUIRED = {
    "streamlit": "streamlit",
    "pandas": "pandas",
    "numpy": "numpy",
    "plotly": "plotly",
}

missing = []

for module, pip_name in REQUIRED.items():
    try:
        __import__(module)
    except ImportError:
        missing.append(pip_name)

if missing:
    print("Missing modules:", ", ".join(missing))
    print("\nInstall them using:")
    print(f"pip install {' '.join(missing)}")
    sys.exit(1)

# ============================================================
# IMPORTS
# ============================================================
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# DATA LOADING
# ============================================================
@st.cache_data
def load_data(uploaded_file=None):

    """Load sales.csv from available locations."""

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        os.path.join(BASE_DIR, "sales.csv"),
        os.path.join(BASE_DIR, "data", "sales.csv"),
        os.path.join(BASE_DIR, "project", "sales.csv"),
        os.path.join(os.getcwd(), "sales.csv"),
        "sales.csv",
    ]

    csv_path = next(
        (c for c in candidates if os.path.exists(c)),
        None
    )

    if uploaded_file is not None:
        source = uploaded_file

    elif csv_path is not None:
        source = csv_path
        st.sidebar.success(
            f"Data loaded: {os.path.basename(csv_path)}"
        )

    else:
        st.error("Sales.csv file not found.")

        st.markdown("**Locations searched:**")

        for c in candidates:
            st.code(c, language="text")

        st.info(
            "Solutions:\n\n"
            "1. Place sales.csv in the same folder as Tableau.py.\n"
            "2. Or upload your CSV file below."
        )

        uploaded = st.file_uploader(
            "Upload sales.csv manually",
            type=["csv"]
        )

        if uploaded is None:
            st.stop()

        source = uploaded

    df = pd.read_csv(
        source,
        index_col=0,
        parse_dates=["Date"]
    )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce")

    df = df.dropna(subset=["Date", "Sales"])

    df = df.sort_values("Date").reset_index(drop=True)

    if df.empty:
        st.error("The dataset contains no valid observations.")
        st.stop()

    # Derived variables
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Month_Name"] = df["Date"].dt.strftime("%b")
    df["Day_of_Week"] = df["Date"].dt.day_name()
    df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
    df["Quarter"] = df["Date"].dt.quarter
    df["Day"] = df["Date"].dt.day

    return df


# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>

    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 1rem;
    }

    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        text-align: center;
        margin-bottom: 1rem;
    }

    .kpi-card h3 {
        margin: 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }

    .kpi-card h2 {
        margin: 0.5rem 0 0 0;
        font-size: 1.8rem;
    }

    .kpi-card p {
        margin: 0.3rem 0 0 0;
        font-size: 0.85rem;
        opacity: 0.8;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA LOADING
# ============================================================
uploaded_file = st.sidebar.file_uploader(
    "Upload sales.csv",
    type=["csv"]
)

df = load_data(uploaded_file)


# ============================================================
# SIDEBAR - FILTERS
# ============================================================
st.sidebar.title("🎛️ Filters")
st.sidebar.markdown("---")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "📅 Analysis Period",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

st.sidebar.markdown("---")

st.sidebar.subheader("🗓️ Aggregation Granularity")

granularity = st.sidebar.selectbox(
    "Aggregate by",
    ["Daily", "Weekly", "Monthly", "Quarterly"],
    index=2
)

st.sidebar.markdown("---")

st.sidebar.subheader("📌 Display Options")

show_ma = st.sidebar.checkbox(
    "Show Moving Average (7 periods)",
    value=True
)

show_trend = st.sidebar.checkbox(
    "Show Trend Line",
    value=False
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "💡 Dashboard developed with Streamlit"
)


# ============================================================
# DATA FILTERING
# ============================================================
mask = (
    (df["Date"].dt.date >= start_date)
    & (df["Date"].dt.date <= end_date)
)

df_f = df.loc[mask].copy()

if df_f.empty:
    st.warning("No data available for the selected period.")
    st.stop()


# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def aggregate(df_in, gran):

    if gran == "Daily":

        return (
            df_in.groupby(df_in["Date"].dt.date)["Sales"]
            .sum()
            .reset_index()
            .rename(columns={"Date": "Period"})
        )

    elif gran == "Weekly":

        tmp = df_in.copy()

        tmp["Period"] = (
            tmp["Date"].dt.to_period("W").dt.start_time
        )

        return tmp.groupby("Period")["Sales"].sum().reset_index()

    elif gran == "Monthly":

        tmp = df_in.copy()

        tmp["Period"] = (
            tmp["Date"].dt.to_period("M").dt.to_timestamp()
        )

        return tmp.groupby("Period")["Sales"].sum().reset_index()

    else:

        tmp = df_in.copy()

        tmp["Period"] = (
            tmp["Date"].dt.to_period("Q").dt.to_timestamp()
        )

        return tmp.groupby("Period")["Sales"].sum().reset_index()


def kpi_card(title, value, delta=None, icon="📈"):

    arrow = "▲" if (delta is not None and delta >= 0) else "▼"

    delta_color = (
        "#d4edda"
        if (delta is not None and delta >= 0)
        else "#f8d7da"
    )

    delta_html = ""

    if delta is not None:

        delta_html = (
            f"<p style='color:{delta_color}; font-weight:bold; margin:0.3rem 0 0 0;'>"
            f"{arrow} {abs(delta):.2f}%</p>"
        )

    st.markdown(f"""
    <div class="kpi-card">
        <h3>{icon} {title}</h3>
        <h2>{value}</h2>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# DASHBOARD HEADER
# ============================================================
st.markdown(
    '<div class="main-header">📊 Sales Dashboard — Complete Analysis</div>',
    unsafe_allow_html=True
)

st.caption(
    f"Analysis Period: **{start_date}** → **{end_date}** | "
    f"Number of Observations: **{len(df_f):,}**"
)

st.markdown("---")


# ============================================================
# KPI CALCULATIONS
# ============================================================
total_sales = df_f["Sales"].sum()
avg_sales = df_f["Sales"].mean()
max_sales = df_f["Sales"].max()
min_sales = df_f["Sales"].min()
std_sales = df_f["Sales"].std()
median_sales = df_f["Sales"].median()
n_days = len(df_f)

# Comparison with previous equivalent period
period_len = (end_date - start_date).days + 1

prev_end = start_date - timedelta(days=1)

prev_start = prev_end - timedelta(days=period_len - 1)

prev_mask = (
    (df["Date"].dt.date >= prev_start)
    & (df["Date"].dt.date <= prev_end)
)

df_prev = df.loc[prev_mask]

if not df_prev.empty:

    prev_total = df_prev["Sales"].sum()
    prev_avg = df_prev["Sales"].mean()

    growth_total = (
        ((total_sales - prev_total) / prev_total * 100)
        if prev_total else None
    )

    growth_avg = (
        ((avg_sales - prev_avg) / prev_avg * 100)
        if prev_avg else None
    )

else:

    growth_total = None
    growth_avg = None


# ============================================================
# KPI SECTION
# ============================================================
st.subheader("🎯 Key Performance Indicators (KPIs)")

c1, c2, c3, c4 = st.columns(4)

with c1:
    kpi_card(
        "Total Sales",
        f"{total_sales:,.2f} €",
        growth_total,
        "💰"
    )

with c2:
    kpi_card(
        "Average Sales",
        f"{avg_sales:,.2f} €",
        growth_avg,
        "📊"
    )

with c3:
    kpi_card(
        "Peak Sales",
        f"{max_sales:,.2f} €",
        None,
        "🚀"
    )

with c4:
    kpi_card(
        "Median Sales",
        f"{median_sales:,.2f} €",
        None,
        "📉"
    )


c5, c6, c7, c8 = st.columns(4)

with c5:
    kpi_card(
        "Minimum Sales",
        f"{min_sales:,.2f} €",
        None,
        "🔻"
    )

with c6:
    kpi_card(
        "Standard Deviation",
        f"{std_sales:,.2f} €",
        None,
        "📐"
    )

with c7:
    best_day = df_f.loc[
        df_f["Sales"].idxmax(), "Date"
    ].strftime("%d/%m/%Y")

    kpi_card(
        "Best Sales Day",
        best_day,
        None,
        "🏆"
    )

with c8:
    kpi_card(
        "Number of Observations",
        f"{n_days:,}",
        None,
        "🔢"
    )

st.markdown("---")


# ============================================================
# APPLICATION TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Sales Evolution",
    "🗓️ Seasonality",
    "📊 Distribution",
    "🔥 Correlations",
    "📋 Data Exploration"
])


# ============================================================
# TAB 1: TIME SERIES ANALYSIS
# ============================================================
with tab1:

    st.subheader("📈 Sales Evolution Over Time")

    agg_df = aggregate(df_f, granularity)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=agg_df["Period"],
        y=agg_df["Sales"],
        mode="lines+markers",
        name="Sales",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=6),
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.15)"
    ))

    if show_ma and len(agg_df) > 7:

        ma = agg_df["Sales"].rolling(
            window=min(7, max(2, len(agg_df)//2)),
            min_periods=1
        ).mean()

        fig.add_trace(go.Scatter(
            x=agg_df["Period"],
            y=ma,
            mode="lines",
            name="Moving Average",
            line=dict(
                color="#ff7f0e",
                width=2,
                dash="dash"
            )
        ))

    if show_trend and len(agg_df) > 1:

        x_num = np.arange(len(agg_df))

        coeffs = np.polyfit(
            x_num,
            agg_df["Sales"],
            1
        )

        trend = np.polyval(coeffs, x_num)

        fig.add_trace(go.Scatter(
            x=agg_df["Period"],
            y=trend,
            mode="lines",
            name="Linear Trend",
            line=dict(
                color="#2ca02c",
                width=2,
                dash="dot"
            )
        ))

    fig.update_layout(
        template="plotly_white",
        height=500,
        xaxis_title="Period",
        yaxis_title="Sales (€)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.1
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:

        st.subheader("💹 Period-over-Period Variation")

        if len(agg_df) > 1:

            agg_df["Variation_%"] = (
                agg_df["Sales"].pct_change() * 100
            )

            colors = [
                "#28a745" if v >= 0 else "#dc3545"
                for v in agg_df["Variation_%"].fillna(0)
            ]

            fig_var = go.Figure(go.Bar(
                x=agg_df["Period"],
                y=agg_df["Variation_%"],
                marker_color=colors,
                name="Variation %"
            ))

            fig_var.update_layout(
                template="plotly_white",
                height=350,
                xaxis_title="Period",
                yaxis_title="Variation (%)",
                showlegend=False
            )

            st.plotly_chart(
                fig_var,
                use_container_width=True
            )

        else:

            st.info(
                "Not enough observations to calculate variation."
            )

    with col_b:

        st.subheader("📊 Cumulative Sales")

        agg_df["Cumulative"] = agg_df["Sales"].cumsum()

        fig_cum = go.Figure(go.Scatter(
            x=agg_df["Period"],
            y=agg_df["Cumulative"],
            mode="lines",
            fill="tozeroy",
            line=dict(
                color="#9467bd",
                width=3
            )
        ))

        fig_cum.update_layout(
            template="plotly_white",
            height=350,
            xaxis_title="Period",
            yaxis_title="Cumulative Sales (€)"
        )

        st.plotly_chart(
            fig_cum,
            use_container_width=True
        )


# ============================================================
# TAB 2: SEASONALITY ANALYSIS
# ============================================================
with tab2:

    st.subheader("🗓️ Seasonality Analysis")

    dow_order = [
        "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday"
    ]

    month_order = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    col1, col2 = st.columns(2)

    with col1:

        dow = (
            df_f.groupby("Day_of_Week")["Sales"]
            .mean()
            .reindex(dow_order)
            .dropna()
        )

        fig_dow = px.bar(
            x=dow.index,
            y=dow.values,
            labels={
                "x": "Day of Week",
                "y": "Average Sales (€)"
            },
            color=dow.values,
            color_continuous_scale="Blues",
            title="Average Sales by Day of the Week"
        )

        fig_dow.update_layout(
            template="plotly_white",
            height=400,
            showlegend=False,
            coloraxis_showscale=False
        )

        st.plotly_chart(
            fig_dow,
            use_container_width=True
        )

    with col2:

        df_f["Month_Label"] = (
            df_f["Date"].dt.strftime("%b")
        )

        by_month = (
            df_f.groupby("Month_Label")["Sales"]
            .mean()
            .reindex(month_order)
            .dropna()
        )

        fig_month = px.bar(
            x=by_month.index,
            y=by_month.values,
            labels={
                "x": "Month",
                "y": "Average Sales (€)"
            },
            color=by_month.values,
            color_continuous_scale="Viridis",
            title="Average Sales by Month"
        )

        fig_month.update_layout(
            template="plotly_white",
            height=400,
            showlegend=False,
            coloraxis_showscale=False
        )

        st.plotly_chart(
            fig_month,
            use_container_width=True
        )

    # Heatmap
    st.subheader("🔥 Heatmap: Day of the Week × Month")

    df_f["Day_Name"] = df_f["Day_of_Week"]

    pivot = df_f.pivot_table(
        values="Sales",
        index="Day_Name",
        columns="Month_Label",
        aggfunc="mean"
    )

    pivot = pivot.reindex(
        [d for d in dow_order if d in pivot.index]
    )

    pivot = pivot.reindex(
        columns=[m for m in month_order if m in pivot.columns]
    )

    fig_heat = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels={
            "x": "Month",
            "y": "Day of the Week",
            "color": "Sales (€)"
        },
        title="Average Sales (Day × Month)"
    )

    fig_heat.update_layout(
        template="plotly_white",
        height=450
    )

    st.plotly_chart(
        fig_heat,
        use_container_width=True
    )

    # Box plot by month
    st.subheader("📦 Monthly Sales Distribution")

    fig_box = px.box(
        df_f,
        x="Month_Label",
        y="Sales",
        category_orders={
            "Month_Label": month_order
        },
        color="Month_Label",
        color_discrete_sequence=px.colors.qualitative.Set3,
        labels={
            "Month_Label": "Month",
            "Sales": "Sales (€)"
        },
        title="Sales Distribution by Month"
    )

    fig_box.update_layout(
        template="plotly_white",
        height=450,
        showlegend=False
    )

    st.plotly_chart(
        fig_box,
        use_container_width=True
    )


# ============================================================
# TAB 3: SALES DISTRIBUTION
# ============================================================
with tab3:

    st.subheader("📊 Sales Distribution Analysis")

    col1, col2 = st.columns(2)

    with col1:

        fig_hist = px.histogram(
            df_f,
            x="Sales",
            nbins=40,
            labels={
                "Sales": "Sales (€)"
            },
            title="Sales Histogram",
            color_discrete_sequence=["#1f77b4"]
        )

        fig_hist.add_vline(
            x=avg_sales,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Mean: {avg_sales:.1f}",
            annotation_position="top"
        )

        fig_hist.add_vline(
            x=median_sales,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Median: {median_sales:.1f}",
            annotation_position="bottom"
        )

        fig_hist.update_layout(
            template="plotly_white",
            height=400
        )

        st.plotly_chart(
            fig_hist,
            use_container_width=True
        )

    with col2:

        fig_box2 = px.box(
            df_f,
            y="Sales",
            points="all",
            labels={
                "Sales": "Sales (€)"
            },
            title="Sales Box Plot",
            color_discrete_sequence=["#ff7f0e"]
        )

        fig_box2.update_layout(
            template="plotly_white",
            height=400
        )

        st.plotly_chart(
            fig_box2,
            use_container_width=True
        )

    # Descriptive statistics
    st.subheader("📈 Descriptive Statistics")

    stats_df = pd.DataFrame({
        "Statistic": [
            "Count",
            "Mean",
            "Median",
            "Standard Deviation",
            "Minimum",
            "Q1 (25%)",
            "Q3 (75%)",
            "Maximum"
        ],

        "Value": [
            f"{len(df_f):,}",
            f"{df_f['Sales'].mean():.2f}",
            f"{df_f['Sales'].median():.2f}",
            f"{df_f['Sales'].std():.2f}",
            f"{df_f['Sales'].min():.2f}",
            f"{df_f['Sales'].quantile(0.25):.2f}",
            f"{df_f['Sales'].quantile(0.75):.2f}",
            f"{df_f['Sales'].max():.2f}"
        ]
    })

    st.dataframe(
        stats_df,
        use_container_width=True,
        hide_index=True
    )

    # Outlier detection
    st.subheader("🎯 Outlier Detection (IQR Method)")

    q1 = df_f["Sales"].quantile(0.25)
    q3 = df_f["Sales"].quantile(0.75)

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = df_f[
        (df_f["Sales"] < lower)
        | (df_f["Sales"] > upper)
    ]

    if outliers.empty:

        st.success(
            "No outliers detected in the selected period."
        )

    else:

        st.warning(
            f"{len(outliers)} outlier(s) detected "
            f"(Bounds: [{lower:.2f} ; {upper:.2f}])"
        )

        st.dataframe(
            outliers[["Date", "Sales"]].style.format(
                {"Sales": "{:.2f}"}
            ),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 4: CORRELATION ANALYSIS
# ============================================================
with tab4:

    st.subheader("🔥 Correlation and Trend Analysis")

    df_corr = df_f.copy()

    df_corr["Day_of_Week_Num"] = (
        df_corr["Date"].dt.weekday
    )

    df_corr["Month_Num"] = (
        df_corr["Date"].dt.month
    )

    df_corr["Quarter"] = (
        df_corr["Date"].dt.quarter
    )

    df_corr["Day_of_Month"] = (
        df_corr["Date"].dt.day
    )

    df_corr["Lag_1"] = (
        df_corr["Sales"].shift(1)
    )

    df_corr["Lag_7"] = (
        df_corr["Sales"].shift(7)
    )

    df_corr["MA_7"] = (
        df_corr["Sales"].rolling(7).mean()
    )

    corr_cols = [
        "Sales",
        "Day_of_Week_Num",
        "Month_Num",
        "Quarter",
        "Day_of_Month",
        "Lag_1",
        "Lag_7",
        "MA_7"
    ]

    corr_matrix = df_corr[corr_cols].corr()

    fig_corr = px.imshow(
        corr_matrix,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlation Matrix"
    )

    fig_corr.update_layout(
        template="plotly_white",
        height=500
    )

    st.plotly_chart(
        fig_corr,
        use_container_width=True
    )

    col1, col2 = st.columns(2)

    with col1:

        fig_lag = px.scatter(
            df_corr.dropna(subset=["Lag_7"]),
            x="Lag_7",
            y="Sales",
            labels={
                "Lag_7": "Sales (T-7) (€)",
                "Sales": "Sales (T) (€)"
            },
            title="Sales Today vs Sales 7 Days Ago",
            opacity=0.6,
            trendline="ols",
            trendline_color_override="red"
        )

        fig_lag.update_layout(
            template="plotly_white",
            height=400
        )

        st.plotly_chart(
            fig_lag,
            use_container_width=True
        )

    with col2:

        by_quarter = (
            df_f.groupby("Quarter")["Sales"]
            .agg(["sum", "mean"])
            .reset_index()
        )

        by_quarter["Quarter"] = (
            "Q" + by_quarter["Quarter"].astype(str)
        )

        fig_q = px.bar(
            by_quarter,
            x="Quarter",
            y="sum",
            labels={
                "sum": "Total Sales (€)",
                "Quarter": "Quarter"
            },
            title="Total Sales by Quarter",
            color="Quarter",
            color_discrete_sequence=px.colors.qualitative.Bold
        )

        fig_q.update_layout(
            template="plotly_white",
            height=400,
            showlegend=False
        )

        st.plotly_chart(
            fig_q,
            use_container_width=True
        )


# ============================================================
# TAB 5: DATA EXPLORATION
# ============================================================
with tab5:

    st.subheader("📋 Data Exploration")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Number of Rows",
            f"{len(df_f):,}"
        )

    with col2:
        st.metric(
            "Number of Columns",
            len(df_f.columns)
        )

    with col3:
        st.metric(
            "Period",
            f"{(end_date - start_date).days + 1} days"
        )

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:

        search = st.text_input(
            "🔍 Search for a date (e.g. 2022-05)",
            ""
        )

    with col2:

        sort_order = st.selectbox(
            "Sort by",
            [
                "Date Ascending",
                "Date Descending",
                "Sales Ascending",
                "Sales Descending"
            ]
        )

    df_display = df_f.copy()

    if search:

        df_display = df_display[
            df_display["Date"]
            .dt.strftime("%Y-%m-%d")
            .str.contains(search, case=False, na=False)
        ]

    if sort_order == "Date Ascending":

        df_display = df_display.sort_values("Date")

    elif sort_order == "Date Descending":

        df_display = df_display.sort_values(
            "Date",
            ascending=False
        )

    elif sort_order == "Sales Ascending":

        df_display = df_display.sort_values("Sales")

    else:

        df_display = df_display.sort_values(
            "Sales",
            ascending=False
        )

    st.dataframe(
        df_display[
            [
                "Date",
                "Sales",
                "Year",
                "Month_Name",
                "Day_of_Week"
            ]
        ].style.format(
            {"Sales": "{:.2f}"}
        ).background_gradient(
            subset=["Sales"],
            cmap="Blues"
        ),
        use_container_width=True,
        height=450
    )

    # CSV export
    csv = df_display.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download Filtered Data (CSV)",
        data=csv,
        file_name=f"sales_{start_date}_{end_date}.csv",
        mime="text/csv"
    )


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")

st.markdown(
    "<div style='text-align:center; color:gray;'>"
    "📊 Sales Dashboard • Developed with Streamlit & Plotly"
    "</div>",
    unsafe_allow_html=True
)
