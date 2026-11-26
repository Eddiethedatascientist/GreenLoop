import os

import pandas as pd
import plotly.express as px
import streamlit as st

from cloud_database import (
    get_activity_data,
    get_activity_per_material,
    get_best_material,
    get_person_summary,
    get_personal_details,
    get_personal_histories,
    get_recent_sorting,
    get_waste_decomposition,
    ranking_database,
    search_participants,
)

st.set_page_config(
    page_title="GreenLoop Sorting and Recycle Leaderboard",
    page_icon="♻️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# ESG pilot assumptions (same values as the local dashboard)
# ---------------------------------------------------------------------------
WEIGHT_KG = {"plastic": 0.03, "metal": 0.04, "paper": 0.02, "other": 0.015}
EMISSION_FACTOR = {"plastic": 1.06, "metal": 5.5, "paper": 3.6, "other": 1.0}


def co2_avoided(material, quantity):
    """Estimated CO2e (kg) avoided for `quantity` items of `material`."""
    if material not in WEIGHT_KG:
        return 0.0
    return quantity * WEIGHT_KG[material] * EMISSION_FACTOR[material]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
IMAGE_DIRS = ["Images", "."]  # look in Images/ first, then the repo root


def show_image(file_name, caption):
    """Display an image if it exists (paths are case-sensitive on Linux!)."""
    for folder in IMAGE_DIRS:
        path = os.path.join(folder, file_name)
        if os.path.exists(path):
            st.image(path, caption=caption, width="stretch")
            return
    st.warning(f"Image not found: {file_name}")


def line_chart(rows, x_label, y_label, title, key):
    """Line chart from a list of (x, y) rows, with an empty-data guard."""
    if not rows:
        st.info("No data yet.")
        return
    df = pd.DataFrame(rows, columns=[x_label, y_label])
    fig = px.line(df, x=x_label, y=y_label, markers=True, title=title)
    st.plotly_chart(fig, width="stretch", key=key)


def esg_line_chart(rows, title, key):
    """Line chart of estimated CO2e per material from (period, material, qty)."""
    data = [
        (period, material, co2_avoided(material, qty))
        for period, material, qty in rows
        if material in WEIGHT_KG
    ]
    if not data:
        st.info("No data yet.")
        return
    df = pd.DataFrame(data, columns=["Date", "Waste", "CO2"])
    fig = px.line(df, x="Date", y="CO2", color="Waste", markers=True, title=title)
    st.plotly_chart(fig, width="stretch", key=key)


# ---------------------------------------------------------------------------
# Sidebar + header
# ---------------------------------------------------------------------------
st.sidebar.title("⚙️ Control panel")
st.sidebar.text("Status: Online")
if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

st.title("🌱 GreenLoop Smart AI-powered Recycling System")
st.markdown(
    "*May the Darkness Be With You 2026 — Track 3: Connected Commons & Shared Loops*"
)

tab1, tab2, tab3 = st.tabs([
    "🏆 Leaderboard",
    "🔬 Model & Science Metrics",
    "🏢 Trash Data & ESG Analytics",
])


# ---------------------------------------------------------------------------
# TAB 1: LEADERBOARD
# ---------------------------------------------------------------------------
@st.fragment(run_every="15s")
def leaderboard_section():
    st.subheader("Leaderboard")
    rankings = ranking_database()
    if not rankings:
        st.info("No sorting records available yet.")
        return

    df = pd.DataFrame(
        rankings,
        columns=["Participants", "Sessions", "Total item sorted", "Green points"],
    )
    df.index = range(1, len(df) + 1)
    df.index.name = "Rank"
    st.dataframe(df, width="stretch")


with tab1:
    st.header("Leaderboard & real-time sorting results")
    st.info(
        "Live sorting happens at the GreenLoop station. "
        "This page shows the results as they are saved."
    )
    leaderboard_section()


# ---------------------------------------------------------------------------
# TAB 2: MODEL & SCIENCE METRICS
# ---------------------------------------------------------------------------
with tab2:
    st.header("🔬 Model & Science Metrics")
    st.caption("YOLOv8 Computer Vision AI training's indices and performances")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("mAP @ 0.50", "79.93%", delta="Epoch 50")
    c2.metric("mAP @ 0.50:0.95", "59.68%", delta="High Strictness")
    c3.metric("Precision", "82.15%", delta="Low False Positive")
    c4.metric("Recall", "75.28%", delta="Robust Detection")

    st.markdown("---")

    sub1, sub2, sub3, sub4 = st.tabs([
        "🎯 Confusion Matrix",
        "📈 Training Loss & Curves",
        "🏷️ Dataset Labels",
        "🖼️ Training Samples",
    ])

    with sub1:
        st.markdown("#### Confusion Matrix")
        col_a, col_b = st.columns(2)
        with col_a:
            show_image("confusion_matrix_normalized.png", "Normalized Confusion Matrix")
        with col_b:
            show_image("confusion_matrix.png", "Original Confusion Matrix")

    with sub2:
        st.markdown("#### Training curves and statistics")
        show_image("results.png", "Loss and training statistics and curves")
        col_a, col_b = st.columns(2)
        with col_a:
            show_image("BoxPR_curve.png", "Precision-Recall curve")
            show_image("BoxP_curve.png", "Precision curve")
        with col_b:
            show_image("BoxF1_curve.png", "F1 confidence curve")
            show_image("BoxR_curve.png", "Recall curve")

    with sub3:
        st.markdown("#### Class labeling")
        show_image("labels.jpg", "Instance labeling and classification")

    with sub4:
        st.markdown("#### Some training samples")
        col_a, col_b = st.columns(2)
        with col_a:
            show_image("train_batch0.jpg", "train_batch0")
        with col_b:
            show_image("train_batch1.jpg", "train_batch1")


# ---------------------------------------------------------------------------
# TAB 3: ANALYTICS
# ---------------------------------------------------------------------------
def show_personal_analytics(person_id, name, total_point):
    """Everything about one participant."""
    sessions, total_items, breakdown = get_person_summary(person_id)

    st.success("Participant found!")
    st.subheader("Participant profile")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.metric("Username", name)
    with col2:
        with st.container(border=True):
            st.metric("User ID", person_id)

    st.markdown("---")
    st.subheader("01. Personal performance overview")
    top_material = breakdown[0][0].capitalize() if breakdown else "—"
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.metric("Total items", total_items, help="Total items sorted")
    with col2:
        with st.container(border=True):
            st.metric("Total sessions", sessions, help="Total sessions started")
    with col3:
        with st.container(border=True):
            st.metric("Green points", total_point, help="Total points acquired")
    with col4:
        with st.container(border=True):
            st.metric("Top material", top_material, help="Top sorted material")

    st.markdown("---")
    st.subheader("02. Personal waste decomposition")
    if breakdown and total_items > 0:
        decomposition = pd.DataFrame(
            [
                {
                    "Material": material.capitalize(),
                    "Quantity": quantity,
                    "Percentage": round(quantity / total_items * 100, 1),
                }
                for material, quantity in breakdown
            ]
        )
        fig = px.bar(
            decomposition,
            x="Quantity",
            y="Material",
            orientation="h",
            text="Percentage",
        )
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig, width="stretch", key=f"person_decomp_{person_id}")
    else:
        st.info("This participant has not sorted any items yet.")

    st.markdown("---")
    st.subheader("03. Personal sorting trends")
    p_daily, p_weekly, p_monthly = get_personal_details(person_id)
    t_daily, t_weekly, t_monthly = st.tabs(["Daily", "Weekly", "Monthly"])
    with t_daily:
        line_chart(p_daily, "Period", "Quantity", "Daily sorting graph", f"p_daily_{person_id}")
    with t_weekly:
        line_chart(p_weekly, "Period", "Quantity", "Weekly sorting graph", f"p_weekly_{person_id}")
    with t_monthly:
        line_chart(p_monthly, "Period", "Quantity", "Monthly sorting graph", f"p_monthly_{person_id}")

    st.markdown("---")
    st.subheader("04. Personal sorting records")
    records = get_personal_histories(person_id)
    if records:
        df = pd.DataFrame(
            records, columns=["Time start", "Time end", "Material", "Quantity"]
        )
        st.dataframe(df, width="stretch")
    else:
        st.info("No sorting records yet.")


with tab3:
    s1, s2, s3 = st.tabs([
        "📊 Overview",
        "👤 Personal analytics",
        "🌱 ESG & Impact",
    ])

    # ----- Overview -----
    with s1:
        st.header("📊 GreenLoop Overview")
        st.caption("Organisation recycling performances and participation")

        ranking = ranking_database()
        if not ranking:
            st.info("No sorting records available yet.")
        else:
            total_people = len(ranking)
            total_sessions = sum(row[1] for row in ranking)
            total_quantity = sum(row[2] for row in ranking)
            total_point_issued = sum(row[3] for row in ranking)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                with st.container(border=True):
                    st.metric("Total item sorted", total_quantity)
            with col2:
                with st.container(border=True):
                    st.metric("Total sessions", total_sessions)
            with col3:
                with st.container(border=True):
                    st.metric("Total participants", total_people)
            with col4:
                with st.container(border=True):
                    st.metric("Total point issued", total_point_issued)

            st.markdown("---")
            st.subheader("01. Waste decomposition")
            trash_summary = get_waste_decomposition()
            if trash_summary:
                waste_df = pd.DataFrame(trash_summary, columns=["Waste type", "Quantity"])
                st.dataframe(waste_df, width="stretch")
                fig = px.pie(waste_df, names="Waste type", values="Quantity", hole=0.5)
                st.plotly_chart(fig, width="stretch", key="overview_pie")
            else:
                st.info("No waste data yet.")

            st.markdown("---")
            st.subheader("02. Sorting activities")
            daily_data, weekly_data, monthly_data = get_activity_data()
            t_daily, t_weekly, t_monthly = st.tabs(["Daily", "Weekly", "Monthly"])
            with t_daily:
                line_chart(daily_data, "Period", "Total quantity", "Daily sorting activity", "act_daily")
            with t_weekly:
                line_chart(weekly_data, "Period", "Total quantity", "Weekly sorting activity", "act_weekly")
            with t_monthly:
                line_chart(monthly_data, "Period", "Total quantity", "Monthly sorting activity", "act_monthly")

            st.markdown("---")
            st.subheader("03. Sorting performance insights")
            average = round(total_quantity / total_sessions, 3) if total_sessions else 0
            best_material = get_best_material() or "—"
            best_person, best_point = ranking[0][0], ranking[0][3]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                with st.container(border=True):
                    st.metric("Average items / session", average)
            with col2:
                with st.container(border=True):
                    st.metric("Most sorted material", best_material)
            with col3:
                with st.container(border=True):
                    st.metric("Best participant", best_person)
            with col4:
                with st.container(border=True):
                    st.metric("Highest green points", best_point)

            st.markdown("---")
            st.subheader("04. Recent sorting activities")
            recent = get_recent_sorting()
            if recent:
                recent_df = pd.DataFrame(
                    recent, columns=["Username", "Time start", "Time end"]
                )
                st.dataframe(recent_df, width="stretch")
            else:
                st.info("No recent sessions.")

    # ----- Personal analytics -----
    with s2:
        st.header("👤 Personal analytics")
        keyword = st.text_input(
            "Search participant", placeholder="Enter participant name..."
        )

        if keyword.strip():
            matches = search_participants(keyword.strip())
            if not matches:
                st.warning("Participant not found! Please check the spelling and try again.")
            else:
                options = {
                    f"{name} (ID {pid})": (pid, name, points)
                    for pid, name, points in matches
                }
                if len(options) > 1:
                    choice = st.selectbox(
                        "Several participants match, choose one", list(options)
                    )
                else:
                    choice = next(iter(options))
                person_id, name, total_point = options[choice]
                show_personal_analytics(person_id, name, total_point)
        else:
            st.info("Type a participant name to see their analytics.")

    # ----- ESG & Impact -----
    with s3:
        st.header("🌱 Environmental Impact Assessment")
        st.caption("Estimated environmental impact based on GreenLoop pilot data")
        st.warning(
            "PILOT ESTIMATES | Figures are preliminary estimates, "
            "not verified environmental measurements."
        )

        waste_summary = get_waste_decomposition()
        if not waste_summary:
            st.info("No sorting data yet.")
        else:
            st.markdown("---")
            st.subheader("01. Environmental impact through numbers")

            esg_by_material = {
                material: co2_avoided(material, qty)
                for material, qty in waste_summary
                if material in WEIGHT_KG
            }
            total_emission = sum(esg_by_material.values())
            count_total = sum(qty for _, qty in waste_summary)
            total_weight = sum(
                qty * WEIGHT_KG[material]
                for material, qty in waste_summary
                if material in WEIGHT_KG
            )
            average_weight = round(total_weight / count_total, 3) if count_total else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                with st.container(border=True):
                    st.metric(
                        "Potential CO2e avoided",
                        f"{total_emission:.2f} kg",
                        help="Estimated using pilot assumptions",
                    )
            with col2:
                with st.container(border=True):
                    st.metric(
                        "Average kg per item",
                        average_weight,
                        help="Average weight per a recycled item",
                    )
            with col3:
                with st.container(border=True):
                    st.metric(
                        "Total item sorted",
                        count_total,
                        help="Actual recorded count",
                    )
            with col4:
                with st.container(border=True):
                    st.metric(
                        "Material categories",
                        len(waste_summary),
                        help="AI classification categories",
                    )

            st.markdown("---")
            st.subheader("02. Environmental impact by material")
            df_impact = pd.DataFrame(
                list(esg_by_material.items()),
                columns=["Material", "Potential CO2e (kg)"],
            )
            fig = px.bar(
                df_impact,
                x="Material",
                y="Potential CO2e (kg)",
                color="Material",
                title="Estimated CO2e avoided by material",
            )
            st.plotly_chart(fig, width="stretch", key="esg_by_material")

            st.markdown("---")
            st.subheader("03. Environmental changes over time")
            m_daily, m_weekly, m_monthly = get_activity_per_material()
            t_daily, t_weekly, t_monthly = st.tabs(["Daily", "Weekly", "Monthly"])
            with t_daily:
                esg_line_chart(m_daily, "Estimated CO2 avoided daily per material", "esg_daily")
            with t_weekly:
                esg_line_chart(m_weekly, "Estimated CO2 avoided weekly per material", "esg_weekly")
            with t_monthly:
                esg_line_chart(m_monthly, "Estimated CO2 avoided monthly per material", "esg_monthly")


st.divider()
st.caption("GreenLoop | AI-powered Smart Waste Sorting System")
