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
import sounddevice as sd
from scipy.io.wavfile import write
import platform

# Constants
DATA_DIR = "data"
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.csv")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
DELETED_ENTRIES_FILE = os.path.join(DATA_DIR, "deleted_entries.csv")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# Audio recording parameters
fs = 44100  # Sample rate
seconds = 30  # Maximum recording duration

# Device detection
def is_mobile():
    """Enhanced mobile device detection"""
    try:
        # Check user agent for mobile devices
        user_agent = st.query_params.get("user_agent", [""])[0].lower()
        mobile_keywords = ['mobi', 'android', 'iphone', 'ipad', 'ipod']
        if any(keyword in user_agent for keyword in mobile_keywords):
            return True
        
        # Check screen dimensions
        if st.query_params.get("screen_width", [""])[0]:
            screen_width = int(st.query_params.get("screen_width", ["768"])[0])
            return screen_width < 768
            
        return False
    except:
        return False

# Responsive layout functions
def responsive_columns(default_cols=2):
    """Create responsive columns based on device"""
    if is_mobile():
        cols = []
        for i in range(default_cols):
            with st.container():
                cols.append(None)  # Using containers instead of columns
        return cols
    return st.columns(default_cols)

def responsive_expander(label, expanded=True):
    """Create responsive expander with different defaults"""
    if is_mobile():
        return st.expander(label, expanded=False)  # Collapsed by default on mobile
    return st.expander(label, expanded=expanded)

def mobile_adjusted_text_input(label, value="", max_chars=None, key=None, placeholder=""):
    """Text input with mobile adjustments"""
    if is_mobile():
        return st.text_input(label, value, max_chars=max_chars, key=key, placeholder=placeholder)
    return st.text_input(label, value, max_chars=max_chars, key=key, placeholder=placeholder)

def mobile_adjusted_text_area(label, value="", height=100, key=None, placeholder=""):
    """Text area with mobile adjustments"""
    if is_mobile():
        return st.text_area(label, value, height=max(80, height//2), key=key, placeholder=placeholder)
    return st.text_area(label, value, height=height, key=key, placeholder=placeholder)

# Initialize files if they don't exist
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({
            "admin": {
                "password": hashlib.sha256("Playafrica@2025!*".encode()).hexdigest(),
                "role": "admin"
            },
            "Guest": {
                "password": hashlib.sha256("Guest@2025".encode()).hexdigest(),
                "role": "Guest"
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
        # Escape any commas in text fields
        for key, value in entry.items():
            if isinstance(value, str) and ',' in value:
                entry[key] = f'"{value}"'
                
        df = pd.DataFrame([entry])
        if os.path.exists(SUBMISSIONS_FILE):
            df.to_csv(SUBMISSIONS_FILE, mode='a', header=False, index=False, escapechar='\\')
        else:
            df.to_csv(SUBMISSIONS_FILE, index=False, escapechar='\\')
        return True
    except Exception as e:
        st.error(f"Error saving submission: {str(e)}")
        return False

def load_submissions() -> pd.DataFrame:
    """Load all submissions with error handling"""
    try:
        if os.path.exists(SUBMISSIONS_FILE):
            return pd.read_csv(SUBMISSIONS_FILE, on_bad_lines='skip')
    except Exception as e:
        st.error(f"Error loading submissions: {str(e)}")
    return pd.DataFrame()

def load_deleted_entries() -> pd.DataFrame:
    """Load deleted entries with error handling"""
    try:
        if os.path.exists(DELETED_ENTRIES_FILE):
            return pd.read_csv(DELETED_ENTRIES_FILE, on_bad_lines='skip')
    except Exception as e:
        st.error(f"Error loading deleted entries: {str(e)}")
    return pd.DataFrame()

def delete_submission(index: int, permanent: bool = False) -> bool:
    """Delete a submission by its index with backup"""
    try:
        df = load_submissions()
        if not df.empty and 0 <= index < len(df):
            if not permanent:
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
    """Display QR code with admin-only download option"""
    if not data:
        st.warning("No URL provided for QR code generation")
        return
    
    qr_img_base64, qr_img = generate_qr_code(data)
    if not qr_img_base64 or not qr_img:
        return
    
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <img src="data:image/png;base64,{qr_img_base64}" width="200">
        <p style="font-size: 14px; margin-top: 10px;">
            Scan to access feedback form<br>
            Point your camera at the QR code
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
        'metric_label': 'var(--metric-label-color)',
        'primary': '#2E86AB',
        'secondary': '#3FB0AC',
        'accent': '#F18F01'
    }

def show_confirmation_dialog(action: str, count: int) -> bool:
    """Show confirmation dialog for deletion or restoration"""
    with st.expander(f"⚠️ Confirm {action}", expanded=True):
        st.warning(f"You are about to {action.lower()} {count} feedback submission(s). This action cannot be undone.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Confirm {action}", type="primary"):
                return True
        with col2:
            if st.button("❌ Cancel"):
                return False
    return False

def play_audio(filename: str) -> None:
    """Play audio file"""
    try:
        if os.path.exists(filename):
            st.audio(filename, format='audio/wav')
        else:
            st.warning("Audio file not found")
    except Exception as e:
        st.error(f"Error playing audio: {str(e)}")

def authenticate() -> bool:
    """Handle user authentication with enhanced UI"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'username' not in st.session_state:
        st.session_state.username = None

    if not st.session_state.authenticated:
        try:
            # Load and process images
            moonkids_img = Image.open("play_africa_mag.jpg")
            paintingkids_img = Image.open("play2.jpg")
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

        # Enhanced Login UI
        st.markdown("""
        <style>
            .login-container {
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }
            .login-header {
                text-align: center;
                padding: 30px 0;
                margin-bottom: 30px;
                background: linear-gradient(135deg, #2E86AB, #3FB0AC);
                color: white;
                font-size: 42px;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 3px;
                border-radius: 12px;
                box-shadow: 0 8px 15px rgba(0,0,0,0.1);
            }
            .login-card {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .login-btn {
                background: linear-gradient(135deg, #2E86AB, #3FB0AC) !important;
                border: none !important;
                color: white !important;
                font-weight: bold !important;
                padding: 12px 24px !important;
                border-radius: 8px !important;
                font-size: 16px !important;
                transition: all 0.3s ease !important;
            }
            .login-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .image-card {
                display: flex;
                flex-direction: column;
                align-items: center;
                margin: 15px;
                padding: 20px;
                background: rgba(255,255,255,0.9);
                border-radius: 12px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .image-card:hover {
                transform: translateY(-5px);
            }
            .image-caption {
                text-align: center;
                margin-top: 15px;
                font-size: 16px;
                color: #2E86AB;
                font-weight: 600;
                max-width: 400px;
            }
            .quote-text {
                text-align: center;
                margin-top: 40px;
                font-size: 18px;
                color: #555;
                font-style: italic;
                padding: 20px;
                border-top: 1px solid #eee;
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                PLAY AFRICA FEEDBACK PORTAL
            </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="image-card">
                <img src="data:image/jpeg;base64,{moonkids_base64}" width="400" style="border-radius: 8px;">
                <div class="image-caption">
                    "Children learn as they play. Most importantly, in play, children learn how to learn." — O. Fred Donaldson
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="image-card">
                <img src="data:image/jpeg;base64,{paintingkids_base64}" width="400" style="border-radius: 8px;">
                <div class="image-caption">
                    "Almost all creativity involves purposeful play" - Abraham Maslow
                </div>
            </div>
            """, unsafe_allow_html=True)

        with st.container():
            st.markdown("""
            <div class="login-card">
                <h2 style="text-align: center; color: #2E86AB; margin-bottom: 25px;">Welcome! Please log in to continue</h2>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                
                if st.form_submit_button("Login", type="primary", help="Enter your credentials to access the feedback system"):
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
            
            st.markdown("""
            </div>
            <div class="quote-text">
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
    """Display home page"""
    colors = get_theme_colors()
    col1, col2 = st.columns([1, 1])
    with col1:
        try:
            st.image("Play_Africa.png", width=300)
        except Exception as e:
            st.warning(f"Logo image not found: {str(e)}")
    with col2:
        json_data = load_lottiefile("lottie_kid2.json")
        if json_data:
            st_lottie(json_data, height=200)
        else:
            st.write("Lottie animation not available.")
    
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
    
    if not st.session_state.authenticated or st.session_state.role == "visitor":
        st.markdown("---")
        st.markdown("<h3 style='text-align: center;'>Visitor Feedback Access</h3>", unsafe_allow_html=True)
        
        # Replace with your actual URL
        qr_url = "https://your-streamlit-app-url.com/Visitor%20Feedback"
        show_qr_code(qr_url)

def show_feedback() -> None:
    """Display feedback form with voice recording option"""
    colors = get_theme_colors()
    
    # Responsive title
    if is_mobile():
        st.markdown(f"<h2 style='color:{colors['text']}'>Play Africa Feedback</h2>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 style='color:{colors['text']}'>Play Africa Visit Feedback</h1>", unsafe_allow_html=True)
    
    # Form instructions with mobile-optimized expander
    with responsive_expander("Form Instructions", expanded=False):
        st.markdown(f"""
        <div style='color:{colors['text']}; font-size: {'14px' if is_mobile() else '16px'}'>
            <p>Please share your experience at Play Africa.</p>
            <p><strong>All fields marked with * are required.</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Voice recording section with responsive layout
    st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>Children's Voice</h3>", unsafe_allow_html=True)
    
    if is_mobile():
        # Vertical layout for mobile
        record_col, stop_col = st.container(), st.container()
        
        with record_col:
            if st.button("🎤 Start Recording", key="start_recording_mobile", 
                        help="Tap to start recording (max 30 seconds)"):
                st.session_state.recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
                st.session_state.recording_started = True
                st.toast("Recording started... Speak now!")
        
        with stop_col:
            if st.button("⏹️ Stop Recording", disabled=not st.session_state.get('recording_started', False),
                        key="stop_recording_mobile", help="Tap to stop recording"):
                sd.stop()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.audio_file = os.path.join(AUDIO_DIR, f"recording_{timestamp}.wav")
                write(st.session_state.audio_file, fs, st.session_state.recording)
                st.success("Recording saved!")
                st.session_state.recording_started = False
    else:
        # Horizontal layout for desktop
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎤 Start Recording", key="start_recording_desktop"):
                st.session_state.recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
                st.session_state.recording_started = True
                st.toast("Recording started... Speak now!")
        
        with col2:
            if st.button("⏹️ Stop Recording", disabled=not st.session_state.get('recording_started', False),
                        key="stop_recording_desktop"):
                sd.stop()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.audio_file = os.path.join(AUDIO_DIR, f"recording_{timestamp}.wav")
                write(st.session_state.audio_file, fs, st.session_state.recording)
                st.success("Recording saved!")
                st.session_state.recording_started = False
    
    # Playback if recording exists
    if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
        st.audio(st.session_state.audio_file, format='audio/wav')
    
    # Main feedback form with responsive fields
    with st.form("feedback_form"):
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>About Your Group</h3>", unsafe_allow_html=True)
        
        # Responsive layout for form fields
        if is_mobile():
            school = mobile_adjusted_text_input("School/Organization/Group*", placeholder="Your organization")
            
            group_type = st.selectbox("Type of Group*", [
                "Preschool / ECD Centre", 
                "Primary School (Grade R–3)",
                "Primary School (Grade 4–7)", 
                "Special Needs School",
                "NGO / Community Group", 
                "Other"
            ], key="group_type_mobile")
            
            col1, col2 = st.columns(2)
            with col1:
                children_no = st.number_input("Children*", min_value=1, value=5, key="children_mobile")
            with col2:
                children_age = mobile_adjusted_text_input("Ages*", placeholder="4-6", key="ages_mobile")
            
            adults_present = st.number_input("Adults*", min_value=1, value=2, key="adults_mobile")
            visit_date = st.date_input("Visit Date*", value=datetime.now(), key="date_mobile")
            
            programme = st.multiselect("Experience Type*", [
                "Play Africa at Constitution Hill", 
                "Outreach Programme",
                "Special Event or Pop‑Up", 
                "Other"
            ], key="program_mobile")
        else:
            # Desktop layout
            col1, col2 = st.columns(2)
            with col1:
                school = st.text_input("School/Organization/Group*", placeholder="Your organization name", key="school_desktop")
            with col2:
                group_type = st.radio("Type of Group*", [
                    "Preschool / ECD Centre", 
                    "Primary School (Grade R–3)",
                    "Primary School (Grade 4–7)", 
                    "Special Needs School",
                    "NGO / Community Group", 
                    "Other"
                ], key="group_type_desktop")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                children_no = st.number_input("Children Participating*", min_value=1, value=20, key="children_desktop")
            with col2:
                children_age = st.text_input("Children Age(s)*", placeholder="4-6 years", key="ages_desktop")
            with col3:
                adults_present = st.number_input("Adults Present*", min_value=1, value=2, key="adults_desktop")
            
            col1, col2 = st.columns(2)
            with col1:
                visit_date = st.date_input("Date of Visit*", value=datetime.now(), key="date_desktop")
            with col2:
                programme = st.multiselect("Type of Experience*", [
                    "Play Africa at Constitution Hill", 
                    "Outreach Programme",
                    "Special Event or Pop‑Up", 
                    "Other"
                ], key="program_desktop")

        # Ratings section
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>Your Ratings</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:{colors['text']}; font-size: {'14px' if is_mobile() else '16px'}'>1 = Needs Improvement, 3 = Satisfactory, 5 = Excellent</p>", unsafe_allow_html=True)
        
        categories = [
            "Overall experience for children",
            "Friendliness and professionalism of facilitators",
            "Level of engagement for children",
            "Inclusiveness and welcoming atmosphere",
            "Relevance of activities to children's learning",
            "Planning and communication before the visit",
            "Physical safety and comfort of the space"
        ]
        
        ratings = {}
        for cat in categories:
            if is_mobile():
                st.markdown(f"<strong style='color:{colors['text']}; font-size: 15px'>{cat}</strong>", unsafe_allow_html=True)
                ratings[cat] = st.slider("", 1, 5, 3, key=f"rating_{cat}_mobile", label_visibility='collapsed')
                st.markdown(f"<div style='color:{colors['text']}; display: flex; justify-content: space-between; margin-top: -15px; font-size: 14px'>"
                            "<span>1 (Poor)</span><span>3</span><span>5 (Excellent)</span></div>", 
                            unsafe_allow_html=True)
            else:
                st.markdown(f"<strong style='color:{colors['text']}'>{cat}</strong>", unsafe_allow_html=True)
                ratings[cat] = st.slider("", 1, 5, 3, key=f"rating_{cat}_desktop", label_visibility='collapsed')
                st.markdown(f"<div style='color:{colors['text']}; display: flex; justify-content: space-between; margin-top: -15px;'>"
                            "<span>1 (Poor)</span><span>2</span><span>3 (OK)</span><span>4</span><span>5 (Excellent)</span></div>", 
                            unsafe_allow_html=True)

        # Feedback questions
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>Your Feedback</h3>", unsafe_allow_html=True)
        
        q1 = mobile_adjusted_text_area("What did children enjoy most?*", placeholder="Describe what the children enjoyed", 
                                      height=100 if is_mobile() else 120, key="q1")
        q2 = mobile_adjusted_text_area("Moments of curiosity/learning?", placeholder="Share special moments", 
                                      height=80 if is_mobile() else 100, key="q2")
        q3 = mobile_adjusted_text_area("How did this support your teaching?", placeholder="Educational objectives", 
                                      height=80 if is_mobile() else 100, key="q3")
        q4 = mobile_adjusted_text_area("Suggestions for improvement", placeholder="Your ideas", 
                                      height=80 if is_mobile() else 100, key="q4")
        q5 = mobile_adjusted_text_area("Would you recommend us? Why?*", placeholder="Your recommendation", 
                                      height=100 if is_mobile() else 120, key="q5")

        # Future collaboration
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>Future Collaboration</h3>", unsafe_allow_html=True)
        
        if is_mobile():
            future_collab = st.selectbox("Interested in future collaboration?", ["Yes", "No", "Maybe"], key="collab_mobile")
            future_topics = mobile_adjusted_text_area("Topics you'd like us to explore?", placeholder="Specific themes", 
                                                    height=80, key="topics_mobile")
        else:
            col1, col2 = st.columns(2)
            with col1:
                future_collab = st.radio("Interested in future collaboration?", ["Yes", "No", "Maybe"], key="collab_desktop")
            with col2:
                future_topics = st.text_area("Topics/needs you'd like us to explore?", placeholder="Any specific themes or subjects", 
                                            height=100, key="topics_desktop")

        # Form submission button
        required_fields = [school, children_age, programme, q1, q5]
        
        submit_col = st.columns(1)
        with submit_col[0]:
            submitted = st.form_submit_button("Submit Feedback", type="primary", 
                                   use_container_width=True, 
                                   help="Tap to submit your feedback")
            if submitted:
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
                        "visit_date": visit_date.strftime("%Y-%m-%d"),
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
                        }),
                        "audio_file": st.session_state.audio_file if st.session_state.audio_file else "",
                        "device_type": "mobile" if is_mobile() else "desktop"
                    }
                    
                    if save_submission(entry):
                        st.success("Thank you for your feedback!")
                        st.balloons()
                        
                        # Clear the recording after submission
                        if 'audio_file' in st.session_state:
                            st.session_state.audio_file = None
                        
                        st.markdown(f"""
                        <div style='
                            background: {colors['card_bg']};
                            border-radius: 10px;
                            padding: {'12px' if is_mobile() else '20px'};
                            margin-top: 10px;
                        '>
                            <h3 style='color:{colors['text']}; font-size: {'16px' if is_mobile() else '18px'}'>Thank You!</h3>
                            <p style='color:{colors['text']}; font-size: {'14px' if is_mobile() else '16px'}'>
                                Your feedback has been submitted successfully.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

def show_dashboard() -> None:
    """Display admin dashboard with consolidated management"""
    colors = get_theme_colors()
    st.markdown(f"<h1 style='color:{colors['text']}'>Feedback Dashboard</h1>", unsafe_allow_html=True)
    
    # Create backup when dashboard is accessed
    if create_backup():
        st.toast("Backup created successfully", icon="✅")
    
    # Consolidated feedback management section
    st.markdown(f"<h2 style='color:{colors['text']}'>Feedback Management</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Active Feedback", "Deleted Feedback"])
    
    with tab1:
        df = load_submissions()
        if df.empty:
            st.info("No feedback submitted yet. Please check back later!")
        else:
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
            
            if 'Date' in display_df.columns:
                try:
                    display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            # Add index column for reference
            display_df['Index'] = df.index
            
            page_size = st.selectbox('Rows per page', [5, 10, 20, 50], index=1, key='active_page_size')
            page_number = st.number_input('Page', min_value=1, max_value=max(1, len(display_df)//page_size + 1), 
                                        value=1, key='active_page')
            start_idx = (page_number - 1) * page_size
            end_idx = min(start_idx + page_size, len(display_df))
            
            table_data = display_df.iloc[start_idx:end_idx] if not display_df.empty else display_df
            
            # Display the table with management options
            delete_indices = []
            for idx, row in table_data.iterrows():
                with st.expander(f"{row['Date']} - {row['Submitted by']}"):
                    st.write(f"Group Type: {row['Group Type']}")
                    st.write(f"Children: {row['Children']} (ages {row['Ages']})")
                    st.write(f"Adults: {row['Adults']}")
                    
                    # Show audio if available
                    audio_file = df.loc[row['Index'], 'audio_file'] if 'audio_file' in df.columns else None
                    if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
                        st.markdown("**Children's Voice Recording:**")
                        play_audio(audio_file)
                        st.download_button(
                            label="Download Recording",
                            data=open(audio_file, "rb").read(),
                            file_name=os.path.basename(audio_file),
                            mime="audio/wav",
                            key=f"audio_{row['Index']}"
                        )
                    
                    # Management buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Delete", key=f"del_{row['Index']}"):
                            delete_indices.append(row['Index'])
                    with col2:
                        if st.button("💀 Permanent Delete", key=f"perm_del_{row['Index']}"):
                            if show_confirmation_dialog("Permanent Delete", 1):
                                if delete_submission(row['Index'], permanent=True):
                                    st.success("Entry permanently deleted")
                                    st.rerun()
            
            # Bulk delete handling
            if delete_indices:
                if show_confirmation_dialog("Delete", len(delete_indices)):
                    success_count = 0
                    for index in sorted(delete_indices, reverse=True):
                        if delete_submission(index):
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"Successfully deleted {success_count} feedback submission(s)")
                        st.rerun()
                    else:
                        st.error("No submissions were deleted")
    
    with tab2:
        deleted_df = load_deleted_entries()
        if not deleted_df.empty:
            deleted_display = deleted_df[['timestamp', 'school', 'group_type']].copy()
            deleted_display = deleted_display.rename(columns={
                'timestamp': 'Date',
                'school': 'Submitted by',
                'group_type': 'Group Type'
            })
            
            if 'Date' in deleted_display.columns:
                try:
                    deleted_display['Date'] = pd.to_datetime(deleted_display['Date']).dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            deleted_display['Index'] = deleted_df.index
            
            deleted_page_size = st.selectbox('Rows per page', [5, 10], index=0, key='deleted_page_size')
            deleted_page_number = st.number_input('Page', min_value=1, 
                                                max_value=max(1, len(deleted_display)//deleted_page_size + 1), 
                                                value=1, key='deleted_page')
            deleted_start_idx = (deleted_page_number - 1) * deleted_page_size
            deleted_end_idx = min(deleted_start_idx + deleted_page_size, len(deleted_display))
            
            deleted_table_data = deleted_display.iloc[deleted_start_idx:deleted_end_idx]
            
            # Display deleted entries with restore options
            restore_indices = []
            for idx, row in deleted_table_data.iterrows():
                with st.expander(f"{row['Date']} - {row['Submitted by']}"):
                    st.write(f"Group Type: {row['Group Type']}")
                    
                    # Show audio if available
                    audio_file = deleted_df.loc[row['Index'], 'audio_file'] if 'audio_file' in deleted_df.columns else None
                    if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
                        st.markdown("**Children's Voice Recording:**")
                        play_audio(audio_file)
                        st.download_button(
                            label="Download Recording",
                            data=open(audio_file, "rb").read(),
                            file_name=os.path.basename(audio_file),
                            mime="audio/wav",
                            key=f"deleted_audio_{row['Index']}"
                        )
                    
                    # Management buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("↩️ Restore", key=f"restore_{row['Index']}"):
                            restore_indices.append(row['Index'])
                    with col2:
                        if st.button("💀 Permanent Delete", key=f"perm_del_deleted_{row['Index']}"):
                            if show_confirmation_dialog("Permanent Delete", 1):
                                if delete_submission(row['Index'], permanent=True):
                                    st.success("Entry permanently deleted")
                                    st.rerun()
            
            # Bulk restore handling
            if restore_indices:
                if show_confirmation_dialog("Restore", len(restore_indices)):
                    success_count = 0
                    for index in sorted(restore_indices, reverse=True):
                        if restore_deleted_entry(index):
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"Successfully restored {success_count} submission(s)")
                        st.rerun()
                    else:
                        st.error("No submissions were restored")
        else:
            st.info("No deleted entries to display")
    
    # Analytics section with all 7 metrics
    st.markdown(f"<h2 style='color:{colors['text']}'>Feedback Analytics</h2>", unsafe_allow_html=True)
    
    df = load_submissions()
    if not df.empty:
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
            ("Space comfort & safety", "safety_space")
        ]

        averages = {}
        for label, col in categories_labels:
            averages[label] = round(df[col].mean(), 2) if total > 0 else 0

        st.markdown(f"<h3 style='color:{colors['text']}'>Key Metrics</h3>", unsafe_allow_html=True)
        
        # Main metrics row with improved styling
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"""
                <div style='
                    background: {colors['card_bg']};
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    text-align: center;
                    margin-bottom: 20px;
                    border-left: 5px solid {colors['primary']};
                    transition: transform 0.3s ease;
                '>
                    <div style='font-size: 14px; color: {colors['metric_label']}; margin-bottom: 8px;'>Total Feedback</div>
                    <div style='font-size: 32px; font-weight: bold; color: {colors['primary']};'>{total}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""
                <div style='
                    background: {colors['card_bg']};
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    text-align: center;
                    margin-bottom: 20px;
                    border-left: 5px solid {colors['secondary']};
                    transition: transform 0.3s ease;
                '>
                    <div style='font-size: 14px; color: {colors['metric_label']}; margin-bottom: 8px;'>Avg. Experience</div>
                    <div style='font-size: 32px; font-weight: bold; color: {colors['secondary']};'>{averages.get('Overall experience', 0)}/5</div>
                    <div style='font-size: 12px; color: {colors['metric_label']}; margin-top: 4px;'>
                        {get_rating_stars(averages.get('Overall experience', 0))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            st.markdown(
                f"""
                <div style='
                    background: {colors['card_bg']};
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    text-align: center;
                    margin-bottom: 20px;
                    border-left: 5px solid {colors['accent']};
                    transition: transform 0.3s ease;
                '>
                    <div style='font-size: 14px; color: {colors['metric_label']}; margin-bottom: 8px;'>Avg. Facilitators</div>
                    <div style='font-size: 32px; font-weight: bold; color: {colors['accent']};'>{averages.get('Facilitator professionalism', 0)}/5</div>
                    <div style='font-size: 12px; color: {colors['metric_label']}; margin-top: 4px;'>
                        {get_rating_stars(averages.get('Facilitator professionalism', 0))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Secondary metrics row - now with 4 metrics
        cols = st.columns(4)
        metric_pairs = [
            ("Avg. Engagement", "Child engagement"),
            ("Avg. Atmosphere", "Welcoming atmosphere"),
            ("Avg. Learning", "Learning relevance"),
            ("Avg. Planning", "Pre-visit communication")
        ]
        
        for (title, key), col in zip(metric_pairs, cols):
            with col:
                st.markdown(
                    f"""
                    <div style='
                        background: {colors['card_bg']};
                        border-radius: 10px;
                        padding: 15px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        text-align: center;
                        margin-bottom: 20px;
                        border-top: 3px solid {colors['primary']};
                        transition: transform 0.3s ease;
                    '>
                        <div style='font-size: 14px; color: {colors['metric_label']}; margin-bottom: 6px;'>{title}</div>
                        <div style='font-size: 24px; font-weight: bold; color: {colors['metric_value']};'>{averages.get(key, 0)}/5</div>
                        <div style='font-size: 12px; color: {colors['metric_label']}; margin-top: 4px;'>
                            {get_rating_stars(averages.get(key, 0))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # Add the 7th metric in a new row
        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 20px;
                border-top: 3px solid {colors['accent']};
                transition: transform 0.3s ease;
                max-width: 300px;
                margin-left: auto;
                margin-right: auto;
            '>
                <div style='font-size: 14px; color: {colors['metric_label']}; margin-bottom: 6px;'>Avg. Space Safety</div>
                <div style='font-size: 24px; font-weight: bold; color: {colors['metric_value']};'>{averages.get('Space comfort & safety', 0)}/5</div>
                <div style='font-size: 12px; color: {colors['metric_label']}; margin-top: 4px;'>
                    {get_rating_stars(averages.get('Space comfort & safety', 0))}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Charts section
        chart_col1, chart_col2 = st.columns([2, 1])
        
        with chart_col1:
            chart_df = pd.DataFrame({
                'Category': [lbl for lbl, _ in categories_labels],
                'Average Rating': [averages[lbl] for lbl, _ in categories_labels]
            })
            
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
            
            text = bar_chart.mark_text(
                align='left',
                baseline='middle',
                dx=3
            ).encode(
                text=alt.Text('Average Rating:Q', format='.2f')
            )
            
            st.altair_chart(bar_chart + text, use_container_width=True)
        
        with chart_col2:
            st.markdown(f"<h4 style='color:{colors['text']}; text-align: center;'>Rating Distribution</h4>", unsafe_allow_html=True)
            
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

    # Export data section
    st.markdown(f"<h2 style='color:{colors['text']}'>Data Export</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export Current Feedback Data"):
            df = load_submissions()
            if not df.empty:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"play_africa_feedback_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv'
                )
            else:
                st.warning("No data to export")
    
    with col2:
        deleted_df = load_deleted_entries()
        if not deleted_df.empty:
            if st.button("Export Deleted Feedback Data"):
                csv = deleted_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"play_africa_deleted_feedback_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv'
                )
        else:
            st.warning("No deleted data to export")

def get_rating_stars(rating: float) -> str:
    """Generate star rating visualization"""
    full_stars = int(rating)
    half_star = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    stars = []
    for _ in range(full_stars):
        stars.append("★")
    for _ in range(half_star):
        stars.append("½")
    for _ in range(empty_stars):
        stars.append("☆")
    
    return " ".join(stars)

def main() -> None:
    """Main application function with responsive settings"""
    st.set_page_config(
        page_title="Play Africa Feedback",
        page_icon=":children_crossing:",
        layout="wide",
        initial_sidebar_state="auto"
    )

    # Add viewport meta tag manually for mobile responsiveness
    st.markdown(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">',
        unsafe_allow_html=True
    )

    # Initialize session state for mobile
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = is_mobile()
    
    # Enhanced CSS with better metrics styling
    st.markdown(f"""
    <style>
        /* Base styles */
        :root {{
            --text-color: black;
            --background-color: white;
            --card-bg-color: white;
            --metric-value-color: #333;
            --metric-label-color: #555;
            --primary-color: #2E86AB;
            --secondary-color: #3FB0AC;
            --accent-color: #F18F01;
        }}
        
        @media (prefers-color-scheme: dark) {{
            :root {{
                --text-color: white;
                --background-color: #0E1117;
                --card-bg-color: #262730;
                --metric-value-color: white;
                --metric-label-color: #AAAAAA;
                --primary-color: #3FB0AC;
                --secondary-color: #2E86AB;
                --accent-color: #F18F01;
            }}
        }}
        
        /* Metric card hover effects */
        div[data-testid="stMarkdownContainer"] > div {{
            transition: transform 0.3s ease;
        }}
        
        div[data-testid="stMarkdownContainer"] > div:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
        }}
        
        /* Star rating styling */
        .star-rating {{
            color: #F18F01;
            letter-spacing: 2px;
        }}
        
        /* Mobile-specific styles */
        @media (max-width: 768px) {{
            /* Form elements */
            .stTextInput input, .stTextArea textarea, .stSelectbox select {{
                font-size: 16px !important;
                padding: 12px !important;
            }}
            
            /* Buttons */
            .stButton>button {{
                width: 100% !important;
                padding: 12px !important;
                font-size: 16px !important;
            }}
            
            /* Containers */
            .main .block-container {{
                padding: 1rem !important;
            }}
            
            /* Sidebar */
            [data-testid="stSidebar"] {{
                width: 100% !important;
            }}
            
            /* Hide some decorative elements on mobile */
            .lottie-animation {{
                display: none;
            }}
            
            /* Adjust form spacing */
            .stForm {{
                padding: 0.5rem !important;
            }}
            
            /* Rating sliders */
            .stSlider {{
                margin-top: 0.5rem !important;
                margin-bottom: 0.5rem !important;
            }}
            
            /* Metric cards */
            div[data-testid="stMarkdownContainer"] > div {{
                padding: 15px !important;
                margin-bottom: 15px !important;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)

    # Initialize audio recording state
    if 'recording_started' not in st.session_state:
        st.session_state.recording_started = False
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None

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
        
        if st.session_state.authenticated:
            st.markdown(f"""
            <div style='font-size: 14px; color: var(--text-color); margin-bottom: 20px;'>
                Logged in as: <strong>{st.session_state.username}</strong> ({st.session_state.role})
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Logout"):
                logout()
        
        if st.session_state.role == "admin":
            menu = st.radio(
                "Navigation",
                ["Home", "Visitor Feedback", "Review Feedback"],
                label_visibility="collapsed"
            )
        else:
            menu = st.radio(
                "Navigation",
                ["Home", "Visitor Feedback"],
                label_visibility="collapsed"
            )
        
        st.markdown("---")
        
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