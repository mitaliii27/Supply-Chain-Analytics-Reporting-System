# dashboards/app.py – Interactive KPI Dashboard (Streamlit)
"""
Launch with:  streamlit run dashboards/app.py
Reads from data/exports/ CSVs produced by the ETL pipeline.
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Allow importing from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.config import EXPORTS_DIR

st.set_page_config(
    page_title="Supply Chain Analytics",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data():
    def read(name):
        path = os.path.join(EXPORTS_DIR, f"{name}.csv")
        return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

    return {
        "delivery":   read("delivery_kpis"),
        "supplier":   read("supplier_kpis"),
        "inventory":  read("inventory_kpis"),
        "orders":     read("orders"),
        "suppliers":  read("suppliers"),
    }


data = load_data()

if all(v.empty for v in data.values()):
    st.error("No data found. Run the ETL pipeline first:  `python run_pipeline.py`")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.title("🔗 Supply Chain Analytics")
st.sidebar.markdown("---")

if not data["delivery"].empty:
    years = sorted(data["delivery"]["order_year"].unique())
    selected_year = st.sidebar.selectbox("Year", years, index=len(years)-1)
else:
    selected_year = 2023

if not data["suppliers"].empty:
    regions = ["All"] + sorted(data["suppliers"]["region"].dropna().unique().tolist())
    selected_region = st.sidebar.selectbox("Supplier Region", regions)
else:
    selected_region = "All"

st.sidebar.markdown("---")
st.sidebar.markdown("**Data last refreshed:** run `python run_pipeline.py` to update")

# ─────────────────────────────────────────────────────────────────────────────
# KPI cards
# ─────────────────────────────────────────────────────────────────────────────

st.title("📦 Supply Chain Analytics Dashboard")

if not data["delivery"].empty:
    yr_data = data["delivery"][data["delivery"]["order_year"] == selected_year]
    total_orders   = yr_data["total_orders"].sum()
    total_value    = yr_data["total_order_value"].sum()
    avg_otif       = yr_data["delivery_rate"].mean() * 100
    avg_delay      = yr_data["avg_delay_days"].mean()
    cancelled      = yr_data["cancelled"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders",      f"{total_orders:,.0f}")
    c2.metric("Order Value",       f"${total_value/1e6:.1f}M")
    c3.metric("OTIF Rate",         f"{avg_otif:.1f}%",
              delta=f"{avg_otif - 90:.1f}% vs 90% target")
    c4.metric("Avg Delay (days)",  f"{avg_delay:.1f}")
    c5.metric("Cancellations",     f"{cancelled:,}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Charts – Row 1
# ─────────────────────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Monthly Order Volume & Delivery Rate")
    if not data["delivery"].empty:
        df = data["delivery"][data["delivery"]["order_year"] == selected_year].copy()
        df["month_label"] = df["order_month"].apply(
            lambda m: ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m]
        )
        fig = go.Figure()
        fig.add_bar(x=df["month_label"], y=df["total_orders"],
                    name="Orders", marker_color="#3B82F6", yaxis="y")
        fig.add_scatter(x=df["month_label"], y=df["delivery_rate"]*100,
                        name="Delivery Rate %", mode="lines+markers",
                        line=dict(color="#10B981", width=2), yaxis="y2")
        fig.update_layout(
            yaxis=dict(title="Orders"),
            yaxis2=dict(title="Delivery Rate %", overlaying="y", side="right",
                        range=[0, 100]),
            legend=dict(x=0, y=1.15, orientation="h"),
            height=350, margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("⚠️ Supplier Risk Distribution")
    if not data["suppliers"].empty:
        df = data["suppliers"].copy()
        if selected_region != "All":
            df = df[df["region"] == selected_region]
        risk_counts = df["risk_flag"].value_counts().reset_index()
        risk_counts.columns = ["Risk Level", "Count"]
        color_map = {
            "Critical": "#EF4444", "High": "#F97316",
            "Medium": "#EAB308",   "Low": "#22C55E"
        }
        fig = px.pie(
            risk_counts, values="Count", names="Risk Level",
            color="Risk Level", color_discrete_map=color_map,
            hole=0.4,
        )
        fig.update_layout(height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Charts – Row 2
# ─────────────────────────────────────────────────────────────────────────────

col3, col4 = st.columns(2)

with col3:
    st.subheader("🏭 Warehouse Stock Health")
    if not data["inventory"].empty:
        df = data["inventory"].copy()
        fig = px.bar(
            df.sort_values("stockout_pct", ascending=True),
            x="stockout_pct", y="warehouse_id",
            orientation="h", color="stockout_pct",
            color_continuous_scale="RdYlGn_r",
            labels={"stockout_pct": "Stockout %", "warehouse_id": "Warehouse"},
        )
        fig.update_layout(height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("📊 Top 10 Suppliers by OTIF Rate")
    if not data["supplier"].empty:
        df = data["supplier"].copy()
        top = (
            df.groupby(["supplier_id", "supplier_name"])["otif_rate"]
            .mean()
            .nlargest(10)
            .reset_index()
        )
        fig = px.bar(
            top.sort_values("otif_rate"),
            x="otif_rate", y="supplier_name",
            orientation="h", color="otif_rate",
            color_continuous_scale="Blues",
            labels={"otif_rate": "OTIF Rate", "supplier_name": "Supplier"},
            range_x=[0, 1],
        )
        fig.update_layout(height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Raw data explorer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("🔍 Data Explorer")
table_choice = st.selectbox(
    "Select table to explore",
    ["delivery_kpis", "supplier_kpis", "inventory_kpis", "orders", "suppliers"],
)
key_map = {
    "delivery_kpis":  "delivery",
    "supplier_kpis":  "supplier",
    "inventory_kpis": "inventory",
    "orders":         "orders",
    "suppliers":      "suppliers",
}
df_show = data[key_map[table_choice]]
st.dataframe(df_show.head(500), use_container_width=True)
st.caption(f"Showing first 500 of {len(df_show):,} rows")
