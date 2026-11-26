
import streamlit as st
import pandas as pd
import os
import plotly.express as px

from cloud_database import *


st.title("♻️ GreenLoop")
st.subheader("Connected Commons & Shared Loops")
st.caption("Online Environmental Intelligence Dashboard")

st.divider()


def show_image(image_name, caption):
    """Display a training image if it exists."""

    image_path = os.path.join("Images", image_name)

    if os.path.exists(image_path):
        st.image(
            image_path,
            caption=caption,
            width="stretch"
        )
    else:
        st.warning(f"Image not found: {image_path}")


tab1, tab2 = st.tabs([
    "🧠 Model & Science Metrics",
    "♻️ Waste Data & ESG Analytics"
])


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

            ranking_data = ranking_database()
            waste_data = get_waste_decomposition()

            daily_data, weekly_data, monthly_data = (
                get_activity_data()
            )

            recent_data = get_recent_sorting()

            ranking_df = pd.DataFrame(
                ranking_data,
                columns=[
                    "Name",
                    "Sessions",
                    "Items",
                    "Points"
                ]
            )

            total_people = len(ranking_df)

            total_points = (
                int(ranking_df["Points"].sum())
                if not ranking_df.empty else 0
            )

            total_items = (
                int(ranking_df["Items"].sum())
                if not ranking_df.empty else 0
            )

            col1, col2, col3 = st.columns(3)

            col1.metric("Participants", total_people)
            col2.metric("Green Points", total_points)
            col3.metric("Items Sorted", total_items)

            st.divider()

            waste_df = pd.DataFrame(
                waste_data,
                columns=["Material", "Quantity"]
            )

            col1, col2 = st.columns(2)

            with col1:

                st.subheader("Waste Composition")

                if not waste_df.empty:

                    fig = px.pie(
                        waste_df,
                        names="Material",
                        values="Quantity",
                        hole=0.45
                    )

                    st.plotly_chart(
                        fig,
                        width="stretch"
                    )

                else:
                    st.info("No waste data available.")

            with col2:

                st.subheader("Most Sorted Material")

                if not waste_df.empty:

                    best_row = waste_df.loc[
                        waste_df["Quantity"].idxmax()
                    ]

                    st.metric(
                        str(best_row["Material"]),
                        int(best_row["Quantity"])
                    )

                else:
                    st.info("No material data available.")

            st.divider()

            st.subheader("Daily Sorting Activity")

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
                    width="stretch"
                )

            else:
                st.info("No daily activity available.")

            st.subheader("Weekly Sorting Activity")

            if weekly_data:

                weekly_df = pd.DataFrame(
                    weekly_data,
                    columns=["Week", "Quantity"]
                )

                fig = px.line(
                    weekly_df,
                    x="Week",
                    y="Quantity",
                    markers=True,
                    title="Items Sorted Per Week"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

            else:
                st.info("No weekly activity available.")

            st.subheader("Monthly Sorting Activity")

            if monthly_data:

                monthly_df = pd.DataFrame(
                    monthly_data,
                    columns=["Month", "Quantity"]
                )

                fig = px.bar(
                    monthly_df,
                    x="Month",
                    y="Quantity",
                    title="Items Sorted Per Month"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

            else:
                st.info("No monthly activity available.")

            st.divider()

            st.subheader("Recent Sorting Sessions")

            if recent_data:

                recent_df = pd.DataFrame(
                    recent_data,
                    columns=[
                        "Participant",
                        "Start Time",
                        "End Time"
                    ]
                )

                st.dataframe(
                    recent_df,
                    width="stretch",
                    hide_index=True
                )

            else:
                st.info("No recent sorting sessions available.")

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

            personal_summary = get_person_summary(person_id)

            points = personal_summary[0]
            sessions = personal_summary[1]
            items = personal_summary[2]

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Green Points",
                int(points)
            )

            col2.metric(
                "Sorting Sessions",
                int(sessions)
            )

            col3.metric(
                "Items Sorted",
                int(items)
            )

            st.divider()

            daily_data, weekly_data, monthly_data = (
                get_personal_details(person_id)
            )

            st.subheader("Personal Sorting Trends")

            if daily_data:

                daily_df = pd.DataFrame(
                    daily_data,
                    columns=["Date", "Quantity"]
                )

                fig = px.bar(
                    daily_df,
                    x="Date",
                    y="Quantity",
                    title="Daily Sorting Activity"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

            else:
                st.info("No daily sorting activity available.")

            if weekly_data:

                weekly_df = pd.DataFrame(
                    weekly_data,
                    columns=["Week", "Quantity"]
                )

                fig = px.line(
                    weekly_df,
                    x="Week",
                    y="Quantity",
                    markers=True,
                    title="Weekly Sorting Activity"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

            else:
                st.info("No weekly sorting activity available.")

            if monthly_data:

                monthly_df = pd.DataFrame(
                    monthly_data,
                    columns=["Month", "Quantity"]
                )

                fig = px.bar(
                    monthly_df,
                    x="Month",
                    y="Quantity",
                    title="Monthly Sorting Activity"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

            else:
                st.info("No monthly sorting activity available.")

            st.divider()

            st.subheader("Personal Sorting History")

            history = get_personal_histories(person_id)

            if history:

                history_df = pd.DataFrame(
                    history,
                    columns=[
                        "Start Time",
                        "End Time",
                        "Material",
                        "Quantity"
                    ]
                )

                st.dataframe(
                    history_df,
                    width="stretch",
                    hide_index=True
                )

                material_df = (
                    history_df
                    .groupby("Material", as_index=False)["Quantity"]
                    .sum()
                )

                fig = px.bar(
                    material_df,
                    x="Material",
                    y="Quantity",
                    title="Materials Sorted"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

            else:
                st.info("No personal sorting history available.")

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
