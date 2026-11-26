import streamlit as st
import pandas as pd
import os
import plotly.express as px

from cloud_database import *

st.set_page_config(
    page_title="GreenLoop Online Dashboard",
    page_icon="♻️",
    layout="wide"
)

st.title("♻️ GreenLoop")
st.subheader("Connected Commons & Shared Loops")
st.caption("Online Environmental Intelligence Dashboard")

st.divider()


def show_image(image_name, caption):
    """Display a training image if it exists."""
    image_path = os.path.join("Images", image_name)

    if os.path.exists(image_path):
        st.image(image_path, caption=caption, use_container_width=True)
    else:
        st.warning(f"Image not found: {image_path}")


tab1, tab2 = st.tabs([
    "🧠 Model & Science Metrics",
    "♻️ Waste Data & ESG Analytics"
])


# =========================================================
# TAB 1: MODEL & SCIENCE METRICS
# =========================================================

with tab1:

    st.header("🧠 Computer Vision Performance")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("mAP50", "79.93%")
    col2.metric("mAP50-95", "59.68%")
    col3.metric("Precision", "82.15%")
    col4.metric("Recall", "75.28%")

    st.divider()

    st.subheader("Model Training Results")

    col1, col2 = st.columns(2)

    with col1:
        show_image("results.png", "Training Results")
        show_image("confusion_matrix.png", "Confusion Matrix")

    with col2:
        show_image(
            "confusion_matrix_normalized.png",
            "Normalized Confusion Matrix"
        )
        show_image("labels.jpg", "Dataset Labels")

    st.divider()

    st.subheader("Performance Curves")

    col1, col2 = st.columns(2)

    with col1:
        show_image("BoxPR_curve.png", "Precision-Recall Curve")
        show_image("BoxP_curve.png", "Precision Curve")

    with col2:
        show_image("BoxF1_curve.png", "F1 Curve")
        show_image("BoxR_curve.png", "Recall Curve")

    st.divider()

    st.subheader("Training Samples")

    col1, col2 = st.columns(2)

    with col1:
        show_image("train_batch0.jpg", "Training Batch 0")

    with col2:
        show_image("train_batch1.jpg", "Training Batch 1")



with tab2:

    st.header("♻️ Waste Data & ESG Analytics")

    s1, s2, s3 = st.tabs([
        "Overview",
        "Personal Analytics",
        "ESG & Impact"
    ])


    with s1:

        @st.fragment(run_every="10s")
        def overview_section():
            ranking = ranking_database()
            waste_data = get_waste_decomposition()
            best_material = get_best_material()

            if not ranking:
                st.info("No sorting records available yet.")
                return

            df = pd.DataFrame(
                ranking,
                columns=[
                    "Person ID",
                    "Name",
                    "Points",
                    "Sessions",
                    "Items"
                ]
            )

            total_people = len(df)
            total_points = int(df["Points"].sum())
            total_items = int(df["Items"].sum())

            col1, col2, col3 = st.columns(3)

            col1.metric("Participants", total_people)
            col2.metric("Green Points", total_points)
            col3.metric("Items Sorted", total_items)

            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Waste Composition")

                if waste_data:
                    waste_df = pd.DataFrame(
                        waste_data,
                        columns=["Material", "Quantity"]
                    )

                    fig = px.pie(
                        waste_df,
                        names="Material",
                        values="Quantity",
                        hole=0.45
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

            with col2:
                st.subheader("Most Sorted Material")

                if best_material:
                    st.metric(
                        best_material[0],
                        int(best_material[1])
                    )
                else:
                    st.info("No material data available.")

            st.divider()

            st.subheader("Daily Sorting Activity")

            daily_data = get_activity_data("daily")

            if daily_data:
                daily_df = pd.DataFrame(
                    daily_data,
                    columns=["Date", "Quantity"]
                )

                fig = px.bar(
                    daily_df,
                    x="Date",
                    y="Quantity",
                    title="Items Sorted Per Day"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            st.subheader("Weekly Sorting Activity")

            weekly_data = get_activity_data("weekly")

            if weekly_data:
                weekly_df = pd.DataFrame(
                    weekly_data,
                    columns=["Week", "Quantity"]
                )

                fig = px.line(
                    weekly_df,
                    x="Week",
                    y="Quantity",
                    markers=True
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            st.subheader("Monthly Sorting Activity")

            monthly_data = get_activity_data("monthly")

            if monthly_data:
                monthly_df = pd.DataFrame(
                    monthly_data,
                    columns=["Month", "Quantity"]
                )

                fig = px.bar(
                    monthly_df,
                    x="Month",
                    y="Quantity"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            st.divider()

            st.subheader("Recent Sorting Activity")

            recent_data = get_recent_sorting()

            if recent_data:
                recent_df = pd.DataFrame(
                    recent_data,
                    columns=[
                        "Participant",
                        "Material",
                        "Quantity",
                        "Time"
                    ]
                )

                st.dataframe(
                    recent_df,
                    use_container_width=True
                )

        overview_section()


    with s2:

        st.subheader("Personal Sorting Analytics")

        participants = get_all_participants()

        if participants:

            participant_dict = {
                person[1]: person[0]
                for person in participants
            }

            selected_person = st.selectbox(
                "Select Participant",
                list(participant_dict.keys())
            )

            person_id = participant_dict[selected_person]

            personal_data = get_personal_details(person_id)

            if personal_data:

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Green Points",
                    personal_data[0]
                )

                col2.metric(
                    "Sorting Sessions",
                    personal_data[1]
                )

                col3.metric(
                    "Items Sorted",
                    personal_data[2]
                )

                st.divider()

                history = get_personal_histories(person_id)

                if history:

                    history_df = pd.DataFrame(
                        history,
                        columns=[
                            "Date",
                            "Material",
                            "Quantity"
                        ]
                    )

                    st.subheader("Personal Sorting History")

                    st.dataframe(
                        history_df,
                        use_container_width=True
                    )

                    fig = px.bar(
                        history_df,
                        x="Material",
                        y="Quantity",
                        title="Materials Sorted"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

        else:
            st.info("No participant data available.")

    with s3:

        st.header("🌱 ESG & Impact")

        st.info(
            "ESG analytics will be integrated here using "
            "Supabase sorting records and GreenLoop pilot assumptions."
        )


st.divider()

st.caption(
    "GreenLoop | AI-powered Smart Waste Sorting System"
)
