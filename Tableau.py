# ============================================================
# VÉRIFICATION DES DÉPENDANCES
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
    print("❌ Modules manquants :", ", ".join(missing))
    print("\n➡️ Installez-les avec :")
    print(f"   pip install {' '.join(missing)}")
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
# CONFIGURATION DE LA PAGE
# ============================================================
st.set_page_config(
    page_title="Dashboard Ventes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CHARGEMENT DES DONNÉES (ROBUSTE)
# ============================================================
@st.cache_data
def load_data():
    """Charge sales.csv en cherchant à plusieurs emplacements."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    candidats = [
        os.path.join(BASE_DIR, "sales.csv"),
        os.path.join(BASE_DIR, "data", "sales.csv"),
        os.path.join(BASE_DIR, "projet", "sales.csv"),
        os.path.join(os.getcwd(), "sales.csv"),
        "sales.csv",
    ]
    
    csv_path = next((c for c in candidats if os.path.exists(c)), None)
    
    if csv_path is None:
        st.error("❌ Fichier `sales.csv` introuvable.")
        st.markdown("**Emplacements recherchés :**")
        for c in candidats:
            st.code(c, language="text")
        st.info(
            "💡 **Solutions :**\n\n"
            "1. Placez `sales.csv` dans le **même dossier** que `Tableau.py`\n"
            "2. Ou chargez-le manuellement via l'uploader ci-dessous"
        )
        uploaded = st.file_uploader("📂 Charger sales.csv manuellement", type=["csv"])
        if uploaded is None:
            st.stop()
        source = uploaded
    else:
        source = csv_path
        st.sidebar.success(f"✅ Données chargées : `{os.path.basename(csv_path)}`")
    
    df = pd.read_csv(source, index_col=0, parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    
    # Variables dérivées
    df["Année"] = df["Date"].dt.year
    df["Mois"] = df["Date"].dt.month
    df["Mois_Nom"] = df["Date"].dt.strftime("%b")
    df["Jour_Semaine"] = df["Date"].dt.day_name()
    df["Semaine"] = df["Date"].dt.isocalendar().week.astype(int)
    df["Trimestre"] = df["Date"].dt.quarter
    df["Jour"] = df["Date"].dt.day
    return df

# ============================================================
# CSS PERSONNALISÉ
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
    .kpi-card h3 { margin: 0; font-size: 0.9rem; opacity: 0.9; }
    .kpi-card h2 { margin: 0.5rem 0 0 0; font-size: 1.8rem; }
    .kpi-card p  { margin: 0.3rem 0 0 0; font-size: 0.85rem; opacity: 0.8; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CHARGEMENT
# ============================================================
df = load_data()

# ============================================================
# SIDEBAR - FILTRES
# ============================================================
st.sidebar.title("🎛️ Filtres")
st.sidebar.markdown("---")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "📅 Période d'analyse",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

st.sidebar.markdown("---")
st.sidebar.subheader("🗓️ Granularité d'agrégation")
granularity = st.sidebar.selectbox(
    "Agréger par",
    ["Journalier", "Hebdomadaire", "Mensuel", "Trimestriel"],
    index=2
)

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Options d'affichage")
show_ma = st.sidebar.checkbox("Afficher la moyenne mobile (7j)", value=True)
show_trend = st.sidebar.checkbox("Afficher la ligne de tendance", value=False)

st.sidebar.markdown("---")
st.sidebar.caption("💡 Dashboard développé avec Streamlit")

# Filtrage
mask = (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)
df_f = df.loc[mask].copy()

if df_f.empty:
    st.warning("⚠️ Aucune donnée sur la période sélectionnée.")
    st.stop()

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================
def aggregate(df_in, gran):
    if gran == "Journalier":
        return (
            df_in.groupby(df_in["Date"].dt.date)["Sales"]
            .sum().reset_index().rename(columns={"Date": "Période"})
        )
    elif gran == "Hebdomadaire":
        tmp = df_in.copy()
        tmp["Période"] = tmp["Date"].dt.to_period("W").dt.start_time
        return tmp.groupby("Période")["Sales"].sum().reset_index()
    elif gran == "Mensuel":
        tmp = df_in.copy()
        tmp["Période"] = tmp["Date"].dt.to_period("M").dt.to_timestamp()
        return tmp.groupby("Période")["Sales"].sum().reset_index()
    else:
        tmp = df_in.copy()
        tmp["Période"] = tmp["Date"].dt.to_period("Q").dt.to_timestamp()
        return tmp.groupby("Période")["Sales"].sum().reset_index()


def kpi_card(title, value, delta=None, icon="📈"):
    arrow = "▲" if (delta is not None and delta >= 0) else "▼"
    delta_color = "#d4edda" if (delta is not None and delta >= 0) else "#f8d7da"
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
# EN-TÊTE
# ============================================================
st.markdown('<div class="main-header">📊 Dashboard Ventes — Analyse complète</div>',
            unsafe_allow_html=True)
st.caption(f"Période analysée : **{start_date}** → **{end_date}** | "
           f"Nombre d'observations : **{len(df_f):,}**")
st.markdown("---")

# ============================================================
# CALCUL DES KPI
# ============================================================
total_sales = df_f["Sales"].sum()
avg_sales = df_f["Sales"].mean()
max_sales = df_f["Sales"].max()
min_sales = df_f["Sales"].min()
std_sales = df_f["Sales"].std()
median_sales = df_f["Sales"].median()
n_days = len(df_f)

# Comparaison avec période précédente équivalente
period_len = (end_date - start_date).days + 1
prev_end = start_date - timedelta(days=1)
prev_start = prev_end - timedelta(days=period_len - 1)
prev_mask = (df["Date"].dt.date >= prev_start) & (df["Date"].dt.date <= prev_end)
df_prev = df.loc[prev_mask]

if not df_prev.empty:
    prev_total = df_prev["Sales"].sum()
    prev_avg = df_prev["Sales"].mean()
    growth_total = ((total_sales - prev_total) / prev_total * 100) if prev_total else None
    growth_avg = ((avg_sales - prev_avg) / prev_avg * 100) if prev_avg else None
else:
    growth_total = growth_avg = None

# ============================================================
# SECTION KPI
# ============================================================
st.subheader("🎯 Indicateurs Clés de Performance")

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Ventes Totales", f"{total_sales:,.2f} €", growth_total, "💰")
with c2:
    kpi_card("Ventes Moyennes", f"{avg_sales:,.2f} €", growth_avg, "📊")
with c3:
    kpi_card("Pic de Ventes", f"{max_sales:,.2f} €", None, "🚀")
with c4:
    kpi_card("Ventes Médianes", f"{median_sales:,.2f} €", None, "📉")

c5, c6, c7, c8 = st.columns(4)
with c5:
    kpi_card("Minimum", f"{min_sales:,.2f} €", None, "🔻")
with c6:
    kpi_card("Écart-type", f"{std_sales:,.2f} €", None, "📐")
with c7:
    best_day = df_f.loc[df_f["Sales"].idxmax(), "Date"].strftime("%d/%m/%Y")
    kpi_card("Meilleur Jour", best_day, None, "🏆")
with c8:
    kpi_card("Nb Observations", f"{n_days:,}", None, "🔢")

st.markdown("---")

# ============================================================
# ONGLETS
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Évolution", "🗓️ Saisonnalité", "📊 Distribution", "🔥 Corrélations", "📋 Données"
])

# ============================================================
# TAB 1 : ÉVOLUTION TEMPORELLE
# ============================================================
with tab1:
    st.subheader("📈 Évolution temporelle des ventes")
    agg_df = aggregate(df_f, granularity)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=agg_df["Période"], y=agg_df["Sales"],
        mode="lines+markers", name="Ventes",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=6),
        fill="tozeroy", fillcolor="rgba(31,119,180,0.15)"
    ))

    if show_ma and len(agg_df) > 7:
        ma = agg_df["Sales"].rolling(window=min(7, max(2, len(agg_df)//2)),
                                     min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=agg_df["Période"], y=ma,
            mode="lines", name="Moyenne mobile",
            line=dict(color="#ff7f0e", width=2, dash="dash")
        ))

    if show_trend and len(agg_df) > 1:
        x_num = np.arange(len(agg_df))
        coeffs = np.polyfit(x_num, agg_df["Sales"], 1)
        trend = np.polyval(coeffs, x_num)
        fig.add_trace(go.Scatter(
            x=agg_df["Période"], y=trend,
            mode="lines", name="Tendance linéaire",
            line=dict(color="#2ca02c", width=2, dash="dot")
        ))

    fig.update_layout(
        template="plotly_white", height=500,
        xaxis_title="Période", yaxis_title="Ventes (€)",
        hovermode="x unified", legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("💹 Variation période sur période")
        if len(agg_df) > 1:
            agg_df["Variation_%"] = agg_df["Sales"].pct_change() * 100
            colors = ["#28a745" if v >= 0 else "#dc3545"
                      for v in agg_df["Variation_%"].fillna(0)]
            fig_var = go.Figure(go.Bar(
                x=agg_df["Période"], y=agg_df["Variation_%"],
                marker_color=colors, name="Variation %"
            ))
            fig_var.update_layout(
                template="plotly_white", height=350,
                xaxis_title="Période", yaxis_title="Variation (%)",
                showlegend=False
            )
            st.plotly_chart(fig_var, use_container_width=True)
        else:
            st.info("Pas assez de points pour calculer la variation.")

    with col_b:
        st.subheader("📊 Ventes cumulées")
        agg_df["Cumul"] = agg_df["Sales"].cumsum()
        fig_cum = go.Figure(go.Scatter(
            x=agg_df["Période"], y=agg_df["Cumul"],
            mode="lines", fill="tozeroy",
            line=dict(color="#9467bd", width=3)
        ))
        fig_cum.update_layout(
            template="plotly_white", height=350,
            xaxis_title="Période", yaxis_title="Cumul (€)"
        )
        st.plotly_chart(fig_cum, use_container_width=True)

# ============================================================
# TAB 2 : SAISONNALITÉ
# ============================================================
with tab2:
    st.subheader("🗓️ Analyse de la saisonnalité")

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_fr = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
              "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi",
              "Sunday": "Dimanche"}
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    months_fr = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                 "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

    col1, col2 = st.columns(2)

    with col1:
        dow = df_f.groupby("Jour_Semaine")["Sales"].mean().reindex(dow_order).dropna()
        dow.index = [dow_fr[i] for i in dow.index]
        fig_dow = px.bar(
            x=dow.index, y=dow.values,
            labels={"x": "Jour", "y": "Ventes moyennes (€)"},
            color=dow.values, color_continuous_scale="Blues",
            title="Ventes moyennes par jour de la semaine"
        )
        fig_dow.update_layout(template="plotly_white", height=400,
                              showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_dow, use_container_width=True)

    with col2:
        df_f["Mois_Label"] = df_f["Date"].dt.strftime("%b")
        by_month = df_f.groupby("Mois_Label")["Sales"].mean().reindex(month_order).dropna()
        by_month.index = [months_fr[month_order.index(m)] for m in by_month.index]
        fig_month = px.bar(
            x=by_month.index, y=by_month.values,
            labels={"x": "Mois", "y": "Ventes moyennes (€)"},
            color=by_month.values, color_continuous_scale="Viridis",
            title="Ventes moyennes par mois"
        )
        fig_month.update_layout(template="plotly_white", height=400,
                                showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_month, use_container_width=True)

    # Heatmap
    st.subheader("🔥 Heatmap : Jour de semaine × Mois")
    df_f["Jour_FR"] = df_f["Jour_Semaine"].map(dow_fr)
    pivot = df_f.pivot_table(
        values="Sales", index="Jour_FR", columns="Mois_Label", aggfunc="mean"
    )
    pivot = pivot.reindex([dow_fr[d] for d in dow_order if dow_fr[d] in pivot.index])
    pivot = pivot.reindex(columns=[c for c in month_order if c in pivot.columns])
    pivot.columns = [months_fr[month_order.index(c)] for c in pivot.columns]

    fig_heat = px.imshow(
        pivot, aspect="auto", color_continuous_scale="YlOrRd",
        labels=dict(x="Mois", y="Jour", color="Ventes (€)"),
        title="Ventes moyennes (Jour × Mois)"
    )
    fig_heat.update_layout(template="plotly_white", height=450)
    st.plotly_chart(fig_heat, use_container_width=True)

    # Box plot par mois
    st.subheader("📦 Distribution par mois")
    fig_box = px.box(
        df_f, x="Mois_Label", y="Sales",
        category_orders={"Mois_Label": month_order},
        color="Mois_Label", color_discrete_sequence=px.colors.qualitative.Set3,
        labels={"Mois_Label": "Mois", "Sales": "Ventes (€)"},
        title="Distribution des ventes par mois"
    )
    fig_box.update_layout(template="plotly_white", height=450, showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

# ============================================================
# TAB 3 : DISTRIBUTION
# ============================================================
with tab3:
    st.subheader("📊 Analyse de la distribution des ventes")

    col1, col2 = st.columns(2)

    with col1:
        fig_hist = px.histogram(
            df_f, x="Sales", nbins=40,
            labels={"Sales": "Ventes (€)"},
            title="Histogramme des ventes",
            color_discrete_sequence=["#1f77b4"]
        )
        fig_hist.add_vline(x=avg_sales, line_dash="dash", line_color="red",
                           annotation_text=f"Moyenne: {avg_sales:.1f}",
                           annotation_position="top")
        fig_hist.add_vline(x=median_sales, line_dash="dash", line_color="green",
                           annotation_text=f"Médiane: {median_sales:.1f}",
                           annotation_position="bottom")
        fig_hist.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        fig_box2 = px.box(
            df_f, y="Sales", points="all",
            labels={"Sales": "Ventes (€)"},
            title="Box plot des ventes",
            color_discrete_sequence=["#ff7f0e"]
        )
        fig_box2.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig_box2, use_container_width=True)

    st.subheader("📈 Statistiques descriptives")
    stats_df = pd.DataFrame({
        "Statistique": ["Nombre", "Moyenne", "Médiane", "Écart-type",
                        "Minimum", "Q1 (25%)", "Q3 (75%)", "Maximum"],
        "Valeur": [
            f"{len(df_f):,}",
            f"{df_f['Sales'].mean():.2f}",
            f"{df_f['Sales'].median():.2f}",
            f"{df_f['Sales'].std():.2f}",
            f"{df_f['Sales'].min():.2f}",
            f"{df_f['Sales'].quantile(0.25):.2f}",
            f"{df_f['Sales'].quantile(0.75):.2f}",
            f"{df_f['Sales'].max():.2f}",
        ]
    })
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

    # Détection des outliers
    st.subheader("🎯 Détection des valeurs extrêmes (méthode IQR)")
    q1 = df_f["Sales"].quantile(0.25)
    q3 = df_f["Sales"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = df_f[(df_f["Sales"] < lower) | (df_f["Sales"] > upper)]

    if outliers.empty:
        st.success("✅ Aucune valeur aberrante détectée sur la période sélectionnée.")
    else:
        st.warning(f"⚠️ {len(outliers)} valeur(s) extrême(s) détectée(s) "
                   f"(bornes : [{lower:.2f} ; {upper:.2f}])")
        st.dataframe(
            outliers[["Date", "Sales"]].style.format({"Sales": "{:.2f}"}),
            use_container_width=True, hide_index=True
        )

# ============================================================
# TAB 4 : CORRÉLATIONS
# ============================================================
with tab4:
    st.subheader("🔥 Analyse des corrélations et tendances")

    df_corr = df_f.copy()
    df_corr["Jour_Semaine_Num"] = df_corr["Date"].dt.weekday
    df_corr["Mois_Num"] = df_corr["Date"].dt.month
    df_corr["Trimestre"] = df_corr["Date"].dt.quarter
    df_corr["Jour_Mois"] = df_corr["Date"].dt.day
    df_corr["Lag_1"] = df_corr["Sales"].shift(1)
    df_corr["Lag_7"] = df_corr["Sales"].shift(7)
    df_corr["MA_7"] = df_corr["Sales"].rolling(7).mean()

    corr_cols = ["Sales", "Jour_Semaine_Num", "Mois_Num", "Trimestre",
                 "Jour_Mois", "Lag_1", "Lag_7", "MA_7"]
    corr_matrix = df_corr[corr_cols].corr()

    fig_corr = px.imshow(
        corr_matrix, text_auto=".2f", aspect="auto",
        color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        title="Matrice de corrélation"
    )
    fig_corr.update_layout(template="plotly_white", height=500)
    st.plotly_chart(fig_corr, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_lag = px.scatter(
            df_corr.dropna(subset=["Lag_7"]), x="Lag_7", y="Sales",
            labels={"Lag_7": "Ventes J-7 (€)", "Sales": "Ventes J (€)"},
            title="Ventes J vs Ventes J-7",
            opacity=0.6,
            trendline="ols", trendline_color_override="red"
        )
        fig_lag.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig_lag, use_container_width=True)

    with col2:
        by_quarter = df_f.groupby("Trimestre")["Sales"].agg(["sum", "mean"]).reset_index()
        by_quarter["Trimestre"] = "T" + by_quarter["Trimestre"].astype(str)
        fig_q = px.bar(
            by_quarter, x="Trimestre", y="sum",
            labels={"sum": "Ventes totales (€)", "Trimestre": "Trimestre"},
            title="Ventes totales par trimestre",
            color="Trimestre", color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_q.update_layout(template="plotly_white", height=400, showlegend=False)
        st.plotly_chart(fig_q, use_container_width=True)

# ============================================================
# TAB 5 : DONNÉES
# ============================================================
with tab5:
    st.subheader("📋 Exploration des données")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nombre de lignes", f"{len(df_f):,}")
    with col2:
        st.metric("Nombre de colonnes", len(df_f.columns))
    with col3:
        st.metric("Période", f"{(end_date - start_date).days + 1} jours")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Rechercher une date (ex: 2022-05)", "")
    with col2:
        sort_order = st.selectbox(
            "Tri",
            ["Date croissante", "Date décroissante",
             "Ventes croissantes", "Ventes décroissantes"]
        )

    df_display = df_f.copy()
    if search:
        df_display = df_display[
            df_display["Date"].dt.strftime("%Y-%m-%d").str.contains(search)
        ]

    if sort_order == "Date croissante":
        df_display = df_display.sort_values("Date")
    elif sort_order == "Date décroissante":
        df_display = df_display.sort_values("Date", ascending=False)
    elif sort_order == "Ventes croissantes":
        df_display = df_display.sort_values("Sales")
    else:
        df_display = df_display.sort_values("Sales", ascending=False)

    st.dataframe(
        df_display[["Date", "Sales", "Année", "Mois_Nom", "Jour_Semaine"]]
        .style.format({"Sales": "{:.2f}"})
        .background_gradient(subset=["Sales"], cmap="Blues"),
        use_container_width=True, height=450
    )

    csv = df_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Télécharger les données filtrées (CSV)",
        data=csv,
        file_name=f"ventes_{start_date}_{end_date}.csv",
        mime="text/csv"
    )

# ============================================================
# PIED DE PAGE
# ============================================================
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:gray;'>"
    "📊 Dashboard Ventes • Développé avec Streamlit & Plotly"
    "</div>",
    unsafe_allow_html=True
)