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
import shutil
from typing import Optional, Tuple
from streamlit.components.v1 import html

# Constants
DATA_DIR = "data"
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.csv")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
DELETED_ENTRIES_FILE = os.path.join(DATA_DIR, "deleted_entries.csv")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# Initialize files if they don't exist
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({
            "admin": {
                "password": hashlib.sha256("admin123".encode()).hexdigest(),
                "role": "admin"
            },
            "visitor": {
                "password": hashlib.sha256("visitor123".encode()).hexdigest(),
                "role": "visitor"
            }
        }, f)

if not os.path.exists(DELETED_ENTRIES_FILE):
    pd.DataFrame().to_csv(DELETED_ENTRIES_FILE, index=False)

def create_backup() -> bool:
    """Create a backup of the submissions file"""
    try:
        if os.path.exists(SUBMISSIONS_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"submissions_backup_{timestamp}.csv")
            shutil.copy2(SUBMISSIONS_FILE, backup_file)
            return True
    except Exception as e:
        st.error(f"Backup failed: {str(e)}")
    return False

def load_lottiefile(filepath: str) -> Optional[dict]:
    """Load Lottie animation file with error handling"""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading Lottie file: {str(e)}")
        return None

def save_submission(entry: dict) -> bool:
    """Save a new feedback submission with error handling"""
    try:
        df = pd.DataFrame([entry])
        if os.path.exists(SUBMISSIONS_FILE):
            df.to_csv(SUBMISSIONS_FILE, mode='a', header=False, index=False)
        else:
            df.to_csv(SUBMISSIONS_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving submission: {str(e)}")
        return False

def load_submissions() -> pd.DataFrame:
    """Load all submissions with error handling"""
    try:
        if os.path.exists(SUBMISSIONS_FILE):
            return pd.read_csv(SUBMISSIONS_FILE)
    except Exception as e:
        st.error(f"Error loading submissions: {str(e)}")
    return pd.DataFrame()

def load_deleted_entries() -> pd.DataFrame:
    """Load deleted entries with error handling"""
    try:
        if os.path.exists(DELETED_ENTRIES_FILE):
            return pd.read_csv(DELETED_ENTRIES_FILE)
    except Exception as e:
        st.error(f"Error loading deleted entries: {str(e)}")
    return pd.DataFrame()

def delete_submission(index: int) -> bool:
    """Delete a submission by its index with backup"""
    try:
        df = load_submissions()
        if not df.empty and 0 <= index < len(df):
            # Save to deleted entries first
            deleted_entry = df.iloc[[index]]
            deleted_df = load_deleted_entries()
            deleted_df = pd.concat([deleted_df, deleted_entry], ignore_index=True)
            deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
            
            # Then remove from main file
            df = df.drop(index).reset_index(drop=True)
            df.to_csv(SUBMISSIONS_FILE, index=False)
            return True
    except Exception as e:
        st.error(f"Error deleting submission: {str(e)}")
    return False

def restore_deleted_entry(index: int) -> bool:
    """Restore a deleted entry"""
    try:
        deleted_df = load_deleted_entries()
        if not deleted_df.empty and 0 <= index < len(deleted_df):
            entry = deleted_df.iloc[[index]]
            # Save to main submissions
            if save_submission(entry.iloc[0].to_dict()):
                # Remove from deleted entries
                deleted_df = deleted_df.drop(index).reset_index(drop=True)
                deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
                return True
    except Exception as e:
        st.error(f"Error restoring entry: {str(e)}")
    return False

def generate_qr_code(data: str) -> Tuple[str, Image.Image]:
    """Generate QR code with error handling"""
    try:
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
        img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode(), img
    except Exception as e:
        st.error(f"Error generating QR code: {str(e)}")
        return "", None

def show_qr_code(data: str) -> None:
    """Display QR code with responsive sizing"""
    if not data:
        st.warning("No URL provided for QR code generation")
        return
    
    qr_img_base64, qr_img = generate_qr_code(data)
    if not qr_img_base64 or not qr_img:
        return
    
    # Responsive QR code container
    st.markdown(f"""
    <div class="qr-code-container" style="text-align: center; margin: 20px auto;">
        <img src="data:image/png;base64,{qr_img_base64}" style="max-width: 100%; height: auto;">
        <p style="font-size: 14px; margin-top: 10px; color: var(--text-color);">
            Scan to access feedback form<br>
            Point your camera at the QR code
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Only show download button for admins
    if st.session_state.get('role') == 'admin':
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        st.download_button(
            label="Download QR Code (Admin Only)",
            data=img_bytes,
            file_name="play_africa_feedback_qr.png",
            mime="image/png",
            help="Administrators can download this QR code for printing"
        )

def get_theme_colors() -> dict:
    """Get theme colors for consistent styling"""
    return {
        'text': 'var(--text-color)',
        'background': 'var(--background-color)',
        'card_bg': 'var(--card-bg-color)',
        'metric_value': 'var(--metric-value-color)',
        'metric_label': 'var(--metric-label-color)'
    }

def show_delete_confirmation_dialog(count: int) -> bool:
    """Show confirmation dialog for deletion"""
    with st.expander("⚠️ Confirm Deletion", expanded=True):
        st.warning(f"You are about to delete {count} feedback submission(s). This action cannot be undone.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Delete", type="primary"):
                return True
        with col2:
            if st.button("❌ Cancel"):
                return False
    return False

def show_restore_confirmation_dialog(count: int) -> bool:
    """Show confirmation dialog for restoration"""
    with st.expander("⚠️ Confirm Restoration", expanded=True):
        st.warning(f"You are about to restore {count} deleted submission(s).")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Restore", type="primary"):
                return True
        with col2:
            if st.button("❌ Cancel"):
                return False
    return False

def detect_orientation() -> str:
    """Detect device orientation"""
    try:
        # This JavaScript will detect orientation and set a session state variable
        js = """
        <script>
        function updateOrientation() {
            const isPortrait = window.innerHeight > window.innerWidth;
            parent.window.postMessage({
                isPortrait: isPortrait,
                type: 'streamlit:orientation'
            }, '*');
        }
        
        // Initial detection
        updateOrientation();
        
        // Update on resize
        window.addEventListener('resize', updateOrientation);
        </script>
        """
        html(js)
        
        # Default to portrait if we can't detect
        return st.session_state.get('is_portrait', True)
    except:
        return True

def authenticate() -> bool:
    """Handle user authentication with responsive design"""
    # Initialize session state variables if they don't exist
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'is_mobile' not in st.session_state:
        # Detect mobile devices
        user_agent = ""
        try:
            user_agent = st.request.headers.get("User-Agent", "").lower()
        except:
            pass
        st.session_state.is_mobile = any(m in user_agent for m in ["mobile", "android", "iphone"])
    
    # Detect orientation
    is_portrait = detect_orientation()

    if not st.session_state.authenticated:
        try:
            # Load and process images
            moonkids_img = Image.open("moonkids.png")
            paintingkids_img = Image.open("paintingkids.png")
            moonkids_img = moonkids_img.resize((400, 300))
            paintingkids_img = paintingkids_img.resize((400, 300))
            
            def image_to_base64(img: Image.Image) -> str:
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                return base64.b64encode(buffered.getvalue()).decode()
            
            moonkids_base64 = image_to_base64(moonkids_img)
            paintingkids_base64 = image_to_base64(paintingkids_img)
            
        except FileNotFoundError as e:
            st.error(f"Image files not found: {str(e)}")
            return False
        except Exception as e:
            st.error(f"Error loading images: {str(e)}")
            return False

        # Responsive login UI
        st.markdown(f"""
        <style>
            .login-header {{
                width: 100%;
                text-align: center;
                padding: {'15px 0' if is_portrait else '25px 0'};
                margin-bottom: {'20px' if is_portrait else '30px'};
                background: linear-gradient(90deg, #2E86AB, #3FB0AC);
                color: white;
                font-size: {'24px' if is_portrait else '32px'};
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: {'2px' if is_portrait else '3px'};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .image-card {{
                display: flex;
                flex-direction: column;
                align-items: center;
                margin: {'10px 0' if is_portrait else '15px'};
                padding: {'15px' if is_portrait else '20px'};
                background: rgba(255,255,255,0.9);
                border-radius: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }}
            
            .image-caption {{
                text-align: center;
                margin-top: 10px;
                font-size: {'14px' if is_portrait else '16px'};
                color: #2E86AB;
                font-weight: 600;
                max-width: 100%;
            }}
            
            .login-form-container {{
                width: 100%;
                margin: {'15px auto' if is_portrait else '30px auto'};
                padding: {'15px' if is_portrait else '25px'};
                border-radius: 10px;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="login-header">PLAY AFRICA LOGIN</div>', unsafe_allow_html=True)

        # Layout based on orientation
        if is_portrait:
            # Stack vertically in portrait
            st.markdown(f"""
            <div class="image-card">
                <img src="data:image/jpeg;base64,{moonkids_base64}" style="max-width: 100%; height: auto; border-radius: 8px;">
                <div class="image-caption">
                    "Blast off to the stars! Our space exploration zone lets young astronauts discover the wonders of the universe through play."
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="image-card">
                <img src="data:image/jpeg;base64,{paintingkids_base64}" style="max-width: 100%; height: auto; border-radius: 8px;">
                <div class="image-caption">
                    "Colorful creations! Our art studio nurtures creativity and self-expression through painting and crafts."
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Side-by-side in landscape
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="image-card">
                    <img src="data:image/jpeg;base64,{moonkids_base64}" style="max-width: 100%; height: auto; border-radius: 8px;">
                    <div class="image-caption">
                        "Blast off to the stars! Our space exploration zone lets young astronauts discover the wonders of the universe through play."
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="image-card">
                    <img src="data:image/jpeg;base64,{paintingkids_base64}" style="max-width: 100%; height: auto; border-radius: 8px;">
                    <div class="image-caption">
                        "Colorful creations! Our art studio nurtures creativity and self-expression through painting and crafts."
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.container():
            st.markdown("""
            <div class="login-form-container">
                <h2 style="text-align: center; color: #2E86AB; margin-bottom: 15px;">Welcome Back!</h2>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                
                if st.form_submit_button("Login", type="primary"):
                    try:
                        with open(USERS_FILE, "r") as f:
                            users = json.load(f)
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
                    except Exception as e:
                        st.error(f"Login error: {str(e)}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style='text-align: center; margin-top: 20px; color: #555; font-style: italic; font-size: {'14px' if is_portrait else '16px'};'>
            "Where every child's imagination takes flight through play and discovery"
        </div>
        """, unsafe_allow_html=True)
        
        return False
    return True

def logout() -> None:
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()

def show_home() -> None:
    """Display home page with responsive layout"""
    colors = get_theme_colors()
    is_portrait = detect_orientation()
    
    # Layout based on orientation
    if is_portrait:
        # Single column layout for portrait
        try:
            st.image("Play_Africa.png", use_column_width=True)
        except Exception as e:
            st.warning(f"Logo image not found: {str(e)}")
    else:
        # Two columns for landscape
        col1, col2 = st.columns([1, 1])
        with col1:
            try:
                st.image("Play_Africa.png", width=300)
            except Exception as e:
                st.warning(f"Logo image not found: {str(e)}")
        with col2:
            pass  # Placeholder for animation
    
    # Load animation (shown in both orientations)
    json_data = load_lottiefile("lottie_kid2.json")
    if json_data:
        st_lottie(json_data, height=200 if is_portrait else 250)
    else:
        st.write("Lottie animation not available.")
    
    st.markdown(f"<h1 style='color:{colors['text']}; font-size: {'24px' if is_portrait else '32px'};'>Welcome to Play Africa</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align: center; font-style: italic; font-size: {'16px' if is_portrait else '20px'}; margin-top: {'15px' if is_portrait else '20px'}; color:{colors['text']}'>"
        "\"Play is the highest form of research.\" – Albert Einstein"
        "</div>", unsafe_allow_html=True
    )
    
    with st.expander("About Play Africa", expanded=True):
        st.markdown(f"""
        <div style='color:{colors['text']}; font-size: {'14px' if is_portrait else '16px'};'>
            <p>At Play Africa, we believe every child's experience is valuable. Your feedback helps us create a better, more engaging space for all our young visitors.</p>
            <p><strong>Why share your thoughts?</strong></p>
            <ul>
                <li>Help us improve our programs and facilities</li>
                <li>Shape the future of Play Africa</li>
                <li>Make your voice heard</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    if not st.session_state.authenticated or st.session_state.role == "visitor":
        st.markdown("---")
        st.markdown(f"<h3 style='text-align: center; font-size: {'18px' if is_portrait else '24px'};'>Visitor Feedback Access</h3>", unsafe_allow_html=True)
        
        # Replace with your actual URL
        qr_url = "https://play-africa-dashboard.streamlit.app/"
        show_qr_code(qr_url)

def show_feedback() -> None:
    """Display feedback form with responsive layout"""
    colors = get_theme_colors()
    is_portrait = detect_orientation()
    
    st.markdown(f"<h1 style='color:{colors['text']}; font-size: {'24px' if is_portrait else '32px'};'>Play Africa Visit Feedback</h1>", unsafe_allow_html=True)
    
    with st.expander("Form Instructions", expanded=False):
        st.markdown(f"""
        <div style='color:{colors['text']}; font-size: {'14px' if is_portrait else '16px'};'>
            <p>Please take a few minutes to share your experience at Play Africa. Your feedback helps us improve our programs and facilities.</p>
            <p><strong>All fields marked with * are required.</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    with st.form("feedback_form"):
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>About You & Your Group</h3>", unsafe_allow_html=True)
        
        school = st.text_input("Name of School / Organisation / Group*", placeholder="Enter your organization name")
        group_type = st.radio("Type of Group*", [
            "Preschool / ECD Centre", "Primary School (Grade R–3)",
            "Primary School (Grade 4–7)", "Special Needs School",
            "NGO / Community Group", "Other"
        ], horizontal=not is_portrait)
        
        # Responsive layout for number inputs
        if is_portrait:
            children_no = st.number_input("Children Participating*", min_value=1, value=20)
            adults_present = st.number_input("Adults Present*", min_value=1, value=2)
        else:
            col1, col2 = st.columns(2)
            with col1:
                children_no = st.number_input("Children Participating*", min_value=1, value=20)
            with col2:
                adults_present = st.number_input("Adults Present*", min_value=1, value=2)
            
        children_age = st.text_input("Children Age(s)* (e.g., 4–6, 7–9)", placeholder="4-6 years")
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

        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>Your Ratings (1-5 scale)</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:{colors['text']}; font-size: {'14px' if is_portrait else '16px'};'>1 = Needs Improvement, 3 = Satisfactory, 5 = Excellent</p>", unsafe_allow_html=True)
        
        ratings = {}
        for cat in categories:
            st.markdown(f"<strong style='color:{colors['text']}; font-size: {'14px' if is_portrait else '16px'};'>{cat}</strong>", unsafe_allow_html=True)
            ratings[cat] = st.slider("", 1, 5, 3, key=cat, label_visibility='collapsed')
            st.markdown(f"<div style='color:{colors['text']}; display: flex; justify-content: space-between; margin-top: -15px; font-size: {'12px' if is_portrait else '14px'};'>"
                        "<span>1 (Poor)</span><span>2</span><span>3 (OK)</span><span>4</span><span>5 (Excellent)</span></div>", 
                        unsafe_allow_html=True)

        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>Your Feedback</h3>", unsafe_allow_html=True)
        q1 = st.text_area("What did the children enjoy most?*", placeholder="Describe what activities or aspects the children enjoyed")
        q2 = st.text_area("Any moments of curiosity, creativity, or learning?", placeholder="Share any special moments you observed")
        q3 = st.text_area("How did this support your teaching goals?", placeholder="Explain how the experience aligned with your educational objectives")
        q4 = st.text_area("Suggestions to improve future visits", placeholder="Your ideas for making Play Africa even better")
        q5 = st.text_area("Would you recommend Play Africa? Why?*", placeholder="Please share your recommendation thoughts")

        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>Future Collaboration</h3>", unsafe_allow_html=True)
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
                if save_submission(entry):
                    st.success("Thank you for your feedback!")
                    st.balloons()
                    
                    st.markdown(f"""
                    <div style='
                        background: {colors['card_bg']};
                        border-radius: 10px;
                        padding: {'15px' if is_portrait else '20px'};
                        margin-top: {'15px' if is_portrait else '20px'};
                    '>
                        <h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>Thank You!</h3>
                        <p style='color:{colors['text']}; font-size: {'14px' if is_portrait else '16px'};'>Your feedback has been submitted successfully. We truly appreciate you taking the time to help us improve Play Africa.</p>
                    </div>
                    """, unsafe_allow_html=True)

def show_dashboard() -> None:
    """Display admin dashboard with responsive layout"""
    colors = get_theme_colors()
    is_portrait = detect_orientation()
    
    st.markdown(f"<h1 style='color:{colors['text']}; font-size: {'24px' if is_portrait else '32px'};'>Feedback Dashboard</h1>", unsafe_allow_html=True)
    
    # Create backup when dashboard is accessed
    if create_backup():
        st.toast("Backup created successfully", icon="✅")
    
    df = load_submissions()
    if df.empty:
        st.info("No feedback submitted yet. Please check back later!")
        return

    rating_columns = ["engagement", "safety", "cleanliness", "fun", "learning", "planning", "safety_space"]
    for col in rating_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

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

    averages = {}
    for label, col in categories_labels:
        averages[label] = round(df[col].mean(), 2) if total > 0 else 0

    st.markdown(f"<h2 style='color:{colors['text']}; font-size: {'20px' if is_portrait else '24px'};'>Overview Metrics</h2>", unsafe_allow_html=True)
    
    # Responsive metrics layout
    if is_portrait:
        # Stack metrics vertically in portrait
        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 15px;
            '>
                <div style='font-size: 14px; color: {colors['metric_label']};'>Total Feedback</div>
                <div style='font-size: 24px; font-weight: bold; color: {colors['metric_value']};'>{total}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 15px;
            '>
                <div style='font-size: 14px; color: {colors['metric_label']};'>Avg. Engagement</div>
                <div style='font-size: 24px; font-weight: bold; color: {colors['metric_value']};'>{averages.get('Overall experience', 0)}/5</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 15px;
            '>
                <div style='font-size: 14px; color: {colors['metric_label']};'>Avg. Safety</div>
                <div style='font-size: 24px; font-weight: bold; color: {colors['metric_value']};'>{averages.get('Facilitator professionalism', 0)}/5</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Horizontal layout in landscape
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

    # Additional metrics - responsive layout
    metric_pairs = [
        ("Avg. Fun", "Welcoming atmosphere"),
        ("Avg. Learning", "Learning relevance"),
        ("Avg. Planning", "Pre-visit communication"),
        ("Avg. Comfort", "Space comfort")
    ]
    
    if is_portrait:
        # Stack metrics vertically in portrait
        for title, key in metric_pairs:
            st.markdown(
                f"""
                <div style='
                    background: {colors['card_bg']};
                    border-radius: 10px;
                    padding: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                    margin-bottom: 15px;
                '>
                    <div style='font-size: 14px; color: {colors['metric_label']};'>{title}</div>
                    <div style='font-size: 20px; font-weight: bold; color: {colors['metric_value']};'>{averages.get(key, 0)}/5</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        # Horizontal layout in landscape
        cols = st.columns(4)
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
                    unsafe_allow_html=True )


    st.markdown(f"<h2 style='color:{colors['text']}; font-size: {'20px' if is_portrait else '24px'};'>Feedback Analysis</h2>", unsafe_allow_html=True)
    
    # Rating trends over time
    with st.expander("📈 Rating Trends Over Time", expanded=True):
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            avg_ratings = df.groupby('date')[rating_columns].mean().reset_index()
            
            # Melt for Altair
            melted = avg_ratings.melt('date', var_name='category', value_name='rating')
            
            # Create chart
            chart = alt.Chart(melted).mark_line(point=True).encode(
                x='date:T',
                y=alt.Y('rating:Q', scale=alt.Scale(domain=[1, 5])),
                color='category:N',
                tooltip=['date', 'category', 'rating']
            ).properties(
                width=600 if not is_portrait else 'container',
                height=300
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.error(f"Could not generate trends chart: {str(e)}")

    # Group type distribution
    with st.expander("👥 Group Type Distribution", expanded=False):
        if 'group_type' in df.columns:
            group_counts = df['group_type'].value_counts().reset_index()
            group_counts.columns = ['Group Type', 'Count']
            
            chart = alt.Chart(group_counts).mark_bar().encode(
                x='Count:Q',
                y=alt.Y('Group Type:N', sort='-x'),
                tooltip=['Group Type', 'Count']
            ).properties(
                width=600 if not is_portrait else 'container',
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Group type data not available")

    # Word cloud of comments
    with st.expander("💬 Common Feedback Themes", expanded=False):
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            
            all_comments = " ".join(df['comments'].apply(lambda x: json.loads(x)['enjoyed'].dropna()))
            
            if all_comments:
                wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_comments)
                
                fig, ax = plt.subplots()
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                
                st.pyplot(fig, use_container_width=True)
            else:
                st.info("No comments available for word cloud")
        except ImportError:
            st.warning("WordCloud library not installed. Install with: pip install wordcloud")
        except Exception as e:
            st.error(f"Error generating word cloud: {str(e)}")

    st.markdown(f"<h2 style='color:{colors['text']}; font-size: {'20px' if is_portrait else '24px'};'>Feedback Management</h2>", unsafe_allow_html=True)
    
    # Feedback table with actions
    with st.expander("📝 View All Feedback", expanded=False):
        st.markdown(f"<p style='color:{colors['text']};'>Showing {len(df)} submissions</p>", unsafe_allow_html=True)
        
        # Display a subset of columns for better readability
        display_cols = ['timestamp', 'school', 'group_type', 'children_no', 'programme']
        display_df = df[display_cols].copy()
        display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Show the table with checkboxes for selection
        selected_indices = []
        for i, row in display_df.iterrows():
            col1, col2 = st.columns([1, 8])
            with col1:
                selected = st.checkbox("", key=f"select_{i}")
            with col2:
                st.markdown(f"""
                <div style='
                    background: {colors['card_bg']};
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 10px;
                '>
                    <strong>{row['school']}</strong><br>
                    <small>Date: {row['timestamp']}</small><br>
                    <small>Group: {row['group_type']} ({row['children_no']} children)</small><br>
                    <small>Program: {json.loads(row['programme'])[0] if row['programme'] else 'N/A'}</small>
                </div>
                """, unsafe_allow_html=True)
            
            if selected:
                selected_indices.append(i)
        
        # Action buttons for selected items
        if selected_indices:
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Delete Selected", help="Permanently delete selected feedback entries"):
                    if show_delete_confirmation_dialog(len(selected_indices)):
                        success_count = 0
                        for idx in sorted(selected_indices, reverse=True):
                            if delete_submission(idx):
                                success_count += 1
                        if success_count > 0:
                            st.success(f"Deleted {success_count} feedback entries")
                            st.rerun()
            
            with col2:
                st.download_button(
                    label="📥 Export Selected",
                    data=df.iloc[selected_indices].to_csv(index=False),
                    file_name=f"play_africa_feedback_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    # Deleted entries management
    with st.expander("🗑️ Deleted Entries (Admin Only)", expanded=False):
        if st.session_state.role != "admin":
            st.warning("This section is only accessible to administrators")
        else:
            deleted_df = load_deleted_entries()
            
            if deleted_df.empty:
                st.info("No deleted entries to display")
            else:
                st.markdown(f"<p style='color:{colors['text']};'>Showing {len(deleted_df)} deleted submissions</p>", unsafe_allow_html=True)
                
                # Display deleted entries
                selected_deleted_indices = []
                for i, row in deleted_df.iterrows():
                    col1, col2 = st.columns([1, 8])
                    with col1:
                        selected = st.checkbox("", key=f"deleted_select_{i}")
                    with col2:
                        st.markdown(f"""
                        <div style='
                            background: #ffebee;
                            border-radius: 8px;
                            padding: 12px;
                            margin-bottom: 10px;
                        '>
                            <strong>{row['school']}</strong><br>
                            <small>Date: {row['timestamp']}</small><br>
                            <small>Group: {row['group_type']} ({row['children_no']} children)</small><br>
                            <small>Program: {json.loads(row['programme'])[0] if row['programme'] else 'N/A'}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if selected:
                        selected_deleted_indices.append(i)
                
                # Restore button
                if selected_deleted_indices:
                    st.markdown("---")
                    if st.button("♻️ Restore Selected", help="Restore selected entries from trash"):
                        if show_restore_confirmation_dialog(len(selected_deleted_indices)):
                            success_count = 0
                            for idx in sorted(selected_deleted_indices, reverse=True):
                                if restore_deleted_entry(idx):
                                    success_count += 1
                            if success_count > 0:
                                st.success(f"Restored {success_count} entries")
                                st.rerun()

def show_admin_tools() -> None:
    """Display admin tools section"""
    if st.session_state.role != "admin":
        st.warning("This section is only accessible to administrators")
        return
    
    colors = get_theme_colors()
    is_portrait = detect_orientation()
    
    st.markdown(f"<h1 style='color:{colors['text']}; font-size: {'24px' if is_portrait else '32px'};'>Administrator Tools</h1>", unsafe_allow_html=True)
    
    with st.expander("🔧 User Management", expanded=True):
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>Manage Users</h3>", unsafe_allow_html=True)
        
        try:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        except Exception as e:
            st.error(f"Error loading users: {str(e)}")
            return
        
        # Display current users
        st.markdown(f"<h4 style='color:{colors['text']}; font-size: {'16px' if is_portrait else '20px'};'>Current Users</h4>", unsafe_allow_html=True)
        
        user_cols = st.columns([3, 2, 2, 2, 1])
        user_cols[0].markdown("**Username**")
        user_cols[1].markdown("**Role**")
        user_cols[2].markdown("**Created**")
        user_cols[3].markdown("**Last Login**")
        user_cols[4].markdown("**Actions**")
        
        for username, user_data in users.items():
            if username == st.session_state.username:
                continue  # Skip current user
                
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].write(username)
            cols[1].write(user_data.get("role", "visitor"))
            cols[2].write(user_data.get("created", "N/A"))
            cols[3].write(user_data.get("last_login", "N/A"))
            
            with cols[4]:
                if st.button("🗑️", key=f"del_{username}"):
                    if st.session_state.role == "admin":
                        del users[username]
                        with open(USERS_FILE, "w") as f:
                            json.dump(users, f)
                        st.success(f"User {username} deleted")
                        st.rerun()
                    else:
                        st.warning("Only admins can delete users")
        
        # Add new user form
        st.markdown(f"<h4 style='color:{colors['text']}; font-size: {'16px' if is_portrait else '20px'};'>Add New User</h4>", unsafe_allow_html=True)
        
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["visitor", "admin"])
            
            if st.form_submit_button("Add User"):
                if new_username and new_password:
                    if new_username in users:
                        st.error("Username already exists")
                    else:
                        users[new_username] = {
                            "password": hashlib.sha256(new_password.encode()).hexdigest(),
                            "role": new_role,
                            "created": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        with open(USERS_FILE, "w") as f:
                            json.dump(users, f)
                        st.success(f"User {new_username} added")
                        st.rerun()
                else:
                    st.error("Please provide both username and password")
    
    with st.expander("💾 Backup Management", expanded=False):
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>Data Backups</h3>", unsafe_allow_html=True)
        
        # List available backups
        backups = []
        if os.path.exists(BACKUP_DIR):
            backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
        
        if not backups:
            st.info("No backups available")
        else:
            st.markdown(f"<p style='color:{colors['text']};'>Available backups:</p>", unsafe_allow_html=True)
            
            selected_backup = st.selectbox("Select backup", backups, label_visibility="collapsed")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Preview Backup"):
                    try:
                        backup_path = os.path.join(BACKUP_DIR, selected_backup)
                        backup_df = pd.read_csv(backup_path)
                        st.dataframe(backup_df.head())
                    except Exception as e:
                        st.error(f"Error loading backup: {str(e)}")
            
            with col2:
                if st.button("🔄 Restore Backup"):
                    try:
                        backup_path = os.path.join(BACKUP_DIR, selected_backup)
                        shutil.copy2(backup_path, SUBMISSIONS_FILE)
                        st.success("Backup restored successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error restoring backup: {str(e)}")
            
            st.download_button(
                label="📥 Download Backup",
                data=open(os.path.join(BACKUP_DIR, selected_backup), "rb").read(),
                file_name=selected_backup,
                mime="text/csv"
            )
            
            if st.button("🗑️ Delete Backup", type="secondary"):
                try:
                    os.remove(os.path.join(BACKUP_DIR, selected_backup))
                    st.success("Backup deleted")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting backup: {str(e)}")
    
    with st.expander("⚙️ System Settings", expanded=False):
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_portrait else '24px'};'>System Configuration</h3>", unsafe_allow_html=True)
        
        # QR code settings
        qr_url = st.text_input("Feedback Form URL", value="https://play-africa-dashboard.streamlit.app/")
        
        # Export all data
        st.markdown("---")
        st.markdown(f"<h4 style='color:{colors['text']}; font-size: {'16px' if is_portrait else '20px'};'>Data Export</h4>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Export Current Data",
                data=load_submissions().to_csv(index=False),
                file_name=f"play_africa_feedback_current_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.download_button(
                label="📥 Export All Data (Incl. Deleted)",
                data=pd.concat([load_submissions(), load_deleted_entries()]).to_csv(index=False),
                file_name=f"play_africa_feedback_full_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

def main() -> None:
    """Main application function with responsive navigation"""
    # Configure page
    st.set_page_config(
        page_title="Play Africa Feedback System",
        page_icon=":children_crossing:",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for responsive design
    st.markdown("""
    <style>
        /* Base responsive styles */
        @media (max-width: 768px) {
            /* Mobile styles */
            .sidebar .sidebar-content {
                width: 100% !important;
            }
            div[data-testid="stSidebar"] {
                width: 100% !important;
            }
            .block-container {
                padding-top: 2rem;
            }
        }
        
        /* Theme colors */
        :root {
            --text-color: #2E86AB;
            --background-color: #f0f2f6;
            --card-bg-color: #ffffff;
            --metric-value-color: #3FB0AC;
            --metric-label-color: #555555;
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            :root {
                --text-color: #ffffff;
                --background-color: #121212;
                --card-bg-color: #1e1e1e;
                --metric-value-color: #3FB0AC;
                --metric-label-color: #aaaaaa;
            }
        }
        
        /* Consistent styling for all buttons */
        button {
            transition: all 0.3s ease !important;
        }
        button:hover {
            transform: scale(1.05) !important;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--background-color);
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
    
    # Check authentication
    if not authenticate():
        return
    
    # Navigation based on role
    pages = {
        "🏠 Home": show_home,
        "📝 Feedback Form": show_feedback,
        "📊 Dashboard": show_dashboard,
    }
    
    # Add admin tools if user is admin
    if st.session_state.role == "admin":
        pages["🛠️ Admin Tools"] = show_admin_tools
    
    # Responsive sidebar navigation
    is_portrait = detect_orientation()
    
    if is_portrait:
        # Mobile-friendly top navigation
        st.markdown("""
        <style>
            .mobile-nav {
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin-bottom: 15px;
            }
            .mobile-nav button {
                flex: 1;
                min-width: 100px;
                padding: 8px;
                font-size: 14px;
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="mobile-nav">', unsafe_allow_html=True)
        for page_name in pages:
            if st.button(page_name):
                st.session_state.current_page = page_name
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add logout button
        if st.button("🔒 Logout"):
            logout()
    else:
        # Desktop sidebar navigation
        with st.sidebar:
            st.markdown(f"""
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='color: var(--text-color);'>Play Africa</h3>
                <p style='color: var(--text-color); font-size: 14px;'>
                    Logged in as <strong>{st.session_state.username}</strong><br>
                    ({st.session_state.role})
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            for page_name in pages:
                if st.button(page_name, use_container_width=True):
                    st.session_state.current_page = page_name
            
            st.markdown("---")
            if st.button("🔒 Logout", use_container_width=True):
                logout()
            
            # QR code in sidebar for quick access
            if st.session_state.role == "admin":
                st.markdown("---")
                st.markdown("**Quick Access QR Code**")
                qr_url = "https://play-africa-dashboard.streamlit.app/"
                show_qr_code(qr_url)
    
    # Initialize current page if not set
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Home"
    
    # Show the selected page
    pages[st.session_state.current_page]()

if __name__ == "__main__":
    main()