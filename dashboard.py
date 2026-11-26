import streamlit as st
import pandas as pd
import os
import threading
from database import *
from computer_vision import *
import plotly.express as px
#Dashboard configuration
#Callback to transfer data from AI to DB
def save_detection(event_id, class_name):
    """
    Transfer the output of the CV model and add it to the
    central database
    """
    saving_recycling_logs(event_id, class_name)
st.set_page_config(
    page_title = "GreenLoop Sorting and Recycle Leaderboard",
    page_icon = "♻️",
    layout = "wide"
)
#Live sorting statistics:
@st.fragment(run_every="2s")
def live_statistics(event_id):
    stats = take_session_statistics(event_id)
    st.subheader("Live sorting statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Plastic", stats["plastic"])
    col2.metric("Paper", stats["paper"])
    col3.metric("Metal", stats["metal"])
    col4.metric("Other", stats["other"])
    total_item = sum(stats.values())
    st.metric("Total item sorted  in this session: ", total_item)
#Initialize GreenLoop default states
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "person_id" not in st.session_state:
    st.session_state.person_id = None
if "event_id" not in st.session_state:
    st.session_state.event_id = None
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()
if "vision_thread" not in st.session_state:
    st.session_state.vision_thread = None
if "vision_started" not in st.session_state:
    st.session_state.vision_started = False


#Set title
st.title("🌱 GreenLoop Smart AI-powered Recycling System")
st.markdown("*May the Darkness Be With You 2026 — Track 3: Connected Commons & Shared Loops*")
#tab division
tab1, tab2, tab3 = st.tabs([
    "🎮 Live Sorting & Leaderboard", 
    "🔬 Model & Science Metrics", 
    "🏢 Trash Data & ESG Analytics"
])

st.sidebar.title("⚙️Control panel")
st.sidebar.subheader("System status")
st.sidebar.text("Status: Online")
st.sidebar.markdown("---")
#Define tab1 layout
init_database()
init_waste_type()
with tab1:
    st.header("Game play & real-time trash sorting")
    st.info("System is ready for computer vision and database")
    #Testing functions
    if st.session_state.is_running and not st.session_state.vision_started:
        event_id = st.session_state.event_id
        stop_event = st.session_state.stop_event
        vision_thread = threading.Thread(
            target=run_vision,
            args=(
                lambda class_name: save_detection(event_id, class_name),
                stop_event
                ),
            daemon=True)
        st.session_state.vision_thread = vision_thread
        st.session_state.vision_started = True
        vision_thread.start()
    
    with st.form("player_form"):
        player_name = st.text_input("Please tell me your name: ")
        submitted = st.form_submit_button("Start sorting session!")
        if st.session_state.is_running:
            st.success("🟢 Session is active")
            st.write(f"Participant ID: {st.session_state.person_id}")
            st.write(f"Event ID: {st.session_state.event_id}")
            live_statistics(st.session_state.event_id)
        #Create a separate thread for computer vision to run
        if submitted:
            input_name = player_name.strip()
            if not input_name:
                st.warning("Please write your name in the textbox!")
            elif st.session_state.is_running:
                st.warning("Another session is currently in operation! Please try again later!")
            else:
                participant_info = data_retrieval(input_name)
                person_id = participant_info["person_id"]
                event_id = start_session(input_name)
                #Store the current state:
                st.session_state.person_id = person_id
                st.session_state.event_id = event_id
                st.session_state.stop_event.clear()
                st.session_state.is_running = True
                st.success(f"Welcome {input_name} to GreenLoop sorting. Your session id is {event_id}. Have fun with your sorting!")
                st.rerun()
    #Ending the state: set the stop state to turn off cam, 
    if st.session_state.is_running:
        if st.button("Finish session"):
            st.session_state.stop_event.set()
            vision_thread = st.session_state.vision_thread
            if vision_thread is not None and vision_thread.is_alive():
                vision_thread.join(timeout=10)
            if vision_thread is not None and vision_thread.is_alive():
                st.error("Computer vision is still on. Please try again!")
            else:
                person_id = st.session_state.person_id
                event_id = st.session_state.event_id
                final_result = end_session(person_id, event_id)
                item_counter = final_result["item_counter"]
                point_earned = final_result["points_earned"]
                total = final_result["total_points"]
                #Reset everything for the new session
                st.session_state.is_running = False
                st.session_state.person_id = None
                st.session_state.event_id = None
                st.session_state.stop_event.clear()
                st.session_state.vision_started = False
                st.session_state.vision_thread = None
                
                st.success("Congratulation! You complete your session successfully!")
                st.subheader("Your sorting summary: ")
                col1, col2, col3, col4 = st.columns(4)

                col1.metric("Plastic", item_counter["plastic"])
                col2.metric("Paper", item_counter["paper"])
                col3.metric("Metal", item_counter["metal"])
                col4.metric("Other", item_counter["other"])

                st.metric("Total Items Sorted", sum(item_counter.values()))
                st.metric("Green points earned: ", point_earned)
                st.metric("Total points: ", total)
                
            
    #Print the information
    rankings = ranking_database()
    st.markdown("----")
    st.subheader("Leaderboard")
    df_leaderboard = pd.DataFrame(
        rankings,
        columns = [
            "Participants",
            "Sessions",
            "Total item sorted",
            "Green points"
        ]
    
    )
    df_leaderboard.index = range(1, len(df_leaderboard) + 1)
    df_leaderboard.index.name = "Rank"
    st.dataframe(df_leaderboard, use_container_width=True)

    
#Sidebar setup
option = st.sidebar.selectbox("Select your role", ["Admin", "Participants", "Users"])
#Setup admin login, on admin can reset the database
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if option == "Admin": 
    st.sidebar.subheader("🔐 Admin Panel")
    if not st.session_state.is_admin:
        with st.sidebar.form("admin_login_form"):
            admin_id = st.text_input("Enter username/ID credentials: ", key="input_ad_id")
            admin_pass = st.text_input("Enter password: ", key="input_ad_pass")
            admin_login_submitted = st.form_submit_button("Login")
            
            if admin_login_submitted:
                if admin_id.strip() == "EddieNguyenTran07" and admin_pass.strip() == "Innovationfair2026":
                    st.session_state.is_admin = True
                    st.success("Login successful!"),
                    st.session_state.pop("input_ad_id", None)
                    st.session_state.pop("input_ad_pass", None)
                    st.rerun()
                else:
                    st.error("Admin ID or password does not match!")
    else:
        st.sidebar.success("Logged in as Admin🟢")
        if st.sidebar.button("Reset data🔄"):
                reset_database()
                st.success("Leaderboard has been reset!")
                #Rerun the page to update the leaderboard
                st.rerun()
        if st.sidebar.button("Sign out"):
            st.session_state.is_admin = False
            st.rerun()
        #Add edit button and rights for admin to modify the current database
        #Every thing related to button now put into session_state
        if "edit_mode" not in st.session_state:
            st.session_state.edit_mode = False
        if st.sidebar.button("Edit current database"):
            st.session_state.edit_mode = True
        if st.session_state.edit_mode:
            personal_data = get_all_participants()
            user_data = []
            for item in personal_data:
                pid = item[0]
                name = item[1]
                points = item[2]
                user_data.append(f"[ID: {pid} - {name} - {points} points]")
            if user_data:
                choices = st.selectbox("Choose who you want to delete: ", user_data)
                if st.button("Confirm delete"):
                    target_id = int(choices.split('[ID: ')[1].split(" - ")[0])
                    delete_participant(target_id)
                    st.success(f"Participant ID {target_id} has been deleted")
                    st.rerun()
            else:
                st.info("Leaderboard is currently empty!")
#Render tab2 
with tab2:
    st.header("🔬 Model & Science Metrics")
    st.caption("YOLOv8 Computer Vision AI training's indices and performances")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label = "mAP @ 0.50", value = "79.93%", delta = "Epoch 50")
    with col2:
        st.metric(label = "mAP @ 0.50:0.95", value = "59.68%", delta = "High Strictness")
    with col3:
        st.metric(label = "Precision", value = "82.15%", delta = "Low False Positive")
    with col4:
        st.metric(label = "Recall", value = "75.28%", delta = "Robust Detection")
    st.markdown("---")
    #Creating subtabs
    sub1, sub2, sub3, sub4  = st.tabs([
        "🎯 Confusion Matrix", 
        "📈 Training Loss & Curves", 
        "🏷️ Dataset Labels",
        "Training Samples"
    ])
    #Images
    img_files = {
        "cm_normed": "confusion_matrix_normalized.png",
        "cm_raw": "confusion_matrix.png",
        "results": "results.png",
        "labels": "labels.jpg",
        "pr": "BoxPR_curve.png",
        "precision": "BoxP_curve.png",
        "F1_confidence": "BoxF1_curve.png",
        "recall": "BoxR_curve.png",
        "sample1": "train_batch1.jpg",
        "sample2": "train_batch0.jpg"
    }
    with sub1:
        st.markdown("#### Confusion Matrix")
        col_cm1, col_cm2 = st.columns(2)
        with col_cm1:
            if os.path.exists(img_files["cm_normed"]):
                st.image(img_files["cm_normed"], caption="Normalized Confusion Matrix", use_container_width=True)
        with col_cm2:
            if os.path.exists(img_files["cm_raw"]):
                st.image(img_files["cm_raw"], caption="Orginal Confusion Matrix", use_container_width=True)
    with sub2:
        st.markdown("#### Training curves and statistics")
        col_curve1, col_curve2, col_curve3, col_curve4, col_curve5 = st.columns(5)
        with col_curve1:
            if os.path.exists(img_files["results"]):
                st.image(img_files["results"], caption="Loss and training statistics and curves", use_container_width=True)
        with col_curve2:
            if os.path.exists(img_files["pr"]):
                st.image(img_files["pr"], caption="Precision and recall curves", use_container_width=True)
        with col_curve3:
            if os.path.exists(img_files["precision"]):
                st.image(img_files["precision"], caption="Precision curve", use_container_width=True)
        with col_curve4:
            if os.path.exists(img_files["F1_confidence"]):
                st.image(img_files["F1_confidence"], caption="F1 confidence curve", use_container_width=True)
        with col_curve5:
            if os.path.exists(img_files["recall"]):
                st.image(img_files["recall"], caption="Recall curves", use_container_width=True)
    with sub3:
        st.markdown("#### Class labeling")
        col_label1, col_label2 = st.columns(2)
        with col_label1:
            if os.path.exists(img_files["labels"]):
                st.image(img_files["labels"], caption="Instane labeling and classification", use_container_width=True)
    with sub4:
        st.markdown("#### Some training samples")
        col_sample1, col_sample2 = st.columns(2)
        with col_sample1:
            if os.path.exists(img_files["sample1"]):
                st.image(img_files["sample1"], caption="train_batch0", use_container_width=True)
        with col_sample2:
            if os.path.exists(img_files["sample2"]):
                st.image(img_files["sample2"], caption="train_batch1", use_container_width=True)
#Analytic tab:
with tab3:
    s1, s2, s3 = st.tabs([
        "📊Overview",
        "👤Personal analytics",
        "🌱	ESG & Impact"
    ])
    with s1:
        st.header("📊 GreenLoop Overview")
        st.caption("Organisation recycling performances and participation")
        conn = get_connection()
        ranking = ranking_database()
        total_people = len(ranking)
        total_sessions = 0
        total_quantity = 0
        total_point_issued = 0
        for item in ranking:
            session = item[1]
            quantity = item[2]
            points = item[3]
            total_sessions += session
            total_quantity += quantity
            total_point_issued += points
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            with st.container(border=True):
                st.metric("Total item sorted: ", total_quantity)
        with col2:
            with st.container(border=True):
                st.metric("Total sessions: ", total_sessions)
        with col3:
            with st.container(border=True):
                st.metric("Total participants: ", total_people)
        with col4:
            with st.container(border=True):
                st.metric("Total point issued: ", total_point_issued)
        st.markdown("---")
        st.subheader("01. Waste decomposition")
        trash_summary = get_waste_decomposition()
        labels = [item[0] for item in trash_summary]
        values = [item[1] for item in trash_summary]
        df = pd.DataFrame(
            trash_summary,
            columns=["Waste type", "Quantity"]
        )
        st.dataframe(df)
        fig = px.pie(
            names=labels,
            values=values,
            hole=0.5
        )
        st.plotly_chart(fig)
        st.markdown("---")
        st.subheader("02. Sorting activities")
        daily, weekly, monthly = st.tabs([
        "Daily",
        "Weekly",
        "Monthly"
        ])
        d, w, m = get_activity_data()
        with daily:
            df = pd.DataFrame(
                d,
                columns=["Period", "Total quantity"]
            )
            fig = px.line(
            df,
            x="Period",
            y="Total quantity",
            markers=True,
            title="Daily sorting activity"
            )
            st.plotly_chart(fig)
        with weekly:
            df = pd.DataFrame(
                w,
                columns=["Period", "Total quantity"]
            )
            fig = px.line(
            df,
            x="Period",
            y="Total quantity",
            markers=True,
            title="Daily sorting activity"
            )
            st.plotly_chart(fig)
        with monthly:
            df = pd.DataFrame(
                m,
                columns=["Period", "Total quantity"]
            )
            fig = px.line(
            df,
            x="Period",
            y="Total quantity",
            markers=True,
            title="Daily sorting activity"
            )
            st.plotly_chart(fig)
        st.markdown("---")
        st.subheader("03. Sorting performance insights")
        average = round(total_quantity / total_sessions, 3)
        best_material = get_best_material()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            with st.container(border=True):
                st.metric("Average items / session", average)
        with col2:
            with st.container(border=True):
                st.metric("Most sorted material", best_material)
        with col3:
            ranking = ranking_database()
            best_point = ranking[0][3]
            best_person = ranking[0][0]
            with st.container(border=True):
                st.metric("Best participant: ", best_person)
        with col4:
            with st.container(border=True):
                st.metric("Highest greenpoint: ", best_point)
            
        st.markdown("---")
        st.subheader("04. Recent sorting activities")
        recent = get_recent_sorting()
        df = pd.DataFrame(
            recent,
            columns=["Username", "Time start", "Time end"]
        )
        st.dataframe(df)
    with s2:
        st.header("👤Personal analytics")
        participant_name = st.text_input("Search participant", placeholder="Enter participant name...")
        if st.button("Search"):
            if not participant_name:
                st.warning("Do not leave this field blank")
            else:
                person_id = 0
                total_point = 0
                total_events = 0
                total_quantity = 0
                trash_details = {}
                input_name = participant_name.strip().lower()
                naming_list, data_general, data_decomposition = get_user_details()
                for item in naming_list:
                    if input_name == item[1].lower():
                        person_id = item[0]
                        total_point = item[2]
                for item in data_general:
                    if input_name == item[1].lower():
                        total_events = item[2]
                        total_quantity = item[3]
                for item in data_decomposition:
                    if item[0].lower() == input_name:
                        if item[1] == "plastic":
                            trash_details["plastic"] = item[2]
                        elif item[1] == "metal":
                            trash_details["metal"] = item[2]
                        elif item[1] == "paper":
                            trash_details["paper"] = item[2]
                        elif item[1] == "other":
                            trash_details["other"] = item[2]
                sorted_list = sorted(trash_details.items(), key=lambda item: item[1], reverse=True)
                top_material = sorted_list[0][0]
                top_quantity = sorted_list[0][1]
                if person_id is not None:
                    st.success("Participant found!")
                else:
                    st.warning("Participant not found! Please check again!")
                if person_id is not None:
                    st.subheader("Participant profile!")
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        with st.container(border=True):
                            st.metric("Username: ", participant_name)
                    with col2:
                        with st.container(border=True):
                            st.metric("User ID: ", person_id)
                st.markdown("---")
                st.subheader("01. Personal Performance Overview")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    with st.container(border=True):
                        st.metric(label="Total Items", value=total_quantity, help="Total items sorted")
                with col2:
                    with st.container(border=True):
                        st.metric(label="Total sessions", value=total_events, help="Total sessions started")
                with col3:
                    with st.container(border=True):
                        st.metric(label="Green points", value=total_point, help="Total points acquired")
                with col4:
                    with st.container(border=True):
                        st.metric(label="Top material", value=top_material, help="Top sorted material")
                st.markdown("---")
                st.subheader("02.Personal waste decomposition")
                decomposition = pd.DataFrame(
                    [
                    {
                        "Material": material.capitalize(),
                        "Quantity": quantity,
                        "Percentage": round(quantity / total_quantity * 100, 1)
                    }
                    for material, quantity in trash_details.items()
                    ]
                )
                fig = px.bar(
                decomposition,
                x="Quantity",
                y="Material",
                orientation="h",
                text="Percentage"
                )
                fig.update_traces(texttemplate="%{text}%", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("---")
                st.subheader("03. Personal sorting trends")
                pdata_daily, pdata_weekly, pdata_monthly = get_personal_details(person_id)
                tab1, tab2, tab3 = st.tabs(["Daily", "Weekly", "Monthly"])
                with tab1:
                    df = pd.DataFrame(
                    pdata_daily,
                    columns=["Period", "Quantity"]
                    )
                    fig = px.line(
                    df,
                    x="Period",
                    y="Quantity",
                    markers=True,
                    title="Daily sorting graph"
                    )
                    st.plotly_chart(fig)
                with tab2:
                    df = pd.DataFrame(
                    pdata_weekly,
                    columns=["Period", "Quantity"]
                    )
                    fig = px.line(
                    df,
                    x="Period",
                    y="Quantity",
                    markers=True,
                    title="Weekly sorting graph"
                    )
                    st.plotly_chart(fig)
                with tab3:
                    df = pd.DataFrame(
                    pdata_monthly,
                    columns=["Period", "Quantity"]
                    )
                    fig = px.line(
                    df,
                    x="Period",
                    y="Quantity",
                    markers=True,
                    title="Monthly sorting graph"
                    )
                    st.plotly_chart(fig)
                st.markdown("---")
                st.subheader("04. Personal sorting records")
                records = get_personal_histories(person_id)
                df = pd.DataFrame(records, columns=["Time start", "Time end", "Material", "Quantity"])
                st.dataframe(df)
    with s3:
        st.header("🌱Environmental Impact Assessment")
        st.caption("Estimated environmental impact based on GreenLoop pilot data")
        st.warning("PILOT ESTIMATES | Figures are preliminary estimates, "
                   "not verified environmental measurements."
        )
        st.markdown("---")
        st.subheader("01. Environmental impact through numbers")
        waste_summary = get_waste_decomposition()
        plastic_weight = 0.03
        metal_weight = 0.04
        paper_weight = 0.02
        other_weight = 0.015
        plastic_factor = 1.06
        paper_factor = 3.6
        metal_factor = 5.5
        other_factor = 1
        esg_summary = {}
        total_weight_material = 0
        for item in waste_summary:
            name = item[0]
            emission = 0
            quantity = item[1]
            if name == "plastic":
                emission = plastic_weight * quantity * plastic_factor
                esg_summary["plastic"] = emission
                total_weight_material += plastic_weight * quantity
            elif name == "metal":
                emission = metal_weight * quantity * metal_factor
                esg_summary["metal"] = emission
                total_weight_material += metal_weight * quantity
            elif name == "paper":
                emission = paper_weight * quantity * paper_factor
                esg_summary["paper"] = emission
                total_weight_material += paper_weight * quantity
            elif name == "other":
                emission = other_weight * quantity * other_factor
                esg_summary["other"] = emission
                total_weight_material += other_weight * quantity
        total_emission = 0
        for item in esg_summary.values():
            total_emission += item
        count_total = 0
        for item in waste_summary:
            count_total += item[1]
        average_weight = round(total_weight_material / count_total, 3)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            with st.container(border=True):
                st.metric(label="Potential CO2e avoided", value=total_emission, help="Estimated using pilot assumptions")
        with col2:
            with st.container(border=True):
                st.metric(label="Average Kg per item", value=average_weight, help="Average weight per a recycled item")
        with col3:
            with st.container(border=True):
                st.metric(label="Total item sorted", value=count_total, help="Actual recorded count")
        with col4:
            with st.container(border=True):
                st.metric(label="Material categories", value=len(waste_summary), help="AI classification categories")
                
        st.markdown("---")
        st.subheader("02. Environmental impact by material")
        df_impact = pd.DataFrame(
            list(esg_summary.items()),
            columns=["Material", "Potential CO2e (kg)"]
        )
        fig = px.bar(
            df_impact,
            x="Material",
            y="Potential CO2e (kg)",
            color = "Material",
            title = "Estimated CO2e avoided by material"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
        st.subheader("03. Environmental changes over time")
        daily_data, weekly_data, monthly_data = get_activity_per_material()
        daily_esg = []
        weekly_esg = []
        monthly_esg = []
        for item in daily_data:
            time = item[0]
            waste = item[1]
            quantity = item[2]
            if waste == "plastic":
                co2 = quantity * plastic_weight * plastic_factor
                data = (time, waste, co2)
                daily_esg.append(data)
            elif waste == "metal":
                co2 = quantity * metal_weight * metal_factor
                data = (time, waste, co2)
                daily_esg.append(data)
            elif waste == "paper":
                co2 = quantity * paper_weight * paper_factor
                data = (time, waste, co2)
                daily_esg.append(data)
            elif waste == "other":
                co2 = quantity * other_weight * other_factor
                data = (time, waste, co2)
                daily_esg.append(data)
        
        for item in weekly_data:
            time = item[0]
            waste = item[1]
            quantity = item[2]
            if waste == "plastic":
                co2 = quantity * plastic_weight * plastic_factor
                data = (time, waste, co2)
                weekly_esg.append(data)
            elif waste == "metal":
                co2 = quantity * metal_weight * metal_factor
                data = (time, waste, co2)
                weekly_esg.append(data)
            elif waste == "paper":
                co2 = quantity * paper_weight * paper_factor
                data = (time, waste, co2)
                weekly_esg.append(data)
            elif waste == "other":
                co2 = quantity * other_weight * other_factor
                data = (time, waste, co2)
                weekly_esg.append(data)
        
        for item in monthly_data:
            time = item[0]
            waste = item[1]
            quantity = item[2]
            if waste == "plastic":
                co2 = quantity * plastic_weight * plastic_factor
                data = (time, waste, co2)
                monthly_esg.append(data)
            elif waste == "metal":
                co2 = quantity * metal_weight * metal_factor
                data = (time, waste, co2)
                monthly_esg.append(data)
            elif waste == "paper":
                co2 = quantity * paper_weight * paper_factor
                data = (time, waste, co2)
                monthly_esg.append(data)
            elif waste == "other":
                co2 = quantity * other_weight * other_factor
                data = (time, waste, co2)
                monthly_esg.append(data)
        tab1, tab2, tab3 = st.tabs(
            ["Daily",
            "Weekly",
            "Monthly"]
        )
        with tab1:
            df_daily = pd.DataFrame(daily_esg, columns=["Date", "Waste", "CO2"])
            fig = px.line(
                df_daily,
                x="Date",
                y="CO2",
                color="Waste",
                markers=True,
                title="Estimated CO2 avoided daily per material"
            )
            st.plotly_chart(fig)
        with tab2:
            df_weekly = pd.DataFrame(weekly_esg, columns=["Date", "Waste", "CO2"])
            fig = px.line(
                df_weekly,
                x="Date",
                y="CO2",
                color="Waste",
                markers=True,
                title="Estimated CO2 avoided weekly per material"
            )
            st.plotly_chart(fig)
        with tab3:
            df_monthly = pd.DataFrame(monthly_esg, columns=["Date", "Waste", "CO2"])
            fig = px.line(
                df_monthly,
                x="Date",
                y="CO2",
                color="Waste",
                markers=True,
                title="Estimated CO2 avoided monthly per material"
            )
            st.plotly_chart(fig)
        
        
