import streamlit as st
import pandas as pd
import plotly.express as px
# import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import io
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Load API key from .env file
load_dotenv()
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Page configuration
st.set_page_config(
    page_title="RetailIQ — Operational Intelligence",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border: 1px solid #0f3460;
        border-bottom: 3px solid #00C4FF;
        border-radius: 12px;
        padding: 28px 32px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    ">
        <div>
            <div style="
                font-size: 32px;
                font-weight: 800;
                color: #ffffff;
                letter-spacing: -0.5px;
                margin-bottom: 6px;
            ">📊 RetailIQ - Operational Intelligence Dashboard</div>
            <div style="
                font-size: 14px;
                color: #a0aec0;
                letter-spacing: 0.3px;
            ">Retail performance analytics powered by AI, built on Sample Superstore data</div>
        </div>
        <div style="text-align: right;">
            <div style="
                font-size: 11px;
                color: #a0aec0;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 4px;
            ">Powered by</div>
            <div style="
                font-size: 13px;
                font-weight: 700;
                color: #00C4FF;
                letter-spacing: 0.5px;
            ">Groq · LLaMA 3.3 · Plotly</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("Sample - Superstore.csv", encoding="latin-1")
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    df["Month"] = df["Order Date"].dt.to_period("M").astype(str)
    return df

df = load_data()

# Data validation
required_columns = [
    "Order Date", "Region", "Category", "Sub-Category",
    "Sales", "Profit", "Quantity", "Discount", "Order ID"
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    st.error(
        f"Dataset is missing required columns: {missing_columns}. "
        f"Please ensure you are using the Sample Superstore dataset."
    )
    st.stop()

if df["Sales"].isnull().any() or df["Profit"].isnull().any():
    st.warning(
        "Dataset contains missing values in Sales or Profit columns. "
        "Some KPI calculations may be affected."
    )

def section_header(icon, title, subtitle=None):
    subtitle_html = (
        f'<div style="font-size:12px;color:#a0aec0;margin-top:4px;">'
        f'{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        f'<div style="'
        f'border-left:4px solid #00C4FF;'
        f'padding:8px 0 8px 16px;'
        f'margin:24px 0 16px 0;">'
        f'<div style="'
        f'font-size:18px;font-weight:700;'
        f'color:#ffffff;letter-spacing:0.3px;">'
        f'{icon} {title}</div>'
        f'{subtitle_html}'
        f'</div>',
        unsafe_allow_html=True
    )

# Sidebar filters
st.sidebar.header("Filters")
st.sidebar.markdown(
    "Use the filters below to drill down by region or product line. "
    "All KPIs, charts, and AI insights update automatically."
)

regions = ["All"] + sorted(df["Region"].unique().tolist())
selected_region = st.sidebar.selectbox("Select Region", regions)

categories = ["All"] + sorted(df["Category"].unique().tolist())
selected_category = st.sidebar.selectbox("Select Product Line", categories)

# Date range filter
st.sidebar.markdown("---")
st.sidebar.subheader("Period Range")

min_date = df["Order Date"].min().date()
max_date = df["Order Date"].max().date()

start_date, end_date = st.sidebar.slider(
    "Select period",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="MMM YYYY"
)

# KPI Comparison Mode
st.sidebar.markdown("---")
st.sidebar.subheader("KPI Display Mode")
comparison_mode = st.sidebar.radio(
    "Show KPIs as",
    options=["Absolute Values", "Period Change"],
    horizontal=False
)

# KPI Targets
st.sidebar.markdown("---")
st.sidebar.subheader("KPI Targets")
st.sidebar.markdown(
    '<p style="font-size:12px;color:#a0aec0;">Set targets to track progress '
    'against goals.</p>',
    unsafe_allow_html=True
)

revenue_target = st.sidebar.number_input(
    "Revenue Target (USD)",
    min_value=0,
    max_value=10000000,
    value=2500000,
    step=100000,
    format="%d"
)
st.sidebar.markdown(
    f'<p style="font-size:11px;color:#a0aec0;margin-top:-12px;">'
    f'Current: USD {revenue_target:,}</p>',
    unsafe_allow_html=True
)

profit_target = st.sidebar.number_input(
    "Profit Target (USD)",
    min_value=0,
    max_value=5000000,
    value=300000,
    step=10000,
    format="%d"
)
st.sidebar.markdown(
    f'<p style="font-size:11px;color:#a0aec0;margin-top:-12px;">'
    f'Current: USD {profit_target:,}</p>',
    unsafe_allow_html=True
)

orders_target = st.sidebar.number_input(
    "Orders Target",
    min_value=0,
    max_value=20000,
    value=5500,
    step=100,
    format="%d"
)
st.sidebar.markdown(
    f'<p style="font-size:11px;color:#a0aec0;margin-top:-12px;">'
    f'Current: {orders_target:,} orders</p>',
    unsafe_allow_html=True
)

# Period Comparison
st.sidebar.markdown("---")
st.sidebar.subheader("Period Comparison")
st.sidebar.markdown(
    '<p style="font-size:12px;color:#a0aec0;">Compare two time periods '
    'side by side.</p>',
    unsafe_allow_html=True
)

enable_comparison = st.sidebar.toggle("Enable Period Comparison")

if enable_comparison:
    st.sidebar.markdown(
        '<p style="font-size:12px;color:#a0aec0;margin-top:8px;">'
        'Period A (current)</p>',
        unsafe_allow_html=True
    )
    period_a_start, period_a_end = st.sidebar.slider(
        "Period A date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="MMM YYYY",
        key="slider_period_a"
    )

    st.sidebar.markdown(
        '<p style="font-size:12px;color:#a0aec0;margin-top:8px;">'
        'Period B (comparison)</p>',
        unsafe_allow_html=True
    )
    period_b_start, period_b_end = st.sidebar.slider(
        "Period B date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="MMM YYYY",
        key="slider_period_b"
    )

# Apply filters
filtered_df = df.copy()
if selected_region != "All":
    filtered_df = filtered_df[filtered_df["Region"] == selected_region]
if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

import calendar

start_date_forced = start_date.replace(day=1)
end_date_forced = end_date.replace(
    day=calendar.monthrange(end_date.year, end_date.month)[1]
)

filtered_df = filtered_df[
    (filtered_df["Order Date"].dt.date >= start_date_forced) &
    (filtered_df["Order Date"].dt.date <= end_date_forced)
]

# KPI calculations
total_revenue = filtered_df["Sales"].sum()
total_profit = filtered_df["Profit"].sum()
profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
total_orders = filtered_df["Order ID"].nunique()
avg_discount = (
    (filtered_df["Discount"] * filtered_df["Sales"]).sum() /
    filtered_df["Sales"].sum() * 100
    if filtered_df["Sales"].sum() > 0 else 0
)

# Monthly aggregation
monthly_df = filtered_df.groupby("Month").agg(
    Revenue=("Sales", "sum"),
    Profit=("Profit", "sum"),
    Orders=("Order ID", "nunique")
).reset_index()

# Period change calculations for KPI display mode
sorted_months = monthly_df.sort_values("Month")

# Calculate the preceding period of equal length
selected_days = (end_date_forced - start_date_forced).days
preceding_end = start_date_forced - pd.Timedelta(days=1)
preceding_start = preceding_end - pd.Timedelta(days=selected_days)

# Check if preceding period exists in the dataset
dataset_min_date = df["Order Date"].min().date()
preceding_period_available = preceding_start >= dataset_min_date

if preceding_period_available:
    # Filter preceding period data
    preceding_df = df.copy()
    if selected_region != "All":
        preceding_df = preceding_df[
            preceding_df["Region"] == selected_region
        ]
    if selected_category != "All":
        preceding_df = preceding_df[
            preceding_df["Category"] == selected_category
        ]
    preceding_df = preceding_df[
        (preceding_df["Order Date"].dt.date >= preceding_start) &
        (preceding_df["Order Date"].dt.date <= preceding_end)
    ].copy()

    preceding_revenue = preceding_df["Sales"].sum()
    preceding_profit = preceding_df["Profit"].sum()
    preceding_orders = preceding_df["Order ID"].nunique()

    revenue_pct = (
        ((total_revenue - preceding_revenue) / preceding_revenue * 100)
        if preceding_revenue else 0
    )
    profit_pct = (
        ((total_profit - preceding_profit) / preceding_profit * 100)
        if preceding_profit else 0
    )
    orders_pct = (
        ((total_orders - preceding_orders) / preceding_orders * 100)
        if preceding_orders else 0
    )

    preceding_period_label = (
        f"{preceding_start.strftime('%b %Y')} to "
        f"{preceding_end.strftime('%b %Y')}"
    )
else:
    revenue_pct = 0
    profit_pct = 0
    orders_pct = 0
    preceding_period_label = ""

section_header(
    "📊",
    "Key Performance Indicators",
    "Showing metrics for the selected region, product line, and date range"
)

# Show warning if period change mode is on but no prior period exists
if comparison_mode == "Period Change" and not preceding_period_available:
    st.markdown(
        '<div style="background-color:#2e1a1a;border:1px solid #5a2d2d;'
        'border-left:4px solid #fc8181;border-radius:8px;'
        'padding:12px 16px;margin-bottom:16px;">'
        '<div style="font-size:13px;font-weight:700;color:#fc8181;'
        'margin-bottom:4px;">No prior period available</div>'
        '<div style="font-size:12px;color:#a0aec0;">'
        'Period Change mode requires a preceding period of equal length '
        'within the dataset. Please select a shorter or later date range '
        'to enable period change view. Showing absolute values instead.'
        '</div></div>',
        unsafe_allow_html=True
    )
    effective_mode = "Absolute Values"
elif comparison_mode == "Period Change" and preceding_period_available:
    st.markdown(
        f'<div style="background-color:#1a2e1a;border:1px solid #2d5a2d;'
        f'border-left:4px solid #48bb78;border-radius:8px;'
        f'padding:10px 16px;margin-bottom:16px;">'
        f'<div style="font-size:12px;color:#a0aec0;">'
        f'Showing change vs preceding period: '
        f'<span style="color:#48bb78;font-weight:600;">'
        f'{preceding_period_label}</span></div>'
        f'</div>',
        unsafe_allow_html=True
    )
    effective_mode = "Period Change"
else:
    effective_mode = "Absolute Values"

kpi_cards = [
    {
        "label": "Total Revenue" if effective_mode == "Absolute Values" else "Revenue Change",
        "value": f"${total_revenue:,.0f}" if effective_mode == "Absolute Values" else (
            f"+{revenue_pct:.1f}%" if revenue_pct >= 0 else f"{revenue_pct:.1f}%"
        )
    },
    {
        "label": "Total Profit" if effective_mode == "Absolute Values" else "Profit Change",
        "value": f"${total_profit:,.0f}" if effective_mode == "Absolute Values" else (
            f"+{profit_pct:.1f}%" if profit_pct >= 0 else f"{profit_pct:.1f}%"
        )
    },
    {
        "label": "Profit Margin",
        "value": f"{profit_margin:.1f}%"
    },
    {
        "label": "Total Orders" if effective_mode == "Absolute Values" else "Orders Change",
        "value": f"{total_orders:,}" if effective_mode == "Absolute Values" else (
            f"+{orders_pct:.1f}%" if orders_pct >= 0 else f"{orders_pct:.1f}%"
        )
    },
    {
        "label": "Avg Discount",
        "value": f"{avg_discount:.1f}%"
    }
]

cols = st.columns(5)
for col, card in zip(cols, kpi_cards):
    with col:
        st.markdown(
            f"""
            <div style="
                background-color: #262730;
                border: 1px solid #3d3f4f;
                border-radius: 10px;
                padding: 20px 16px;
                text-align: center;
                min-height: 90px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            ">
                <div style="
                    font-size: 12px;
                    color: #a0aec0;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 8px;
                    font-weight: 600;
                ">{card['label']}</div>
                <div style="
                    font-size: 26px;
                    font-weight: 700;
                    color: #ffffff;
                ">{card['value']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Progress Towards Targets and Performance Heatmap side by side
col_targets, col_heatmap = st.columns(2)

with col_targets:
    section_header(
        "🎯",
        "Progress Towards Targets",
        "Tracking performance against set goals"
    )

    def progress_bar_html(label, current, target, prefix="$"):
        if target == 0:
            return ""
        pct = min((current / target) * 100, 100)
        remaining = max(target - current, 0)
        on_track_color = (
            "#48bb78" if pct >= 75
            else "#f6ad55" if pct >= 50
            else "#fc8181"
        )
        status = (
            "On track" if pct >= 75
            else "At risk" if pct >= 50
            else "Behind target"
        )

        if prefix == "$":
            current_fmt = f"USD {current:,.0f}"
            target_fmt = f"USD {target:,.0f}"
            remaining_fmt = f"USD {remaining:,.0f} remaining"
        else:
            current_fmt = f"{current:,.0f}"
            target_fmt = f"{target:,.0f}"
            remaining_fmt = f"{remaining:,.0f} remaining"

        return (
            f'<div style="margin-bottom:16px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;margin-bottom:6px;">'
            f'<span style="font-size:13px;font-weight:600;color:#ffffff;">'
            f'{label}</span>'
            f'<span style="font-size:12px;font-weight:700;'
            f'color:{on_track_color};">'
            f'{status} — {pct:.1f}%</span>'
            f'</div>'
            f'<div style="background-color:#3d3f4f;border-radius:6px;'
            f'height:10px;overflow:hidden;">'
            f'<div style="background-color:{on_track_color};width:{pct}%;'
            f'height:10px;border-radius:6px;"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;'
            f'margin-top:4px;">'
            f'<span style="font-size:11px;color:#a0aec0;">'
            f'{current_fmt} of {target_fmt} target</span>'
            f'<span style="font-size:11px;color:#a0aec0;">'
            f'{remaining_fmt}</span>'
            f'</div>'
            f'</div>'
        )

    target_html = (
        f'<div style="'
        f'background-color:#262730;'
        f'border:1px solid #3d3f4f;'
        f'border-radius:10px;'
        f'padding:20px 24px;'
        f'margin-bottom:16px;">'
        f'<div style="font-size:12px;color:#a0aec0;text-transform:uppercase;'
        f'letter-spacing:1px;font-weight:600;margin-bottom:16px;">'
        f'Progress Towards Targets</div>'
        f'{progress_bar_html("Total Revenue", total_revenue, revenue_target, "$")}'
        f'{progress_bar_html("Total Profit", total_profit, profit_target, "$")}'
        f'{progress_bar_html("Total Orders", total_orders, orders_target, "")}'
        f'</div>'
    )
    st.markdown(target_html, unsafe_allow_html=True)

    # Overall target achievement stat card
    revenue_pct_target = min((total_revenue / revenue_target * 100), 100) if revenue_target > 0 else 0
    profit_pct_target = min((total_profit / profit_target * 100), 100) if profit_target > 0 else 0
    orders_pct_target = min((total_orders / orders_target * 100), 100) if orders_target > 0 else 0

    overall_achievement = (revenue_pct_target + profit_pct_target + orders_pct_target) / 3

    achievement_color = (
        "#48bb78" if overall_achievement >= 75
        else "#f6ad55" if overall_achievement >= 50
        else "#fc8181"
    )
    achievement_status = (
        "On track" if overall_achievement >= 75
        else "At risk" if overall_achievement >= 50
        else "Behind target"
    )

    st.markdown(
        f'<div style="background-color:#262730;border:1px solid #3d3f4f;'
        f'border-left:4px solid {achievement_color};'
        f'border-radius:10px;padding:20px 24px;margin-top:4px;">'
        f'<div style="font-size:11px;color:#a0aec0;text-transform:uppercase;'
        f'letter-spacing:1px;font-weight:600;margin-bottom:12px;">'
        f'Overall Target Achievement</div>'
        f'<div style="display:flex;align-items:flex-end;'
        f'justify-content:space-between;margin-bottom:12px;">'
        f'<div style="font-size:42px;font-weight:800;color:{achievement_color};'
        f'line-height:1;">{overall_achievement:.1f}%</div>'
        f'<div style="font-size:13px;font-weight:700;color:{achievement_color};'
        f'margin-bottom:6px;">{achievement_status}</div>'
        f'</div>'
        f'<div style="background-color:#3d3f4f;border-radius:6px;'
        f'height:8px;overflow:hidden;margin-bottom:12px;">'
        f'<div style="background-color:{achievement_color};'
        f'width:{overall_achievement:.1f}%;height:8px;border-radius:6px;">'
        f'</div></div>'
        f'<div style="display:flex;justify-content:space-between;">'
        f'<div style="font-size:11px;color:#a0aec0;">Revenue: '
        f'<span style="color:#ffffff;font-weight:600;">'
        f'{revenue_pct_target:.1f}%</span></div>'
        f'<div style="font-size:11px;color:#a0aec0;">Profit: '
        f'<span style="color:#ffffff;font-weight:600;">'
        f'{profit_pct_target:.1f}%</span></div>'
        f'<div style="font-size:11px;color:#a0aec0;">Orders: '
        f'<span style="color:#ffffff;font-weight:600;">'
        f'{orders_pct_target:.1f}%</span></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col_heatmap:
    section_header(
        "🗺️",
        "Performance Heatmap",
        "Profit margin by region and product category"
    )

    heatmap_df = filtered_df.groupby(["Region", "Category"]).agg(
        Revenue=("Sales", "sum"),
        Profit=("Profit", "sum")
    ).reset_index()

    heatmap_df["Profit Margin %"] = (
        heatmap_df["Profit"] / heatmap_df["Revenue"] * 100
    ).round(1)

    heatmap_pivot = heatmap_df.pivot(
        index="Region",
        columns="Category",
        values="Profit Margin %"
    )

    fig_heatmap = px.imshow(
        heatmap_pivot,
        text_auto=True,
        color_continuous_scale=[
            [0.0, "#4a0000"],
            [0.2, "#fc8181"],
            [0.5, "#f6ad55"],
            [0.75, "#48bb78"],
            [1.0, "#00C4FF"]
        ],
        aspect="auto",
        title="Profit Margin % by Region and Product Line"
    )

    fig_heatmap.update_traces(
        texttemplate="%{z:.1f}%",
        textfont={"size": 13, "color": "white"}
    )

    fig_heatmap.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        coloraxis_showscale=False,
        xaxis=dict(
            title=dict(
                text="Product Category",
                font=dict(color="#a0aec0")
            ),
            tickfont=dict(color="white"),
            side="bottom"
        ),
        yaxis=dict(
            title=dict(
                text="Region",
                font=dict(color="#a0aec0")
            ),
            tickfont=dict(color="white")
        ),
        height=320,
        margin=dict(t=40, b=40, l=40, r=20)
    )

    with st.container(border=True):
        st.plotly_chart(fig_heatmap, use_container_width=True)

    best_combo = heatmap_df.loc[heatmap_df["Profit Margin %"].idxmax()]
    worst_combo = heatmap_df.loc[heatmap_df["Profit Margin %"].idxmin()]

    st.markdown(
        f'<div style="display:flex;gap:12px;margin-top:8px;">'
        f'<div style="flex:1;background-color:#1a2e1a;border:1px solid #2d5a2d;'
        f'border-left:4px solid #48bb78;border-radius:8px;padding:16px 18px;">'
        f'<div style="font-size:11px;color:#a0aec0;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:6px;">Best Performing Combination</div>'
        f'<div style="font-size:14px;font-weight:700;color:#48bb78;margin-bottom:4px;">'
        f'{best_combo["Region"]} — {best_combo["Category"]}</div>'
        f'<div style="font-size:13px;color:#e2e8f0;">'
        f'Profit margin: {best_combo["Profit Margin %"]:.1f}%</div>'
        f'</div>'
        f'<div style="flex:1;background-color:#2e1a1a;border:1px solid #5a2d2d;'
        f'border-left:4px solid #fc8181;border-radius:8px;padding:16px 18px;">'
        f'<div style="font-size:11px;color:#a0aec0;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:6px;">Lowest Performing Combination</div>'
        f'<div style="font-size:14px;font-weight:700;color:#fc8181;margin-bottom:4px;">'
        f'{worst_combo["Region"]} — {worst_combo["Category"]}</div>'
        f'<div style="font-size:13px;color:#e2e8f0;">'
        f'Profit margin: {worst_combo["Profit Margin %"]:.1f}%</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# Period Comparison Section
if enable_comparison:
    section_header(
        "🔄",
        "Period Comparison",
        "Side by side comparison of two selected time periods"
    )

    # Always filter from raw df to avoid main date slider interference
    period_a_df = df.copy()
    period_b_df = df.copy()

    # Apply region filter
    if selected_region != "All":
        period_a_df = period_a_df[
            period_a_df["Region"] == selected_region
        ]
        period_b_df = period_b_df[
            period_b_df["Region"] == selected_region
        ]

    # Apply category filter
    if selected_category != "All":
        period_a_df = period_a_df[
            period_a_df["Category"] == selected_category
        ]
        period_b_df = period_b_df[
            period_b_df["Category"] == selected_category
        ]

    # Apply each period's own date range independently
    import calendar

    period_a_start_forced = period_a_start.replace(day=1)
    period_a_end_forced = period_a_end.replace(
        day=calendar.monthrange(period_a_end.year, period_a_end.month)[1]
    )
    period_b_start_forced = period_b_start.replace(day=1)
    period_b_end_forced = period_b_end.replace(
        day=calendar.monthrange(period_b_end.year, period_b_end.month)[1]
    )

    period_a_df = period_a_df[
        (period_a_df["Order Date"].dt.date >= period_a_start_forced) &
        (period_a_df["Order Date"].dt.date <= period_a_end_forced)
    ].copy()

    period_b_df = period_b_df[
        (period_b_df["Order Date"].dt.date >= period_b_start_forced) &
        (period_b_df["Order Date"].dt.date <= period_b_end_forced)
    ].copy()

    # st.write(f"Period A: {period_a_start_forced} to {period_a_end_forced} — rows: {len(period_a_df)}")
    # st.write(f"Period B: {period_b_start_forced} to {period_b_end_forced} — rows: {len(period_b_df)}")

    # st.write(f"Period A: {period_a_start} to {period_a_end} — rows: {len(period_a_df)}")
    # st.write(f"Period B: {period_b_start} to {period_b_end} — rows: {len(period_b_df)}")

    # Calculate KPIs for both periods
    a_revenue = period_a_df["Sales"].sum()
    a_profit = period_a_df["Profit"].sum()
    a_orders = period_a_df["Order ID"].nunique()
    a_margin = (a_profit / a_revenue * 100) if a_revenue > 0 else 0
    a_discount = period_a_df["Discount"].mean() * 100

    b_revenue = period_b_df["Sales"].sum()
    b_profit = period_b_df["Profit"].sum()
    b_orders = period_b_df["Order ID"].nunique()
    b_margin = (b_profit / b_revenue * 100) if b_revenue > 0 else 0
    b_discount = period_b_df["Discount"].mean() * 100

    # Determine which period is more recent
    # Treat the period with the later start date as the newer period
    if period_a_start >= period_b_start:
        newer_revenue, older_revenue = a_revenue, b_revenue
        newer_profit, older_profit = a_profit, b_profit
        newer_orders, older_orders = a_orders, b_orders
        newer_margin, older_margin = a_margin, b_margin
        newer_discount, older_discount = a_discount, b_discount
        newer_label, older_label = "Period A", "Period B"
    else:
        newer_revenue, older_revenue = b_revenue, a_revenue
        newer_profit, older_profit = b_profit, a_profit
        newer_orders, older_orders = b_orders, a_orders
        newer_margin, older_margin = b_margin, a_margin
        newer_discount, older_discount = b_discount, a_discount
        newer_label, older_label = "Period B", "Period A"

    def pct_change(newer, older):
        if older == 0:
            return 0
        return ((newer - older) / older) * 100

    def comparison_row(metric, a_val, b_val, fmt, newer_val, older_val):
        if fmt == "$":
            a_fmt = f"USD {a_val:,.0f}"
            b_fmt = f"USD {b_val:,.0f}"
        elif fmt == "%":
            a_fmt = f"{a_val:.1f}%"
            b_fmt = f"{b_val:.1f}%"
        else:
            a_fmt = f"{a_val:,.0f}"
            b_fmt = f"{b_val:,.0f}"

        chg = pct_change(newer_val, older_val)
        chg_color = "#48bb78" if chg >= 0 else "#fc8181"
        chg_arrow = "▲" if chg >= 0 else "▼"
        chg_label = f"{chg_arrow} {abs(chg):.1f}%"

        return (
            f'<tr style="border-bottom:1px solid #3d3f4f;">'
            f'<td style="padding:12px 16px;color:#a0aec0;font-size:13px;'
            f'font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">'
            f'{metric}</td>'
            f'<td style="padding:12px 16px;color:#ffffff;font-size:14px;'
            f'font-weight:700;text-align:center;">{a_fmt}</td>'
            f'<td style="padding:12px 16px;color:#ffffff;font-size:14px;'
            f'font-weight:700;text-align:center;">{b_fmt}</td>'
            f'<td style="padding:12px 16px;font-size:13px;font-weight:700;'
            f'text-align:center;color:{chg_color};">{chg_label}</td>'
            f'</tr>'
        )

    period_a_label = (
        f"{period_a_start.strftime('%b %Y')} to "
        f"{period_a_end.strftime('%b %Y')}"
    )
    period_b_label = (
        f"{period_b_start.strftime('%b %Y')} to "
        f"{period_b_end.strftime('%b %Y')}"
    )

    comparison_html = (
        f'<div style="background-color:#262730;border:1px solid #3d3f4f;'
        f'border-radius:10px;overflow:hidden;margin-bottom:16px;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead>'
        f'<tr style="background-color:#1a1a2e;">'
        f'<th style="padding:14px 16px;text-align:left;color:#a0aec0;'
        f'font-size:12px;text-transform:uppercase;letter-spacing:1px;'
        f'width:25%;">Metric</th>'
        f'<th style="padding:14px 16px;text-align:center;color:#00C4FF;'
        f'font-size:12px;text-transform:uppercase;letter-spacing:1px;'
        f'width:25%;">Period A<br>'
        f'<span style="font-weight:400;font-size:11px;color:#a0aec0;">'
        f'{period_a_label}</span></th>'
        f'<th style="padding:14px 16px;text-align:center;color:#00FF9F;'
        f'font-size:12px;text-transform:uppercase;letter-spacing:1px;'
        f'width:25%;">Period B<br>'
        f'<span style="font-weight:400;font-size:11px;color:#a0aec0;">'
        f'{period_b_label}</span></th>'
        f'<th style="padding:14px 16px;text-align:center;color:#a0aec0;'
        f'font-size:12px;text-transform:uppercase;letter-spacing:1px;'
        f'width:25%;">Change ({newer_label} vs {older_label})</th>'
        f'</tr>'
        f'</thead>'
        f'<tbody>'
        f'{comparison_row("Total Revenue", a_revenue, b_revenue, "$", newer_revenue, older_revenue)}'
        f'{comparison_row("Total Profit", a_profit, b_profit, "$", newer_profit, older_profit)}'
        f'{comparison_row("Profit Margin", a_margin, b_margin, "%", newer_margin, older_margin)}'
        f'{comparison_row("Total Orders", a_orders, b_orders, "", newer_orders, older_orders)}'
        f'{comparison_row("Avg Discount", a_discount, b_discount, "%", newer_discount, older_discount)}'
        f'</tbody>'
        f'</table>'
        f'</div>'
    )

    st.markdown(comparison_html, unsafe_allow_html=True)

# Anomaly Detection
from sklearn.ensemble import IsolationForest
import numpy as np

section_header(
    "⚠️",
    "Anomaly Alerts",
    "Machine learning anomaly detection using Isolation Forest — top 3 deviations per metric"
)

def detect_anomalies_isolation_forest(series, contamination=0.1):
    if len(series) < 6:
        return np.zeros(len(series), dtype=int)
    data = series.values.reshape(-1, 1)
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100
    )
    preds = model.fit_predict(data)
    return preds

revenue_preds = detect_anomalies_isolation_forest(monthly_df["Revenue"])
profit_preds = detect_anomalies_isolation_forest(monthly_df["Profit"])

revenue_anomaly_df = monthly_df[revenue_preds == -1].copy()
profit_anomaly_df = monthly_df[profit_preds == -1].copy()

revenue_mean = monthly_df["Revenue"].mean()
profit_mean = monthly_df["Profit"].mean()

# Rank by deviation and keep top 3
revenue_anomaly_df["Deviation"] = abs(
    revenue_anomaly_df["Revenue"] - revenue_mean
)
revenue_anomaly_df = revenue_anomaly_df.nlargest(3, "Deviation")

profit_anomaly_df["Deviation"] = abs(
    profit_anomaly_df["Profit"] - profit_mean
)
profit_anomaly_df = profit_anomaly_df.nlargest(3, "Deviation")

total_anomalies = len(revenue_anomaly_df) + len(profit_anomaly_df)

if total_anomalies > 0:
    with st.expander(
        f"⚠️ {total_anomalies} anomalies detected — click to review"
    ):
        st.markdown(
            '<p style="font-size:11px;color:#a0aec0;margin-bottom:12px;">'
            'Detected using Isolation Forest (scikit-learn) — an unsupervised '
            'machine learning algorithm that identifies data points deviating '
            'significantly from normal patterns without assuming a fixed '
            'distribution.</p>',
            unsafe_allow_html=True
        )

        if not revenue_anomaly_df.empty:
            for _, row in revenue_anomaly_df.iterrows():
                direction = (
                    "spike" if row["Revenue"] > revenue_mean else "dip"
                )
                rev_value = f"{row['Revenue']:,.0f}"
                rev_avg = f"{revenue_mean:,.0f}"
                st.warning(
                    f"Revenue {direction} detected in {row['Month']} — "
                    f"USD {rev_value} vs average of USD {rev_avg}"
                )

        if not profit_anomaly_df.empty:
            for _, row in profit_anomaly_df.iterrows():
                direction = (
                    "spike" if row["Profit"] > profit_mean else "dip"
                )
                prof_value = f"{row['Profit']:,.0f}"
                prof_avg = f"{profit_mean:,.0f}"
                st.warning(
                    f"Profit {direction} detected in {row['Month']} — "
                    f"USD {prof_value} vs average of USD {prof_avg}"
                )
else:
    with st.expander("Anomaly Alerts"):
        st.success(
            "No anomalies detected in the current dataset using "
            "Isolation Forest analysis."
        )

# Trend Charts
# st.markdown("---")
section_header("📈", "Trends Over Time", "Monthly performance across revenue, profit, orders, and product mix")

# Inject CSS to style containers as cards
st.markdown("""
    <style>
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #262730;
        border: 1px solid #3d3f4f;
        border-radius: 10px;
        padding: 8px;
    }
    div[data-testid="column"]:nth-child(1) > div > div > div > div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="column"]:nth-child(2) > div > div > div > div[data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 520px;
    }
    div[data-testid="column"]:nth-child(3) > div > div > div > div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="column"]:nth-child(4) > div > div > div > div[data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 480px;
    }
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    from numpy.polynomial import polynomial as P
    import numpy as np

    monthly_df["Month_Index"] = range(len(monthly_df))
    coeffs = P.polyfit(monthly_df["Month_Index"], monthly_df["Revenue"], 1)

    last_index = monthly_df["Month_Index"].max()
    forecast_indices = [last_index + i for i in range(1, 4)]

    last_date = pd.Period(monthly_df["Month"].iloc[-1], "M")
    forecast_months = [(last_date + i).strftime("%Y-%m") for i in range(1, 4)]
    forecast_values = [P.polyval(i, coeffs) for i in forecast_indices]

    forecast_df = pd.DataFrame({
        "Month": forecast_months,
        "Revenue": forecast_values,
        "Type": "Forecast"
    })

    actual_df = monthly_df[["Month", "Revenue"]].copy()
    actual_df["Type"] = "Actual"

    combined_df = pd.concat([actual_df, forecast_df], ignore_index=True)

    fig_revenue = px.line(
        combined_df,
        x="Month",
        y="Revenue",
        color="Type",
        title="Monthly Revenue Trend with Forecast",
        markers=True,
        color_discrete_map={
            "Actual": "#00C4FF",
            "Forecast": "#FFA500"
        }
    )
    fig_revenue.update_traces(
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: $%{y:,.0f}<extra></extra>"
    )
    fig_revenue.update_layout(
        xaxis_tickangle=-45,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white"
    )

    last_actual_revenue = monthly_df["Revenue"].iloc[-1]
    avg_forecast_revenue = sum(forecast_values) / len(forecast_values)
    forecast_change_pct = ((avg_forecast_revenue - last_actual_revenue) / last_actual_revenue) * 100
    direction = "growth" if forecast_change_pct > 0 else "decline"
    arrow_color = "#48bb78" if forecast_change_pct > 0 else "#fc8181"

    with st.container(border=True):
        st.plotly_chart(fig_revenue, use_container_width=True)

with col2:
    fig_profit = px.line(
        monthly_df,
        x="Month",
        y="Profit",
        title="Monthly Profit Trend",
        markers=True,
        color_discrete_sequence=["#00FF9F"]
    )
    fig_profit.update_traces(
        hovertemplate="<b>%{x}</b><br>Profit: $%{y:,.0f}<extra></extra>"
    )
    fig_profit.update_layout(
        xaxis_tickangle=-45,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white"
    )
    with st.container(border=True):
        st.plotly_chart(fig_profit, use_container_width=True)
        # st.markdown(
        #     '<p style="font-size:13px;color:transparent;margin-top:-10px;">'
        #     'placeholder placeholder placeholder placeholder placeholder</p>',
        #     unsafe_allow_html=True
        # )

st.markdown(
    f'<div style="'
    f'background-color:#262730;'
    f'border:1px solid #3d3f4f;'
    f'border-left:4px solid {arrow_color};'
    f'border-radius:8px;'
    f'padding:12px 16px;'
    f'margin-bottom:16px;'
    f'display:flex;'
    f'align-items:center;'
    f'gap:10px;'
    f'">'
    f'<span style="font-size:20px;">{"📈" if forecast_change_pct > 0 else "📉"}</span>'
    f'<div>'
    f'<span style="font-size:11px;color:#a0aec0;text-transform:uppercase;'
    f'letter-spacing:1px;font-weight:600;">Revenue Forecast</span>'
    f'<div style="font-size:13px;color:{arrow_color};font-weight:600;margin-top:2px;">'
    f'Projected average monthly revenue for the next quarter indicates a '
    f'{abs(forecast_change_pct):.1f}% {direction} compared to the most recent month.'
    f'</div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

col3, col4 = st.columns(2)

with col3:
    fig_orders = px.bar(
        monthly_df,
        x="Month",
        y="Orders",
        title="Monthly Order Volume",
        color_discrete_sequence=["#FF6B6B"]
    )
    fig_orders.update_traces(
        hovertemplate="<b>%{x}</b><br>Orders: %{y:,}<extra></extra>"
    )
    fig_orders.update_layout(
        xaxis_tickangle=-45,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white"
    )
    with st.container(border=True):
        st.plotly_chart(fig_orders, use_container_width=True)

with col4:
    category_df = filtered_df.groupby("Category").agg(
        Revenue=("Sales", "sum")
    ).reset_index()

    fig_category = px.pie(
        category_df,
        values="Revenue",
        names="Category",
        title="Revenue by Product Line",
        color_discrete_sequence=["#00C4FF", "#00FF9F", "#FF6B6B"]
    )
    fig_category.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white"
    )
    with st.container(border=True):
        st.plotly_chart(fig_category, use_container_width=True)

# Top 5 Performers
# st.markdown("---")
section_header("🏆", "Top 5 Performers", "Leading sub-categories by revenue and profit for the current selection")

col_top1, col_top2 = st.columns(2)

with col_top1:
    with st.container(border=True):
        st.markdown(
            '<p style="font-size:12px;color:#a0aec0;text-transform:uppercase;'
            'letter-spacing:1px;font-weight:600;margin-bottom:8px;">'
            'Top 5 Sub-Categories by Revenue</p>',
            unsafe_allow_html=True
        )
        top_subcat = (
            filtered_df.groupby("Sub-Category")["Sales"]
            .sum()
            .reset_index()
            .rename(columns={"Sales": "Revenue"})
            .nlargest(5, "Revenue")
            .reset_index(drop=True)
        )
        top_subcat.index += 1
        top_subcat["Revenue"] = top_subcat["Revenue"].apply(
            lambda x: f"${x:,.0f}"
        )
        st.dataframe(
            top_subcat,
            use_container_width=True,
            column_config={
                "Sub-Category": st.column_config.TextColumn("Sub-Category"),
                "Revenue": st.column_config.TextColumn("Revenue")
            }
        )

with col_top2:
    with st.container(border=True):
        st.markdown(
            '<p style="font-size:12px;color:#a0aec0;text-transform:uppercase;'
            'letter-spacing:1px;font-weight:600;margin-bottom:8px;">'
            'Top 5 Sub-Categories by Profit</p>',
            unsafe_allow_html=True
        )
        top_profit = (
            filtered_df.groupby("Sub-Category")["Profit"]
            .sum()
            .reset_index()
            .nlargest(5, "Profit")
            .reset_index(drop=True)
        )
        top_profit.index += 1
        top_profit["Profit"] = top_profit["Profit"].apply(
            lambda x: f"${x:,.0f}"
        )
        st.dataframe(
            top_profit,
            use_container_width=True,
            column_config={
                "Sub-Category": st.column_config.TextColumn("Sub-Category"),
                "Profit": st.column_config.TextColumn("Profit")
            }
        )

def generate_kpi_commentary(kpi_name, value, context_data):
    prompt = f"""
You are a senior business analyst writing an executive KPI narrative for a 
leadership dashboard. Your job is to explain what is actually happening in 
the data, not describe what the metric is.

STRICT RULES:
- Use EXACTLY these four labels, each on its own line, nothing else
- Every sentence must reference specific numbers from the context provided
- Do not write generic business language like "the company is performing well"
- Explain the actual trend — is it accelerating, decelerating, recovering, declining?
- Identify the specific driver behind the trend if the data shows one
- Write in plain English, no markdown, no special characters
- Write all currency as plain text e.g. 2.3 million dollars not $2,297,201

WHAT IT MEANS: One sentence explaining what this specific value tells us about 
the business right now, referencing the actual number and what it implies.

TREND: One sentence describing the actual direction and momentum of this metric 
over recent months, referencing specific high and low points from the data.

NEXT STEP: One sentence recommending a specific action directly tied to what 
the trend reveals, not a generic recommendation.

KPI: {kpi_name}
Current Value: {value}
Data Context: {context_data}
Active Filters: Region: {selected_region} | Product Line: {selected_category} | 
Date Range: {start_date_forced} to {end_date_forced}

IMPORTANT FILTER CONTEXT:
{"You are analysing the FULL dataset across all regions and product lines." 
if selected_region == "All" and selected_category == "All" 
else f"You are analysing a FILTERED subset. Only include insights relevant to: "
f"{'Region: ' + selected_region if selected_region != 'All' else 'All Regions'}, "
f"{'Category: ' + selected_category if selected_category != 'All' else 'All Categories'}. "
f"Do not make claims about the overall business — only about this specific segment."}
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=350
    )

    raw = response.choices[0].message.content
    clean = raw.replace("**", "").replace("__", "").replace("*", "").replace("#", "")
    return clean

def parse_and_display_commentary(commentary, kpi_name):
    lines = commentary.strip().split("\n")
    parsed = {}

    keys = ["WHAT IT MEANS", "TREND", "NEXT STEP"]

    for line in lines:
        line = line.strip()
        for key in keys:
            if line.upper().startswith(key + ":"):
                content = line[len(key) + 1:].strip()
                parsed[key] = content
                break

    what_it_means = parsed.get("WHAT IT MEANS", "Not available")
    trend = parsed.get("TREND", "Not available")
    next_step = parsed.get("NEXT STEP", "Not available")

    card_html = (
        '<div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);"'
        ' class="kpi-card">'
        '<style>'
        '.kpi-card {'
        'border:1px solid #0f3460;'
        'border-left:4px solid #00C4FF;'
        'border-radius:8px;'
        'padding:20px 24px;'
        'margin-bottom:16px;'
        '}'
        '.kpi-title {'
        'font-size:15px;font-weight:700;color:#00C4FF;'
        'margin-bottom:14px;letter-spacing:0.5px;'
        '}'
        '.kpi-label {'
        'font-weight:600;color:#a0aec0;font-size:12px;'
        'text-transform:uppercase;letter-spacing:1px;'
        'display:block;margin-bottom:4px;'
        '}'
        '.kpi-content {'
        'color:#e2e8f0;font-size:14px;'
        'line-height:1.6;margin-bottom:12px;'
        '}'
        '</style>'
        f'<div class="kpi-title">{kpi_name}</div>'
        f'<span class="kpi-label">What it means</span>'
        f'<div class="kpi-content">{what_it_means}</div>'
        f'<span class="kpi-label">Trend</span>'
        f'<div class="kpi-content">{trend}</div>'
        f'<span class="kpi-label">Next Step</span>'
        f'<div class="kpi-content">{next_step}</div>'
        '</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)

def generate_pdf_report(kpi_data, insights):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=inch*0.75,
                            leftMargin=inch*0.75,
                            topMargin=inch*0.75,
                            bottomMargin=inch*0.75)

    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6
    )
    elements.append(Paragraph("Smart KPI Dashboard Report", title_style))

    # Subtitle
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=4
    )
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}",
        subtitle_style
    ))
    elements.append(Paragraph(
        f"Filters applied — Region: {selected_region} | Product Line: {selected_category}",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.3 * inch))

    # KPI Summary Table
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=8
    )
    elements.append(Paragraph("Key Performance Indicators", section_style))

    table_data = [["KPI", "Value"]]
    for kpi_name, kpi_value in kpi_data.items():
        table_data.append([kpi_name, kpi_value])

    table = Table(table_data, colWidths=[3.5 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f5f5f5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f5f5f5"), colors.white]),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    # AI Insights Section
    elements.append(Paragraph("AI Generated Insights", section_style))

    insight_label_style = ParagraphStyle(
        "InsightLabel",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=4,
        spaceBefore=10
    )

    insight_body_style = ParagraphStyle(
        "InsightBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#333333"),
        spaceAfter=4,
        leading=14
    )

    label_map = {
        "WHAT IT MEANS": "What it means",
        "TREND": "Trend",
        "NEXT STEP": "Next Step"
    }

    for kpi_name, commentary in insights.items():
        elements.append(Paragraph(kpi_name, insight_label_style))
        lines = commentary.strip().split("\n")
        for line in lines:
            line = line.strip()
            for key, display in label_map.items():
                if line.upper().startswith(key + ":"):
                    content = line[len(key) + 1:].strip()
                    elements.append(Paragraph(
                        f"<b>{display}:</b> {content}",
                        insight_body_style
                    ))
                    break

    doc.build(elements)
    buffer.seek(0)
    return buffer

def send_email_report(recipient_email, kpi_data, insights, pdf_buffer):
    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("SENDER_APP_PASSWORD")

    summary_lines = []
    summary_lines.append("SMART KPI DASHBOARD REPORT")
    summary_lines.append(f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}")
    summary_lines.append(f"Filters — Region: {selected_region} | Product Line: {selected_category}")
    summary_lines.append("\n--- KEY PERFORMANCE INDICATORS ---\n")

    for kpi_name, kpi_value in kpi_data.items():
        summary_lines.append(f"{kpi_name}: {kpi_value}")

    summary_lines.append("\n--- AI GENERATED INSIGHTS ---\n")

    label_map = {
        "WHAT IT MEANS": "What it means",
        "TREND": "Trend",
        "NEXT STEP": "Next Step"
    }

    for kpi_name, commentary in insights.items():
        summary_lines.append(f"\n{kpi_name}")
        summary_lines.append("-" * len(kpi_name))
        lines = commentary.strip().split("\n")
        for line in lines:
            line = line.strip()
            for key, display in label_map.items():
                if line.upper().startswith(key + ":"):
                    content = line[len(key) + 1:].strip()
                    summary_lines.append(f"{display}: {content}")
                    break

    plain_text = "\n".join(summary_lines)

    html_lines = []
    html_lines.append("""
    <html><body>
    <h2 style="color:#1a1a2e;">Smart KPI Dashboard Report</h2>
    <p style="color:#666;">Generated on {date}<br>
    Filters — Region: {region} | Product Line: {category}</p>
    <h3 style="color:#1a1a2e;">Key Performance Indicators</h3>
    <table style="border-collapse:collapse;width:60%;">
    <tr style="background:#1a1a2e;color:white;">
        <th style="padding:10px;text-align:left;">KPI</th>
        <th style="padding:10px;text-align:center;">Value</th>
    </tr>
    """.format(
        date=datetime.now().strftime('%d %B %Y at %H:%M'),
        region=selected_region,
        category=selected_category
    ))

    for i, (kpi_name, kpi_value) in enumerate(kpi_data.items()):
        bg = "#f5f5f5" if i % 2 == 0 else "#ffffff"
        html_lines.append(
            f'<tr style="background:{bg};">'
            f'<td style="padding:8px;border:1px solid #ccc;">{kpi_name}</td>'
            f'<td style="padding:8px;border:1px solid #ccc;text-align:center;">{kpi_value}</td>'
            f'</tr>'
        )

    html_lines.append("</table>")
    html_lines.append('<h3 style="color:#1a1a2e;margin-top:30px;">AI Generated Insights</h3>')

    for kpi_name, commentary in insights.items():
        html_lines.append(f'<h4 style="color:#1a1a2e;">{kpi_name}</h4>')
        html_lines.append('<table style="border-collapse:collapse;width:90%;margin-bottom:15px;">')
        lines = commentary.strip().split("\n")
        for line in lines:
            line = line.strip()
            for key, display in label_map.items():
                if line.upper().startswith(key + ":"):
                    content = line[len(key) + 1:].strip()
                    html_lines.append(
                        f'<tr>'
                        f'<td style="padding:8px;border:1px solid #ccc;'
                        f'background:#1a1a2e;color:white;width:120px;'
                        f'font-weight:bold;">{display}</td>'
                        f'<td style="padding:8px;border:1px solid #ccc;">{content}</td>'
                        f'</tr>'
                    )
                    break
        html_lines.append("</table>")

    html_lines.append("</body></html>")
    html_body = "\n".join(html_lines)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"KPI Dashboard Report — {datetime.now().strftime('%d %B %Y')}"
    msg["From"] = sender_email
    msg["To"] = recipient_email

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    pdf_buffer.seek(0)
    attachment = MIMEBase("application", "octet-stream")
    attachment.set_payload(pdf_buffer.read())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        f"attachment; filename=kpi_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    )
    msg.attach(attachment)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())

# AI Summary Section
section_header(
    "🤖", "AI Summary",
    "AI-powered insights generated from your current KPI data"
)

# Pre-generation info card
if "insights" not in st.session_state or not st.session_state.insights:
    st.markdown("""
        <div style="
            background-color:#262730;
            border:1px solid #3d3f4f;
            border-radius:10px;
            padding:20px 24px;
            margin-bottom:16px;
            display:flex;
            align-items:flex-start;
            gap:16px;
        ">
            <div style="font-size:28px;margin-top:2px;">🤖</div>
            <div>
                <div style="
                    font-size:14px;font-weight:700;
                    color:#ffffff;margin-bottom:6px;
                ">Ready to analyse your KPIs</div>
                <div style="font-size:13px;color:#a0aec0;line-height:1.6;">
                    Click the button below to generate AI-powered insights for each KPI.
                    The AI will analyse trends, flag anomalies, and recommend next steps
                    based on your current filters and date range.
                </div>
                <div style="
                    margin-top:12px;
                    display:flex;
                    gap:24px;
                ">
                    <div style="font-size:12px;color:#a0aec0;">
                        <span style="color:#00C4FF;font-weight:600;">5</span>
                        KPIs analysed
                    </div>
                    <div style="font-size:12px;color:#a0aec0;">
                        <span style="color:#00C4FF;font-weight:600;">4</span>
                        insights per KPI
                    </div>
                    <div style="font-size:12px;color:#a0aec0;">
                        <span style="color:#00C4FF;font-weight:600;">Groq</span>
                        LLaMA 3.3 70B
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

if st.button("Generate AI Insights", type="primary"):
    st.session_state.insights = {}

    top_region = filtered_df.groupby("Region")["Sales"].sum().idxmax()
    bottom_region = filtered_df.groupby("Region")["Sales"].sum().idxmin()
    top_category = filtered_df.groupby("Category")["Sales"].sum().idxmax()
    bottom_category = filtered_df.groupby("Category")["Sales"].sum().idxmin()
    top_subcat = filtered_df.groupby("Sub-Category")["Sales"].sum().idxmax()
    worst_subcat = filtered_df.groupby("Sub-Category")["Profit"].sum().idxmin()
    most_discounted = filtered_df.groupby("Sub-Category")["Discount"].mean().idxmax()
    avg_order_value = total_revenue / total_orders if total_orders else 0

    # Full monthly trend data
    monthly_revenue_trend = monthly_df[["Month", "Revenue"]].to_dict("records")
    monthly_profit_trend = monthly_df[["Month", "Profit"]].to_dict("records")
    monthly_orders_trend = monthly_df[["Month", "Orders"]].to_dict("records")

    # Best and worst months
    best_revenue_month = monthly_df.loc[monthly_df["Revenue"].idxmax(), "Month"]
    worst_revenue_month = monthly_df.loc[monthly_df["Revenue"].idxmin(), "Month"]
    best_profit_month = monthly_df.loc[monthly_df["Profit"].idxmax(), "Month"]
    worst_profit_month = monthly_df.loc[monthly_df["Profit"].idxmin(), "Month"]

    # Month on month change for most recent period
    if len(monthly_df) >= 2:
        last_month_revenue = monthly_df["Revenue"].iloc[-1]
        prev_month_revenue = monthly_df["Revenue"].iloc[-2]
        last_month = monthly_df["Month"].iloc[-1]
        prev_month = monthly_df["Month"].iloc[-2]
        mom_revenue_change = (
            ((last_month_revenue - prev_month_revenue) / prev_month_revenue * 100)
            if prev_month_revenue else 0
        )
    else:
        mom_revenue_change = 0
        last_month = "N/A"
        prev_month = "N/A"

    # Category and region breakdowns
    region_breakdown = (
        filtered_df.groupby("Region")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
        .to_dict("records")
    )
    category_breakdown = (
        filtered_df.groupby("Category")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
        .to_dict("records")
    )
    subcat_breakdown = (
        filtered_df.groupby("Sub-Category")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
        .nlargest(5, "Revenue")
        .to_dict("records")
    )

    # Discount impact
    high_discount_df = filtered_df[filtered_df["Discount"] > 0.2]
    high_discount_revenue = high_discount_df["Sales"].sum()
    high_discount_profit = high_discount_df["Profit"].sum()

    kpi_jobs = [
        {
            "name": "Total Revenue",
            "value": f"USD {total_revenue:,.0f}",
            "context": (
                f"Full monthly revenue trend from oldest to most recent: "
                f"{monthly_revenue_trend}. "
                f"Best revenue month: {best_revenue_month}. "
                f"Worst revenue month: {worst_revenue_month}. "
                f"Most recent month {last_month}: USD {last_month_revenue:,.0f}. "
                f"Previous month {prev_month}: USD {prev_month_revenue:,.0f}. "
                f"Month on month change: {mom_revenue_change:.1f}%. "
                f"Top region: {top_region}. Bottom region: {bottom_region}. "
                f"Top category: {top_category}. "
                f"Regional breakdown: {region_breakdown}. "
                f"Category breakdown: {category_breakdown}. "
                f"Top 5 sub-categories: {subcat_breakdown}."
            )
        },
        {
            "name": "Total Profit",
            "value": f"USD {total_profit:,.0f}",
            "context": (
                f"Full monthly profit trend: {monthly_profit_trend}. "
                f"Best profit month: {best_profit_month}. "
                f"Worst profit month: {worst_profit_month}. "
                f"Total revenue: USD {total_revenue:,.0f}. "
                f"Profit margin: {profit_margin:.1f}%. "
                f"Average discount applied: {avg_discount:.1f}%. "
                f"Revenue from orders with over 20 percent discount: "
                f"USD {high_discount_revenue:,.0f}. "
                f"Profit from those same orders: USD {high_discount_profit:,.0f}. "
                f"Worst sub-category by profit: {worst_subcat}. "
                f"Category breakdown by profit: {category_breakdown}. "
                f"Bottom region: {bottom_region}."
            )
        },
        {
            "name": "Profit Margin",
            "value": f"{profit_margin:.1f}%",
            "context": (
                f"Total revenue: USD {total_revenue:,.0f}. "
                f"Total profit: USD {total_profit:,.0f}. "
                f"Average discount: {avg_discount:.1f}%. "
                f"Most discounted sub-category: {most_discounted}. "
                f"Revenue from heavily discounted orders: "
                f"USD {high_discount_revenue:,.0f}. "
                f"Profit from heavily discounted orders: "
                f"USD {high_discount_profit:,.0f}. "
                f"Bottom category by profit: {bottom_category}. "
                f"Category margin breakdown: {category_breakdown}. "
                f"Regional margin breakdown: {region_breakdown}."
            )
        },
        {
            "name": "Total Orders",
            "value": f"{total_orders:,}",
            "context": (
                f"Full monthly orders trend: {monthly_orders_trend}. "
                f"Average order value: USD {avg_order_value:,.0f}. "
                f"Total revenue: USD {total_revenue:,.0f}. "
                f"Top region by revenue: {top_region}. "
                f"Top category by revenue: {top_category}. "
                f"Top 5 sub-categories by revenue: {subcat_breakdown}. "
                f"Best revenue month: {best_revenue_month}. "
                f"Most recent month orders: "
                f"{monthly_df['Orders'].iloc[-1] if len(monthly_df) > 0 else 0}."
            )
        },
        {
            "name": "Average Discount",
            "value": f"{avg_discount:.1f}%",
            "context": (
                f"Average discount across all orders: {avg_discount:.1f}%. "
                f"Most discounted sub-category: {most_discounted}. "
                f"Orders with over 20 percent discount — "
                f"revenue: USD {high_discount_revenue:,.0f}, "
                f"profit: USD {high_discount_profit:,.0f}. "
                f"Total profit: USD {total_profit:,.0f}. "
                f"Profit margin: {profit_margin:.1f}%. "
                f"Category breakdown: {category_breakdown}. "
                f"The relationship between discount rate and profit margin "
                f"should be the central focus of this insight."
            )
        }
    ]

    progress_bar = st.progress(0, text="Starting AI analysis...")

    for i, job in enumerate(kpi_jobs):
        progress_bar.progress(
            i / len(kpi_jobs),
            text=f"Analysing {job['name']}... ({i + 1} of {len(kpi_jobs)})"
        )
        insight = generate_kpi_commentary(
            job["name"], job["value"], job["context"]
        )
        st.session_state.insights[job["name"]] = insight

    progress_bar.progress(1.0, text="Analysis complete.")

    st.markdown(
        f'<div style="background-color:#1a2e1a;border:1px solid #2d5a2d;'
        f'border-left:4px solid #48bb78;border-radius:8px;'
        f'padding:12px 16px;margin:16px 0;'
        f'display:flex;align-items:center;gap:12px;">'
        f'<span style="font-size:18px;">✅</span>'
        f'<div>'
        f'<div style="font-size:13px;font-weight:700;color:#48bb78;">'
        f'Analysis complete</div>'
        f'<div style="font-size:12px;color:#a0aec0;margin-top:2px;">'
        f'Generated at {datetime.now().strftime("%H:%M on %d %b %Y")} — '
        f'Region: {selected_region} | '
        f'Product Line: {selected_category}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# Display stored insights
if "insights" in st.session_state and st.session_state.insights:
    for kpi_name, insight in st.session_state.insights.items():
        parse_and_display_commentary(insight, kpi_name)

# Export Report Section
if "insights" in st.session_state and st.session_state.insights:
    # st.markdown("---")
    section_header("📤", "Export Report", "Download a PDF report or send the summary directly to an email address")

    kpi_data = {
        "Total Revenue": f"USD {total_revenue:,.0f}",
        "Total Profit": f"USD {total_profit:,.0f}",
        "Profit Margin": f"{profit_margin:.1f}%",
        "Total Orders": f"{total_orders:,}",
        "Average Discount": f"{avg_discount:.1f}%"
    }

    export_option = st.radio(
        "Choose export format",
        options=["PDF Report", "Email Summary"],
        horizontal=True
    )

    if export_option == "PDF Report":
        pdf_buffer = generate_pdf_report(kpi_data, st.session_state.insights)
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name=f"kpi_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

    elif export_option == "Email Summary":
        with st.form("email_form"):
            recipient = st.text_input(
                "Recipient email address",
                placeholder="Enter the email address to send the report to"
            )
            submitted = st.form_submit_button("Send Email Report")

            if submitted:
                if recipient:
                    try:
                        pdf_buffer_email = generate_pdf_report(
                            kpi_data, st.session_state.insights
                        )
                        send_email_report(
                            recipient,
                            kpi_data,
                            st.session_state.insights,
                            pdf_buffer_email
                        )
                        st.success(f"Report sent successfully to {recipient}")
                    except Exception as e:
                        st.error(f"Failed to send email: {str(e)}")
                else:
                    st.warning("Please enter a recipient email address before submitting.")

# Data Preview
section_header(
    "🗃️",
    "Data Preview",
    "Sample of the underlying dataset for the current filters and date range"
)

with st.expander("Click to view raw data"):
    st.markdown(
        f'<p style="font-size:12px;color:#a0aec0;margin-bottom:8px;">'
        f'Showing {min(10, len(filtered_df))} of {len(filtered_df):,} records '
        f'for the current selection.</p>',
        unsafe_allow_html=True
    )

    preview_df = filtered_df[[
        "Order Date",
        "Region",
        "Category",
        "Sub-Category",
        "Sales",
        "Profit",
        "Quantity",
        "Discount"
    ]].copy()

    preview_df["Order Date"] = preview_df["Order Date"].dt.strftime("%d %b %Y")
    preview_df["Sales"] = preview_df["Sales"].apply(lambda x: f"${x:,.2f}")
    preview_df["Profit"] = preview_df["Profit"].apply(lambda x: f"${x:,.2f}")
    preview_df["Discount"] = preview_df["Discount"].apply(
        lambda x: f"{x*100:.0f}%"
    )

    st.dataframe(
        preview_df.head(10),
        use_container_width=True,
        column_config={
            "Order Date": st.column_config.TextColumn("Order Date"),
            "Region": st.column_config.TextColumn("Region"),
            "Category": st.column_config.TextColumn("Category"),
            "Sub-Category": st.column_config.TextColumn("Sub-Category"),
            "Sales": st.column_config.TextColumn("Revenue"),
            "Profit": st.column_config.TextColumn("Profit"),
            "Quantity": st.column_config.NumberColumn("Qty"),
            "Discount": st.column_config.TextColumn("Discount")
        }
    )

    st.markdown(
        f'<p style="font-size:11px;color:#a0aec0;margin-top:8px;">'
        f'Dataset: Sample Superstore | '
        f'Total records: {len(df):,} | '
        f'Date range: {df["Order Date"].min().strftime("%b %Y")} '
        f'to {df["Order Date"].max().strftime("%b %Y")}'
        f'</p>',
        unsafe_allow_html=True
    )

# Natural Language Q&A
section_header(
    "💬",
    "Ask the Data",
    "Type any question about the current dataset and get an AI-powered answer"
)

# Initialise chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(
            f'<div style="'
            f'background-color:#1e2a3a;'
            f'border:1px solid #2d4a6a;'
            f'border-left:4px solid #00C4FF;'
            f'border-radius:8px;'
            f'padding:12px 16px;'
            f'margin-bottom:8px;'
            f'display:flex;gap:12px;align-items:flex-start;">'
            f'<span style="font-size:16px;">🧑‍💼</span>'
            f'<div style="font-size:14px;color:#e2e8f0;">{message["content"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div style="'
            f'background-color:#262730;'
            f'border:1px solid #3d3f4f;'
            f'border-left:4px solid #48bb78;'
            f'border-radius:8px;'
            f'padding:12px 16px;'
            f'margin-bottom:8px;'
            f'display:flex;gap:12px;align-items:flex-start;">'
            f'<span style="font-size:16px;">🤖</span>'
            f'<div style="font-size:14px;color:#e2e8f0;line-height:1.6;">'
            f'{message["content"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

# Build dataset context for the AI
def build_data_context():
    top_region = filtered_df.groupby("Region")["Sales"].sum().idxmax()
    bottom_region = filtered_df.groupby("Region")["Sales"].sum().idxmin()
    top_category = filtered_df.groupby("Category")["Sales"].sum().idxmax()
    top_subcat = filtered_df.groupby("Sub-Category")["Sales"].sum().idxmax()
    worst_subcat_profit = filtered_df.groupby(
        "Sub-Category"
    )["Profit"].sum().idxmin()
    avg_order_value = total_revenue / total_orders if total_orders else 0
    most_discounted = filtered_df.groupby(
        "Sub-Category"
    )["Discount"].mean().idxmax()

    region_breakdown = (
        filtered_df.groupby("Region")["Sales"]
        .sum()
        .reset_index()
        .to_dict("records")
    )
    category_breakdown = (
        filtered_df.groupby("Category")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
        .to_dict("records")
    )

    # Full monthly breakdown
    full_monthly = monthly_df[["Month", "Revenue", "Profit", "Orders"]].to_dict("records")

    # Yearly summary
    filtered_df["Year"] = filtered_df["Order Date"].dt.year
    yearly_summary = (
        filtered_df.groupby("Year")
        .agg(
            Revenue=("Sales", "sum"),
            Profit=("Profit", "sum"),
            Orders=("Order ID", "nunique"),
            Avg_Discount=("Discount", "mean")
        )
        .reset_index()
    )
    yearly_summary["Profit_Margin"] = (
        yearly_summary["Profit"] / yearly_summary["Revenue"] * 100
    ).round(1)
    yearly_dict = yearly_summary.to_dict("records")

    # Yearly category breakdown
    yearly_category = (
        filtered_df.groupby(["Year", "Category"])
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
        .to_dict("records")
    )

    # Yearly region breakdown
    yearly_region = (
        filtered_df.groupby(["Year", "Region"])
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
        .to_dict("records")
    )

    # Worst performing months
    worst_profit_months = (
        monthly_df.nsmallest(5, "Profit")[["Month", "Revenue", "Profit"]]
        .to_dict("records")
    )
    best_profit_months = (
        monthly_df.nlargest(5, "Profit")[["Month", "Revenue", "Profit"]]
        .to_dict("records")
    )

    # Sub-category profitability
    subcat_profit = (
        filtered_df.groupby("Sub-Category")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
    )
    subcat_profit["Margin"] = (
        subcat_profit["Profit"] / subcat_profit["Revenue"] * 100
    ).round(1)
    subcat_profit_dict = subcat_profit.sort_values(
        "Profit", ascending=True
    ).head(5).to_dict("records")

    return f"""
You are a concise, data-driven business analyst assistant embedded in an
operational KPI dashboard. A senior leadership reviewer is asking you questions
about their business performance data.

STRICT RESPONSE RULES:
- Answer in 2 to 4 sentences maximum. Never exceed this.
- Always reference specific numbers from the data provided. Never give vague answers.
- Write in plain business English. No bullet points, no markdown, no headers.
- If asked about a specific year or month, look it up in the yearly or monthly
  data provided and answer with the exact figures.
- Never say the data does not contain year or month specific information.
  It always does — look harder.
- Never speculate beyond what the data shows.
- Always end with one specific actionable recommendation tied to the data.

CURRENT FILTERS:
Region: {selected_region}
Product Line: {selected_category}
Date Range: {start_date_forced} to {end_date_forced}

OVERALL SUMMARY METRICS:
Total Revenue: USD {total_revenue:,.0f}
Total Profit: USD {total_profit:,.0f}
Profit Margin: {profit_margin:.1f}%
Total Orders: {total_orders:,}
Average Order Value: USD {avg_order_value:,.0f}
Average Discount: {avg_discount:.1f}%

YEARLY PERFORMANCE SUMMARY:
{yearly_dict}

YEARLY PERFORMANCE BY CATEGORY:
{yearly_category}

YEARLY PERFORMANCE BY REGION:
{yearly_region}

FULL MONTHLY BREAKDOWN:
{full_monthly}

BEST 5 PROFIT MONTHS:
{best_profit_months}

WORST 5 PROFIT MONTHS:
{worst_profit_months}

REGIONAL PERFORMANCE:
Top region by revenue: {top_region}
Lowest region by revenue: {bottom_region}
Regional breakdown: {region_breakdown}

PRODUCT PERFORMANCE:
Top category: {top_category}
Top sub-category by revenue: {top_subcat}
Worst sub-category by profit: {worst_subcat_profit}
Most discounted sub-category: {most_discounted}
Category breakdown: {category_breakdown}

BOTTOM 5 SUB-CATEGORIES BY PROFIT:
{subcat_profit_dict}
"""

def ask_data_question(question, data_context):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": data_context},
            {"role": "user", "content": question}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content

# Chat input
user_question = st.chat_input(
    "Ask a question about your data - e.g. Why did profit drop in 2015? "
    "Which region has the best margin?"
)

if user_question:
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_question
    })

    with st.spinner("Analysing your question..."):
        data_context = build_data_context()
        answer = ask_data_question(user_question, data_context)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer
    })

    st.rerun()

# Clear chat button
if st.session_state.chat_history:
    if st.button("Clear conversation", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()