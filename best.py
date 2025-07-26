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
        'metric_label': 'var(--metric-label-color)'
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
                <h2 style="text-align: center; color: #2E86AB; margin-bottom: 25px;">Welcome Back!</h2>
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
    st.markdown(f"<h1 style='color:{colors['text']}'>Play Africa Visit Feedback</h1>", unsafe_allow_html=True)
    
    with st.expander("Form Instructions", expanded=False):
        st.markdown(f"""
        <div style='color:{colors['text']}'>
            <p>Please take a few minutes to share your experience at Play Africa. Your feedback helps us improve our programs and facilities.</p>
            <p><strong>All fields marked with * are required.</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Voice recording section (outside the form)
    st.markdown(f"<h3 style='color:{colors['text']}'>Children's Voice</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{colors['text']}'>Let the children record their thoughts about their experience (optional)</p>", unsafe_allow_html=True)
    
    # Initialize audio_file in session state if it doesn't exist
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None
    
    # Recording controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎤 Start Recording"):
            st.session_state.recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
            st.session_state.recording_started = True
            st.toast("Recording started... Speak now!")
    
    with col2:
        if st.button("⏹️ Stop Recording", disabled=not st.session_state.get('recording_started', False)):
            sd.stop()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.audio_file = os.path.join(AUDIO_DIR, f"recording_{timestamp}.wav")
            write(st.session_state.audio_file, fs, st.session_state.recording)
            st.success("Recording saved!")
            st.session_state.recording_started = False
    
    # Playback if recording exists
    if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
        st.audio(st.session_state.audio_file, format='audio/wav')
    
    # Main feedback form
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
                    "audio_file": st.session_state.audio_file if st.session_state.audio_file else ""
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
                        padding: 20px;
                        margin-top: 20px;
                    '>
                        <h3 style='color:{colors['text']}'>Thank You!</h3>
                        <p style='color:{colors['text']}'>Your feedback has been submitted successfully. We truly appreciate you taking the time to help us improve Play Africa.</p>
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
    
    # Analytics section
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
            ("Space comfort", "safety_space")
        ]

        averages = {}
        for label, col in categories_labels:
            averages[label] = round(df[col].mean(), 2) if total > 0 else 0

        st.markdown(f"<h3 style='color:{colors['text']}'>Key Metrics</h3>", unsafe_allow_html=True)
        
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

def main() -> None:
    """Main application function"""
    st.set_page_config(
        page_title="Play Africa Feedback",
        page_icon=":children_crossing:",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize audio recording state
    if 'recording_started' not in st.session_state:
        st.session_state.recording_started = False
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None

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
        
        .metric-card {
            transition: transform 0.2s;
        }
        
        .metric-card:hover {
            transform: scale(1.02);
        }
        
        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input, .stSelectbox select {
            background-color: var(--card-bg-color) !important;
            color: var(--text-color) !important;
            border: 1px solid rgba(0,0,0,0.1) !important;
        }
        
        .stDataFrame {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        [data-testid="stSidebar"] {
            background-color: var(--card-bg-color) !important;
        }
        
        @media (max-width: 768px) {
            .stDataFrame {
                width: 100% !important;
            }
            
            .metric-card {
                margin-bottom: 15px !important;
            }
        }
        
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
        
        /* Custom styles for confirmation dialogs */
        .confirmation-dialog {
            border-left: 5px solid #FF4B4B;
            padding: 1rem;
            margin-bottom: 1rem;
            background-color: rgba(255, 75, 75, 0.1);
        }
        
        /* Audio recording button styles */
        .audio-btn {
            background: #FF4B4B !important;
            color: white !important;
            border-radius: 50% !important;
            width: 50px !important;
            height: 50px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 20px !important;
        }
    </style>
    """, unsafe_allow_html=True)

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