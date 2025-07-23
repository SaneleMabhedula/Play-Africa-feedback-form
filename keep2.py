import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
from streamlit_lottie import st_lottie
import altair as alt
import numpy as np
from PIL import Image
import qrcode
import base64
from io import BytesIO
import hashlib

# Setup data storage
DATA_DIR = "data"
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.csv")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Initialize users file if it doesn't exist
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({
            "admin": {
                "password": hashlib.sha256("admin123".encode()).hexdigest(),  # Hashed password
                "role": "admin"
            },
            "visitor": {
                "password": hashlib.sha256("visitor123".encode()).hexdigest(),  # Hashed password
                "role": "visitor"
            }
        }, f)

def load_lottiefile(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        return None

def save_submission(entry):
    df = pd.DataFrame([entry])
    if os.path.exists(SUBMISSIONS_FILE):
        df.to_csv(SUBMISSIONS_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(SUBMISSIONS_FILE, index=False)

def load_submissions():
    if os.path.exists(SUBMISSIONS_FILE):
        return pd.read_csv(SUBMISSIONS_FILE)
    return pd.DataFrame()

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered)
    return base64.b64encode(buffered.getvalue()).decode()

def show_qr_code(data):
    qr_img = generate_qr_code(data)
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <h3>Scan to access feedback form</h3>
        <img src="data:image/png;base64,{qr_img}" width="200">
        <p style="font-size: 12px; margin-top: 10px;">Point your camera at the QR code</p>
    </div>
    """, unsafe_allow_html=True)

# Theme-adaptive colors
def get_theme_colors():
    return {
        'text': 'var(--text-color)',
        'background': 'var(--background-color)',
        'card_bg': 'var(--card-bg-color)',
        'metric_value': 'var(--metric-value-color)',
        'metric_label': 'var(--metric-label-color)'
    }

# --- Authentication ---
def authenticate():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'username' not in st.session_state:
        st.session_state.username = None

    if not st.session_state.authenticated:
        # Custom CSS for the login page
        st.markdown("""
        <style>
            .login-container {
                max-width: 400px;
                padding: 30px;
                margin: 0 auto;
                border-radius: 10px;
                background-color: var(--card-bg-color);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .login-title {
                text-align: center;
                color: #2E86AB;
                margin-bottom: 30px;
                font-size: 28px;
                font-weight: 600;
            }
            .stTextInput>div>div>input {
                text-align: center;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #ddd;
            }
            .login-button {
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                background-color: #2E86AB;
                color: white;
                font-weight: 600;
                border: none;
                margin-top: 20px;
            }
            .login-button:hover {
                background-color: #1F5F7A;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Login container
        st.markdown("""
        <div class="login-container">
            <div class="login-title">Play Africa Login</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form inside the container
        with st.form("login_form"):
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                
                if st.form_submit_button("Login", type="primary"):
                    users = load_users()
                    if username in users:
                        hashed_password = hashlib.sha256(password.encode()).hexdigest()
                        if users[username]["password"] == hashed_password:
                            st.session_state.authenticated = True
                            st.session_state.role = users[username]["role"]
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.error("Incorrect password")
                    else:
                        st.error("Username not found")
        
        # Add some space and Play Africa branding
        st.markdown("""
        <div style='text-align: center; margin-top: 50px;'>
            <p style='color: var(--text-color); font-size: 14px;'>
                Welcome to Play Africa's Feedback System
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        return False
    return True

def logout():
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()

# --- Home Page ---
def show_home():
    colors = get_theme_colors()
    col1, col2 = st.columns([1, 1])
    with col1:
        try:
            st.image("Play_Africa.png", width=300)
        except:
            st.warning("Play Africa logo image not found")
    with col2:
        json_data = load_lottiefile("lottie_kid2.json")
        if json_data:
            st_lottie(json_data, height=200)
        else:
            st.write("Lottie animation not found.")
    
    st.markdown(f"<h1 style='color:{colors['text']}'>Welcome to Play Africa</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align: center; font-style: italic; font-size: 20px; margin-top: 20px; color:{colors['text']}'>"
        "\"Play is the highest form of research.\" – Albert Einstein"
        "</div>", unsafe_allow_html=True
    )
    
    with st.expander("About Play Africa", expanded=True):
        st.markdown(f"""
        <div style='color:{colors['text']}'>
            <p>At Play Africa, we believe every child's experience is valuable. Your feedback helps us create a better, more engaging space for all our young visitors.</p>
            <p><strong>Why share your thoughts?</strong></p>
            <ul>
                <li>Help us improve our programs and facilities</li>
                <li>Shape the future of Play Africa</li>
                <li>Make your voice heard</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Show QR code for feedback form if user is visitor or not logged in
    if not st.session_state.authenticated or st.session_state.role == "visitor":
        st.markdown("---")
        st.markdown("<h2 style='text-align: center;'>Quick Access</h2>", unsafe_allow_html=True)
        show_qr_code("https://your-streamlit-app-url.com/Visitor%20Feedback")

# --- Feedback Form ---
def show_feedback():
    colors = get_theme_colors()
    st.markdown(f"<h1 style='color:{colors['text']}'>Play Africa Visit Feedback</h1>", unsafe_allow_html=True)
    
    with st.expander("Form Instructions", expanded=False):
        st.markdown(f"""
        <div style='color:{colors['text']}'>
            <p>Please take a few minutes to share your experience at Play Africa. Your feedback helps us improve our programs and facilities.</p>
            <p><strong>All fields marked with * are required.</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.form("feedback_form"):
        st.markdown(f"<h3 style='color:{colors['text']}'>About You & Your Group</h3>", unsafe_allow_html=True)
        
        school = st.text_input("Name of School / Organisation / Group*", placeholder="Enter your organization name")
        group_type = st.radio("Type of Group*", [
            "Preschool / ECD Centre", "Primary School (Grade R–3)",
            "Primary School (Grade 4–7)", "Special Needs School",
            "NGO / Community Group", "Other"
        ])
        children_no = st.number_input("Children Participating*", min_value=1, value=20)
        children_age = st.text_input("Children Age(s)* (e.g., 4–6, 7–9)", placeholder="4-6 years")
        adults_present = st.number_input("Adults Present*", min_value=1, value=2)
        visit_date = st.date_input("Date of Visit / Programme*", value=datetime.now())
        programme = st.multiselect("Type of Experience*", [
            "Play Africa at Constitution Hill", "Outreach Programme",
            "Special Event or Pop‑Up", "Other"
        ])

        categories = [
            "Overall experience for children",
            "Friendliness and professionalism of facilitators",
            "Level of engagement for children",
            "Inclusiveness and welcoming atmosphere",
            "Relevance of activities to children's learning",
            "Planning and communication before the visit",
            "Physical safety and comfort of the space"
        ]

        # Sliders for ratings
        st.markdown(f"<h3 style='color:{colors['text']}'>Your Ratings (1-5 scale)</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:{colors['text']}'>1 = Needs Improvement, 3 = Satisfactory, 5 = Excellent</p>", unsafe_allow_html=True)
        
        ratings = {}
        for cat in categories:
            st.markdown(f"<strong style='color:{colors['text']}'>{cat}</strong>", unsafe_allow_html=True)
            ratings[cat] = st.slider("", 1, 5, 3, key=cat, label_visibility='collapsed')
            st.markdown(f"<div style='color:{colors['text']}; display: flex; justify-content: space-between; margin-top: -15px;'>"
                        "<span>1 (Poor)</span><span>2</span><span>3 (OK)</span><span>4</span><span>5 (Excellent)</span></div>", 
                        unsafe_allow_html=True)

        st.markdown(f"<h3 style='color:{colors['text']}'>Your Feedback</h3>", unsafe_allow_html=True)
        q1 = st.text_area("What did the children enjoy most?*", placeholder="Describe what activities or aspects the children enjoyed")
        q2 = st.text_area("Any moments of curiosity, creativity, or learning?", placeholder="Share any special moments you observed")
        q3 = st.text_area("How did this support your teaching goals?", placeholder="Explain how the experience aligned with your educational objectives")
        q4 = st.text_area("Suggestions to improve future visits", placeholder="Your ideas for making Play Africa even better")
        q5 = st.text_area("Would you recommend Play Africa? Why?*", placeholder="Please share your recommendation thoughts")

        st.markdown(f"<h3 style='color:{colors['text']}'>Future Collaboration</h3>", unsafe_allow_html=True)
        future_collab = st.radio("Interested in future collaboration?", ["Yes", "No", "Maybe"])
        future_topics = st.text_area("Topics/needs you'd like us to explore?", placeholder="Any specific themes or subjects you'd like to see")

        required_fields = [
            school, children_age, programme, q1, q5
        ]
        
        if st.form_submit_button("Submit Feedback"):
            if not all(required_fields):
                st.error("Please fill in all required fields (marked with *)")
            else:
                entry = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "school": school,
                    "group_type": group_type,
                    "children_no": children_no,
                    "children_age": children_age,
                    "adults_present": adults_present,
                    "programme": json.dumps(programme),
                    "engagement": ratings["Overall experience for children"],
                    "safety": ratings["Friendliness and professionalism of facilitators"],
                    "cleanliness": ratings["Level of engagement for children"],
                    "fun": ratings["Inclusiveness and welcoming atmosphere"],
                    "learning": ratings["Relevance of activities to children's learning"],
                    "planning": ratings["Planning and communication before the visit"],
                    "safety_space": ratings["Physical safety and comfort of the space"],
                    "comments": json.dumps({
                        "enjoyed": q1,
                        "curiosity": q2,
                        "support_goals": q3,
                        "improve": q4,
                        "recommend": q5,
                        "future_topics": future_topics,
                        "collaboration": future_collab
                    })
                }
                save_submission(entry)
                st.success("Thank you for your feedback!")
                st.balloons()
                
                # Show appreciation message
                st.markdown(f"""
                <div style='
                    background: {colors['card_bg']};
                    border-radius: 10px;
                    padding: 20px;
                    margin-top: 20px;
                '>
                    <h3 style='color:{colors['text']}'>Thank You!</h3>
                    <p style='color:{colors['text']}'>Your feedback has been submitted successfully. We truly appreciate you taking the time to help us improve Play Africa.</p>
                    <p style='color:{colors['text']}'>A copy of your feedback has been sent to your email address.</p>
                </div>
                """, unsafe_allow_html=True)

# --- Dashboard ---
def show_dashboard():
    colors = get_theme_colors()
    st.markdown(f"<h1 style='color:{colors['text']}'>Feedback Dashboard</h1>", unsafe_allow_html=True)
    
    df = load_submissions()
    if df.empty:
        st.info("No feedback submitted yet. Please check back later!")
        return

    # Process data
    rating_columns = ["engagement", "safety", "cleanliness", "fun", "learning", "planning", "safety_space"]
    for col in rating_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0  # Default value if column is missing

    total = len(df)
    categories_labels = [
        ("Overall experience", "engagement"),
        ("Facilitator professionalism", "safety"),
        ("Child engagement", "cleanliness"),
        ("Welcoming atmosphere", "fun"),
        ("Learning relevance", "learning"),
        ("Pre-visit communication", "planning"),
        ("Space comfort", "safety_space")
    ]

    # Calculate averages
    averages = {}
    for label, col in categories_labels:
        averages[label] = round(df[col].mean(), 2) if total > 0 else 0

    # --- Metrics Section ---
    st.markdown(f"<h2 style='color:{colors['text']}'>Overview Metrics</h2>", unsafe_allow_html=True)
    
    # Main metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 20px;
            '>
                <div style='font-size: 14px; color: {colors['metric_label']};'>Total Feedback</div>
                <div style='font-size: 28px; font-weight: bold; color: {colors['metric_value']};'>{total}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 20px;
            '>
                <div style='font-size: 14px; color: {colors['metric_label']};'>Avg. Engagement</div>
                <div style='font-size: 28px; font-weight: bold; color: {colors['metric_value']};'>{averages.get('Overall experience', 0)}/5</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 20px;
            '>
                <div style='font-size: 14px; color: {colors['metric_label']};'>Avg. Safety</div>
                <div style='font-size: 28px; font-weight: bold; color: {colors['metric_value']};'>{averages.get('Facilitator professionalism', 0)}/5</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Secondary metrics row
    cols = st.columns(4)
    metric_pairs = [
        ("Avg. Fun", "Welcoming atmosphere"),
        ("Avg. Learning", "Learning relevance"),
        ("Avg. Planning", "Pre-visit communication"),
        ("Avg. Comfort", "Space comfort")
    ]
    
    for (title, key), col in zip(metric_pairs, cols):
        with col:
            st.markdown(
                f"""
                <div style='
                    background: {colors['card_bg']};
                    border-radius: 10px;
                    padding: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                    margin-bottom: 20px;
                '>
                    <div style='font-size: 14px; color: {colors['metric_label']};'>{title}</div>
                    <div style='font-size: 24px; font-weight: bold; color: {colors['metric_value']};'>{averages.get(key, 0)}/5</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # --- Category Comparison ---
   
    
    # Create two columns for charts
    chart_col1, chart_col2 = st.columns([2, 1])
    
    with chart_col1:
        # Main bar chart
        chart_df = pd.DataFrame({
            'Category': [lbl for lbl, _ in categories_labels],
            'Average Rating': [averages[lbl] for lbl, _ in categories_labels]
        })
        
        # Sort by rating for better visualization
        chart_df = chart_df.sort_values('Average Rating', ascending=False)
        
        bar_chart = alt.Chart(chart_df).mark_bar(size=40).encode(
            y=alt.Y('Category:N', title='Categories', sort='-x', axis=alt.Axis(labelLimit=200)),
            x=alt.X('Average Rating:Q', title='Average Rating (1-5 scale)', scale=alt.Scale(domain=[0,5])),
            color=alt.Color('Average Rating:Q', legend=None, scale=alt.Scale(scheme='viridis')),
            tooltip=['Category', 'Average Rating']
        ).properties(
            height=400,
            title="Average Ratings by Category"
        )
        
        # Add text labels
        text = bar_chart.mark_text(
            align='left',
            baseline='middle',
            dx=3  # Nudges text to right so it doesn't appear on top of the bar
        ).encode(
            text=alt.Text('Average Rating:Q', format='.2f')
        )
        
        st.altair_chart(bar_chart + text, use_container_width=True)
    
    with chart_col2:
        # Pie chart for rating distribution
        st.markdown(f"<h4 style='color:{colors['text']}; text-align: center;'>Rating Distribution</h4>", unsafe_allow_html=True)
        
        # Calculate rating distribution
        rating_values = np.concatenate([df[col].values for _, col in categories_labels])
        rating_dist = pd.Series(rating_values).value_counts().sort_index()
        
        pie_data = pd.DataFrame({
            'Rating': rating_dist.index,
            'Count': rating_dist.values
        })
        
        pie_chart = alt.Chart(pie_data).mark_arc().encode(
            theta='Count:Q',
            color=alt.Color('Rating:N', scale=alt.Scale(scheme='viridis')),
            tooltip=['Rating', 'Count']
        ).properties(
            height=300,
            width=300
        )
        
        st.altair_chart(pie_chart, use_container_width=True)

    # --- Feedback Submissions Table ---
    st.markdown(f"<h2 style='color:{colors['text']}'>Feedback Submissions</h2>", unsafe_allow_html=True)
    
    display_cols = ['timestamp', 'school', 'group_type', 'children_no', 'children_age', 'adults_present']
    for col in display_cols:
        if col not in df.columns:
            df[col] = 'N/A'
    
    display_df = df[display_cols].copy()
    display_df = display_df.rename(columns={
        'timestamp': 'Date',
        'school': 'Submitted by',
        'group_type': 'Group Type',
        'children_no': 'Children',
        'children_age': 'Ages',
        'adults_present': 'Adults'
    })
    
    # Convert timestamp to readable format
    if 'Date' in display_df.columns:
        try:
            display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
        except:
            pass
    
    # Pagination for table
    page_size = st.selectbox('Rows per page', [5, 10, 20, 50], index=1)
    page_number = st.number_input('Page', min_value=1, max_value=max(1, len(display_df)//page_size + 1), value=1)
    start_idx = (page_number - 1) * page_size
    end_idx = min(start_idx + page_size, len(display_df))
    
    # Fixed the TypeError by ensuring we're working with a valid DataFrame slice
    table_data = display_df.iloc[start_idx:end_idx] if not display_df.empty else display_df
    
    st.dataframe(
        table_data,
        height=(len(table_data) * 35 + 38) if not table_data.empty else 100,
        use_container_width=True
    )

    # Export button
    st.download_button(
        label="Export Data as CSV",
        data=display_df.to_csv(index=False).encode('utf-8'),
        file_name=f"play_africa_feedback_{datetime.now().strftime('%Y%m%d')}.csv",
        mime='text/csv'
    )

    # --- Feedback Comments ---
    st.markdown(f"<h2 style='color:{colors['text']}'>Feedback Comments</h2>", unsafe_allow_html=True)
    
    # Filter options
    st.markdown(f"<h4 style='color:{colors['text']}'>Filter Comments</h4>", unsafe_allow_html=True)
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        min_rating = st.slider("Minimum Average Rating", 1, 5, 1)
    
    with filter_col2:
        search_term = st.text_input("Search Comments")
    
    # Apply filters
    filtered_df = df.copy()
    
    # Calculate average rating per submission
    filtered_df['avg_rating'] = filtered_df[rating_columns].mean(axis=1)
    filtered_df = filtered_df[filtered_df['avg_rating'] >= min_rating]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['comments'].str.contains(search_term, case=False, na=False)
        ]
    
    # Pagination for comments
    comments_per_page = st.selectbox('Comments per page', [3, 5, 10], index=1)
    total_pages = max(1, (len(filtered_df) + comments_per_page - 1) // comments_per_page)
    comment_page = st.number_input('Comments Page', min_value=1, max_value=total_pages, value=1)
    start_comment = (comment_page - 1) * comments_per_page
    end_comment = min(start_comment + comments_per_page, len(filtered_df))
    
    for idx in range(start_comment, end_comment):
        row = filtered_df.iloc[idx]
        with st.expander(f"Feedback from {row.get('school', 'Unknown')} - {row.get('timestamp', '')} (Avg: {row.get('avg_rating', 0):.1f}/5)"):
            try:
                comments = json.loads(row.get('comments', '{}'))
            except:
                comments = {}
            
            # Display ratings
            st.markdown(f"<h4 style='color:{colors['text']}'>Ratings</h4>", unsafe_allow_html=True)
            rating_cols = st.columns(3)
            for i, (label, col) in enumerate(categories_labels):
                with rating_cols[i % 3]:
                    st.markdown(f"""
                    <div style='
                        background: {colors['card_bg']};
                        border-radius: 5px;
                        padding: 8px;
                        margin-bottom: 8px;
                    '>
                        <div style='font-size: 12px; color: {colors['metric_label']};'>{label}</div>
                        <div style='font-size: 16px; font-weight: bold; color: {colors['metric_value']};'>
                            {row.get(col, 'N/A')}/5
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Display comments
            st.markdown(f"<div style='margin-top: 20px;'>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='color:{colors['text']}'>What children enjoyed:</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:{colors['text']}'>{comments.get('enjoyed', 'N/A')}</p>", unsafe_allow_html=True)
            
            st.markdown(f"<h4 style='color:{colors['text']}'>Learning moments:</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:{colors['text']}'>{comments.get('curiosity', 'N/A')}</p>", unsafe_allow_html=True)
            
            st.markdown(f"<h4 style='color:{colors['text']}'>Teaching support:</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:{colors['text']}'>{comments.get('support_goals', 'N/A')}</p>", unsafe_allow_html=True)
            
            st.markdown(f"<h4 style='color:{colors['text']}'>Improvement suggestions:</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:{colors['text']}'>{comments.get('improve', 'N/A')}</p>", unsafe_allow_html=True)
            
            st.markdown(f"<h4 style='color:{colors['text']}'>Recommendation:</h4>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:{colors['text']}'>{comments.get('recommend', 'N/A')}</p>", unsafe_allow_html=True)
            
            if comments.get('future_topics'):
                st.markdown(f"<h4 style='color:{colors['text']}'>Suggested Topics:</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:{colors['text']}'>{comments.get('future_topics', 'N/A')}</p>", unsafe_allow_html=True)
            
            st.markdown(f"<p style='color:{colors['text']}'><strong>Future collaboration:</strong> {comments.get('collaboration', 'N/A')}</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# --- Main ---
def main():
    st.set_page_config(
        page_title="Play Africa Feedback",
        page_icon=":children_crossing:",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS for theme adaptation and improvements
    st.markdown("""
    <style>
        :root {
            --text-color: black;
            --background-color: white;
            --card-bg-color: white;
            --metric-value-color: #333;
            --metric-label-color: #555;
        }
        
        @media (prefers-color-scheme: dark) {
            :root {
                --text-color: white;
                --background-color: #0E1117;
                --card-bg-color: #262730;
                --metric-value-color: white;
                --metric-label-color: #AAAAAA;
            }
        }
        
        body {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        
        .stApp {
            background-color: var(--background-color);
        }
        
        /* Improved cards */
        .metric-card {
            transition: transform 0.2s;
        }
        
        .metric-card:hover {
            transform: scale(1.02);
        }
        
        /* Better form styling */
        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input, .stSelectbox select {
            background-color: var(--card-bg-color) !important;
            color: var(--text-color) !important;
            border: 1px solid rgba(0,0,0,0.1) !important;
        }
        
        /* Improved table styling */
        .stDataFrame {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Better sidebar */
        [data-testid="stSidebar"] {
            background-color: var(--card-bg-color) !important;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .stDataFrame {
                width: 100% !important;
            }
            
            .metric-card {
                margin-bottom: 15px !important;
            }
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--card-bg-color);
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
    """, unsafe_allow_html=True)

    # Authenticate user
    if not authenticate():
        return

    with st.sidebar:
        lottie = load_lottiefile("lottie_logo.json")
        if lottie:
            st_lottie(lottie, height=100)
        
        st.markdown("""
        <div style='
            font-family: "Comfortaa", cursive;
            font-size: 24px;
            color: var(--text-color);
            text-align: center;
            margin-bottom: 20px;
        '>
            Play Africa
        </div>
        """, unsafe_allow_html=True)
        
        # Show logged in user info
        if st.session_state.authenticated:
            st.markdown(f"""
            <div style='font-size: 14px; color: var(--text-color); margin-bottom: 20px;'>
                Logged in as: <strong>{st.session_state.username}</strong> ({st.session_state.role})
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Logout"):
                logout()
        
        # Navigation based on role
        if st.session_state.role == "admin":
            menu = st.radio(
                "Navigation",
                ["Home", "Visitor Feedback", "Review Feedback"],
                label_visibility="collapsed"
            )
        else:  # visitor
            menu = st.radio(
                "Navigation",
                ["Home", "Visitor Feedback"],
                label_visibility="collapsed"
            )
        
        st.markdown("---")
        
        # Quick stats in sidebar
        if st.session_state.role == "admin" and menu == "Review Feedback":
            df = load_submissions()
            if not df.empty:
                st.markdown(f"""
                <div style='
                    font-size: 14px;
                    color: var(--text-color);
                '>
                    <p><strong>Quick Stats:</strong></p>
                    <p>• Total submissions: {len(df)}</p>
                    <p>• Last submission: {pd.to_datetime(df['timestamp']).max().strftime('%Y-%m-%d') if 'timestamp' in df.columns else 'N/A'}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown(
            f"""
            <div style='font-size:14px; color:var(--text-color); margin-top: 20px;'>
                <p><strong>Contact Us:</strong></p>
                <p>info@playafrica.org.za</p>
                <p>+27 11 123 4567</p>
                <p style='margin-top: 20px;'>© {datetime.now().year} Play Africa. All rights reserved.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    if menu == "Home":
        show_home()
    elif menu == "Visitor Feedback":
        show_feedback()
    elif menu == "Review Feedback" and st.session_state.role == "admin":
        show_dashboard()

if __name__ == "__main__":
    main()