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
import platform
import uuid

# Constants - using absolute paths for reliability
DATA_DIR = os.path.abspath("data")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.csv")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
DELETED_ENTRIES_FILE = os.path.join(DATA_DIR, "deleted_entries.csv")

# Ensure directories exist with proper permissions
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# Define expected columns for submissions, including 'id' as first column
EXPECTED_COLUMNS = [
    'id', 'timestamp', 'school', 'group_type', 'children_no', 'children_age',
    'adults_present', 'visit_date', 'programme', 'engagement', 'safety',
    'cleanliness', 'fun', 'learning', 'planning', 'safety_space', 'comments',
    'audio_file', 'device_type'
]

def initialize_data_files():
    """Initialize data files with proper structure and permissions"""
    try:
        # Initialize submissions file
        if not os.path.exists(SUBMISSIONS_FILE) or os.path.getsize(SUBMISSIONS_FILE) == 0:
            pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(SUBMISSIONS_FILE, index=False)
            os.chmod(SUBMISSIONS_FILE, 0o666)
        
        # Initialize deleted entries file
        if not os.path.exists(DELETED_ENTRIES_FILE) or os.path.getsize(DELETED_ENTRIES_FILE) == 0:
            pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(DELETED_ENTRIES_FILE, index=False)
            os.chmod(DELETED_ENTRIES_FILE, 0o666)
        
        # Initialize users file
        if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
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
            os.chmod(USERS_FILE, 0o666)
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")

def ensure_ids_in_datafiles():
    for csvfile in [SUBMISSIONS_FILE, DELETED_ENTRIES_FILE]:
        if os.path.exists(csvfile) and os.path.getsize(csvfile) > 0:
            df = pd.read_csv(csvfile)
            # If id column is missing, add new UUIDs
            if 'id' not in df.columns:
                df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
            else:
                # If id column is present but blank, fill with UUIDs
                df['id'] = [i if pd.notna(i) and str(i).strip() and str(i) != "nan" else str(uuid.uuid4()) for i in df['id']]
            df.to_csv(csvfile, index=False)
ensure_ids_in_datafiles()

# Initialize data files at startup
initialize_data_files()

def audio_recorder():
    """Audio recorder component with fallback upload."""
    component_key = f"audio_recorder_{uuid.uuid4().hex}"
    if "audio_file" not in st.session_state:
        st.session_state.audio_file = None

    html_code = f"""
    <script>
    window.audioRecorder_{component_key} = {{
        recorder: null,
        audioChunks: [],
        audioPreview: null,
        startRecording: async function() {{
            try {{
                this.audioChunks = [];
                const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                this.recorder = new MediaRecorder(stream);
                this.recorder.ondataavailable = e => {{
                    if (e.data.size > 0) {{
                        this.audioChunks.push(e.data);
                    }}
                }};
                this.recorder.start(100);
                document.getElementById("status_{component_key}").innerText = "Recording... (Max 30 seconds)";
                document.getElementById("preview-container_{component_key}").style.display = "none";
                setTimeout(() => {{
                    if (this.recorder && this.recorder.state === 'recording') {{
                        this.stopRecording();
                    }}
                }}, 30000);
            }} catch (error) {{
                document.getElementById("status_{component_key}").innerText = "Error: " + error.message;
                window.parent.postMessage({{
                    type: 'streamlitError',
                    error: "Failed to start recording: " + error.message,
                    componentKey: "{component_key}"
                }}, '*');
            }}
        }},
        stopRecording: async function() {{
            try {{
                if (!this.recorder || this.recorder.state === 'inactive') {{
                    document.getElementById("status_{component_key}").innerText = "No active recording";
                    return;
                }}
                await new Promise((resolve) => {{
                    this.recorder.onstop = async () => {{
                        try {{
                            if (this.audioChunks.length === 0) {{
                                throw new Error("No audio data recorded");
                            }}
                            const audioBlob = new Blob(this.audioChunks, {{ type: 'audio/wav' }});
                            const arrayBuffer = await audioBlob.arrayBuffer();
                            const reader = new window.FileReader();
                            reader.onloadend = function () {{
                                var base64Data = reader.result.split(',')[1];
                                window.parent.postMessage({{
                                    type: 'audioData',
                                    data: base64Data,
                                    filename: 'recording_' + new Date().getTime() + '.wav',
                                    componentKey: "{component_key}"
                                }}, '*');
                            }};
                            reader.readAsDataURL(audioBlob);

                            if (this.audioPreview) {{
                                URL.revokeObjectURL(this.audioPreview);
                            }}
                            this.audioPreview = URL.createObjectURL(audioBlob);
                            const previewContainer = document.getElementById("preview-container_{component_key}");
                            previewContainer.style.display = "block";
                            document.getElementById("audio-preview_{component_key}").src = this.audioPreview;
                            document.getElementById("status_{component_key}").innerText = "Recording complete - ready to submit";
                            resolve();
                        }} catch (error) {{
                            document.getElementById("status_{component_key}").innerText = "Error processing";
                            window.parent.postMessage({{
                                type: 'streamlitError',
                                error: "Processing error: " + error.message,
                                componentKey: "{component_key}"
                            }}, '*');
                            resolve();
                        }} finally {{
                            if (this.recorder && this.recorder.stream) {{
                                this.recorder.stream.getTracks().forEach(track => track.stop());
                            }}
                        }}
                    }};
                    this.recorder.stop();
                }});
            }} catch (error) {{
                document.getElementById("status_{component_key}").innerText = "Error stopping";
                window.parent.postMessage({{
                    type: 'streamlitError',
                    error: "Stop error: " + error.message,
                    componentKey: "{component_key}"
                }}, '*');
            }}
        }}
    }};
    window.addEventListener('message', (event) => {{
        if (event.data.type === 'triggerStopRecording' && event.data.componentKey === "{component_key}") {{
            window.audioRecorder_{component_key}.stopRecording();
        }}
    }});
    </script>
    <div style="margin: 10px 0; font-family: Arial, sans-serif;">
        <button onclick="window.audioRecorder_{component_key}.startRecording()" style="padding: 8px 16px; margin-right: 10px; 
                background-color: #2E86AB; color: white; border: none; 
                border-radius: 4px; cursor: pointer;">
            🎤 Start Recording
        </button>
        <button onclick="window.audioRecorder_{component_key}.stopRecording()" style="padding: 8px 16px; 
                background-color: #F18F01; color: white; border: none; 
                border-radius: 4px; cursor: pointer;">
            ⏹️ Stop Recording
        </button>
        <p id="status_{component_key}" style="margin-top: 10px; font-size: 14px; color: #555;">
            Ready to record (max 30 seconds)
        </p>
        <div id="preview-container_{component_key}" style="display: none; margin-top: 15px; padding: 10px; 
             background-color: #f5f5f5; border-radius: 5px;">
            <p style="font-size: 14px; margin-bottom: 5px; font-weight: bold;">Your Recording:</p>
            <audio id="audio-preview_{component_key}" controls style="width: 100%;"></audio>
        </div>
    </div>
    """
    html(html_code, height=200)

    # Fallback uploader for audio - now accepts both WAV and M4A
    st.markdown("**If the voice recorder does not work, you can upload an audio recording instead:**")
    upload = st.file_uploader("Upload audio file", type=["wav", "m4a"], key=f"audio_upload_{component_key}")
    if upload:
        try:
            # Ensure the audio directory exists
            os.makedirs(AUDIO_DIR, exist_ok=True)
            
            # Save the uploaded file with appropriate extension
            ext = "wav" if upload.type == "audio/wav" else "m4a"
            audio_path = os.path.join(AUDIO_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
            
            with open(audio_path, "wb") as f:
                f.write(upload.read())
                
            st.session_state.audio_file = audio_path
            st.success("Audio uploaded successfully.")
            
            # Display the audio player
            audio_bytes = open(audio_path, 'rb').read()
            st.audio(audio_bytes, format=f'audio/{ext}')
        except Exception as e:
            st.error(f"Error processing uploaded audio: {str(e)}")
        return

    # Initialize session state for this component if not exists
    if f"audio_data_{component_key}" not in st.session_state:
        st.session_state[f"audio_data_{component_key}"] = None
    if f"audio_filename_{component_key}" not in st.session_state:
        st.session_state[f"audio_filename_{component_key}"] = None
    if f"audio_error_{component_key}" not in st.session_state:
        st.session_state[f"audio_error_{component_key}"] = None

    # Handle audio data from the component
    if st.session_state.get(f"audio_data_{component_key}"):
        try:
            audio_bytes = base64.b64decode(st.session_state[f"audio_data_{component_key}"])
            filename = st.session_state.get(f"audio_filename_{component_key}", f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
            audio_path = os.path.join(AUDIO_DIR, filename)
            
            # Ensure audio directory exists
            os.makedirs(AUDIO_DIR, exist_ok=True)
            
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            
            st.session_state.audio_file = audio_path
            # Clear the component state
            st.session_state[f"audio_data_{component_key}"] = None
            st.session_state[f"audio_filename_{component_key}"] = None
            st.success("Recording saved successfully!")
            
            # Play the recording immediately after saving
            st.audio(audio_path, format='audio/wav')
        except Exception as e:
            st.error(f"Error saving recording: {str(e)}")
            st.session_state[f"audio_error_{component_key}"] = str(e)

    if st.session_state.get(f"audio_error_{component_key}"):
        st.error(f"Recording error: {st.session_state[f'audio_error_{component_key}']}")
        st.session_state[f"audio_error_{component_key}"] = None

def is_mobile():
    """Detect if user is on a mobile device"""
    try:
        user_agent = st.query_params.get("user_agent", [""])[0].lower()
        mobile_keywords = ['mobi', 'android', 'iphone', 'ipad', 'ipod']
        if any(keyword in user_agent for keyword in mobile_keywords):
            return True
        
        if st.query_params.get("screen_width", [""])[0]:
            screen_width = int(st.query_params.get("screen_width", ["768"])[0])
            return screen_width < 768
            
        return False
    except:
        return False

def responsive_columns(default_cols=2):
    """Create responsive columns based on device type"""
    if is_mobile():
        cols = []
        for i in range(default_cols):
            with st.container():
                cols.append(None)
        return cols
    return st.columns(default_cols)

def responsive_expander(label, expanded=True):
    """Create responsive expander based on device type"""
    if is_mobile():
        return st.expander(label, expanded=False)
    return st.expander(label, expanded=expanded)

def mobile_adjusted_text_input(label, value="", max_chars=None, key=None, placeholder=""):
    """Create responsive text input based on device type"""
    if is_mobile():
        return st.text_input(label, value, max_chars=max_chars, key=key, placeholder=placeholder)
    return st.text_input(label, value, max_chars=max_chars, key=key, placeholder=placeholder)

def mobile_adjusted_text_area(label, value="", height=100, key=None, placeholder=""):
    """Create responsive text area based on device type"""
    if is_mobile():
        return st.text_area(label, value, height=max(80, height//2), key=key, placeholder=placeholder)
    return st.text_area(label, value, height=height, key=key, placeholder=placeholder)

def create_backup() -> bool:
    """Create a backup of submissions with verification"""
    try:
        if not os.path.exists(SUBMISSIONS_FILE):
            return False
            
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.csv")
        
        shutil.copy2(SUBMISSIONS_FILE, backup_path)
        os.chmod(backup_path, 0o666)
        
        # Verify backup was created
        if not os.path.exists(backup_path):
            raise Exception("Backup file not created")
            
        return True
    except Exception as e:
        st.error(f"Backup failed: {str(e)}")
        return False

def load_lottiefile(filepath: str) -> Optional[dict]:
    """Load Lottie animation file"""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading Lottie file: {str(e)}")
        return None

def save_submission(entry: dict) -> bool:
    """Save submission with proper validation and error handling"""
    try:
        # Set a unique id if not already set
        if not entry.get('id'):
            entry['id'] = str(uuid.uuid4())
            
        # Ensure all expected columns exist
        for col in EXPECTED_COLUMNS:
            if col not in entry:
                entry[col] = None
        
        # Clean and validate data
        entry = {k: (v.strip() if isinstance(v, str) else v) for k, v in entry.items()}
        
        # Load existing data
        if os.path.exists(SUBMISSIONS_FILE) and os.path.getsize(SUBMISSIONS_FILE) > 0:
            existing_df = pd.read_csv(SUBMISSIONS_FILE)
            # Ensure all columns exist in the existing data
            for col in EXPECTED_COLUMNS:
                if col not in existing_df.columns:
                    existing_df[col] = None
        else:
            existing_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        
        # Create new DataFrame with the entry
        new_df = pd.DataFrame([entry])
        
        # Combine with existing data
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # Save to file
        combined_df.to_csv(SUBMISSIONS_FILE, index=False)
        os.chmod(SUBMISSIONS_FILE, 0o666)  # Ensure proper permissions
        
        return True
    except Exception as e:
        st.error(f"Error saving submission: {str(e)}")
        return False

def load_submissions() -> pd.DataFrame:
    """Load submissions with robust error handling"""
    try:
        if not os.path.exists(SUBMISSIONS_FILE) or os.path.getsize(SUBMISSIONS_FILE) == 0:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
            
        df = pd.read_csv(SUBMISSIONS_FILE)
        
        # Ensure all expected columns exist
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None
                
        # Validate audio file paths
        if 'audio_file' in df.columns:
            df['audio_file'] = df['audio_file'].apply(
                lambda x: x if isinstance(x, str) and os.path.exists(x) else None
            )
            
        return df
    except Exception as e:
        st.error(f"Error loading submissions: {str(e)}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def load_deleted_entries() -> pd.DataFrame:
    """Load deleted entries with validation"""
    try:
        if not os.path.exists(DELETED_ENTRIES_FILE) or os.path.getsize(DELETED_ENTRIES_FILE) == 0:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
            
        df = pd.read_csv(DELETED_ENTRIES_FILE)
        
        # Ensure all expected columns exist
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None
        
        # Clean IDs by stripping whitespace
        if 'id' in df.columns:
            df['id'] = df['id'].astype(str).str.strip()
                
        return df
    except Exception as e:
        st.error(f"Error loading deleted entries: {str(e)}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def delete_submission_by_id(row_id: str, permanent: bool = False) -> bool:
    """Delete a submission by its unique id"""
    try:
        df = load_submissions()
        match = df[df['id'] == row_id]
        if match.empty:
            st.error("Row not found!")
            return False
            
        idx = match.index[0]
        row_to_delete = df.loc[idx].copy()
        audio_file = row_to_delete['audio_file']
        
        if permanent:
            # Remove from deleted_entries if it exists there
            deleted_df = load_deleted_entries()
            match_deleted = deleted_df[deleted_df['id'] == row_id]
            if not match_deleted.empty:
                deleted_df = deleted_df.drop(match_deleted.index)
                deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
                os.chmod(DELETED_ENTRIES_FILE, 0o666)
                
            # Delete audio file if it exists
            if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                except Exception as e:
                    st.error(f"Error deleting audio file: {str(e)}")
        else:
            # Move to deleted entries
            deleted_df = load_deleted_entries()
            deleted_df = pd.concat([deleted_df, pd.DataFrame([row_to_delete])], ignore_index=True)
            deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
            os.chmod(DELETED_ENTRIES_FILE, 0o666)
            
        # Remove from main submissions
        df = df.drop(idx)
        df.to_csv(SUBMISSIONS_FILE, index=False)
        os.chmod(SUBMISSIONS_FILE, 0o666)
        return True
    except Exception as e:
        st.error(f"Deletion failed: {str(e)}")
        return False

def restore_deleted_entry_by_id(row_id: str) -> bool:
    """Restore a deleted entry by its unique id"""
    try:
        deleted_df = load_deleted_entries()
        match = deleted_df[deleted_df['id'] == row_id]
        if match.empty:
            st.error("Row not found!")
            return False
            
        idx = match.index[0]
        entry = deleted_df.loc[idx].copy().to_dict()
        
        # Save to main submissions
        if save_submission(entry):
            # Remove from deleted entries
            deleted_df = deleted_df.drop(idx)
            deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
            os.chmod(DELETED_ENTRIES_FILE, 0o666)
            return True
    except Exception as e:
        st.error(f"Error restoring entry: {str(e)}")
    return False

def permanently_delete_deleted_entry_by_id(row_id: str) -> bool:
    """Permanently delete an entry from the deleted entries file by id."""
    try:
        deleted_df = load_deleted_entries()
        match = deleted_df[deleted_df['id'] == row_id]
        if match.empty:
            st.error("Row not found!")
            return False

        idx = match.index[0]
        row_to_delete = deleted_df.loc[idx].copy()
        audio_file = row_to_delete['audio_file']

        # Remove from deleted_entries
        deleted_df = deleted_df.drop(idx)
        deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
        os.chmod(DELETED_ENTRIES_FILE, 0o666)

        # Optionally, delete audio file
        if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except Exception as e:
                st.error(f"Error deleting audio file: {str(e)}")
        return True
    except Exception as e:
        st.error(f"Permanent deletion failed: {str(e)}")
    return False

def generate_qr_code(data: str) -> Tuple[str, Image.Image]:
    """Generate QR code from data"""
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
    """Display QR code with download option"""
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
    """Show confirmation dialog for destructive actions"""
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
    """Play audio with validation and download option"""
    try:
        if not filename or not isinstance(filename, str) or not os.path.exists(filename):
            st.warning("No valid audio file available")
            return
            
        # Determine file type based on extension
        file_ext = filename.lower().split('.')[-1]
        if file_ext not in ['wav', 'm4a']:
            st.error("Unsupported audio format - only WAV and M4A files supported")
            return

        # Display audio player
        audio_bytes = open(filename, 'rb').read()
        st.audio(audio_bytes, format=f'audio/{file_ext}')
        
        # Add download button
        st.download_button(
            label="Download Recording",
            data=audio_bytes,
            file_name=os.path.basename(filename),
            mime=f'audio/{file_ext}',
            key=f"dl_{filename}"
        )
    except Exception as e:
        st.error(f"Error playing audio: {str(e)}")

def authenticate() -> bool:
    """Handle user authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'username' not in st.session_state:
        st.session_state.username = None

    if not st.session_state.authenticated:
        try:
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
                
                submit_button = st.form_submit_button("Login", type="primary", help="Enter your credentials to access the feedback system")
                if submit_button:
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
    """Show home page"""
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
    
    st.markdown("---")
    st.markdown("<h3 style='text-align: center;'>Quick Access to Feedback Form</h3>", unsafe_allow_html=True)
    
    qr_url = "https://play-africa-feedback-form.streamlit.app/"
    show_qr_code(qr_url)

def show_feedback() -> None:
    """Show feedback form"""
    colors = get_theme_colors()
    
    if is_mobile():
        st.markdown(f"<h2 style='color:{colors['text']}'>Play Africa Feedback</h2>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 style='color:{colors['text']}'>Play Africa Visit Feedback</h1>", unsafe_allow_html=True)
    
    with responsive_expander("Form Instructions", expanded=False):
        st.markdown(f"""
        <div style='color:{colors['text']}; font-size: {'14px' if is_mobile() else '16px'}'>
            <p>Please share your experience at Play Africa.</p>
            <p><strong>All fields marked with * are required.</strong></p>
            <p>You can record children's voices and listen to the recording before submitting.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>Children's Voice</h3>", unsafe_allow_html=True)
    
    audio_recorder()
    
    if st.session_state.get('audio_error'):
        st.error(f"Recording error: {st.session_state.audio_error}")
        st.session_state.audio_error = None
    
    if st.session_state.get('audio_file'):
        try:
            file_ext = st.session_state.audio_file.lower().split('.')[-1]
            st.audio(st.session_state.audio_file, format=f'audio/{file_ext}')
        except Exception as e:
            st.error(f"Error playing recording: {str(e)}")

    with st.form("feedback_form", clear_on_submit=True):
        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>About Your Group</h3>", unsafe_allow_html=True)
        
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

        st.markdown(f"<h3 style='color:{colors['text']}; font-size: {'18px' if is_mobile() else '20px'}'>Your Ratings</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:{colors['text']}; font-size: {'14px' if is_mobile() else '16px'}>1 = Needs Improvement, 3 = Satisfactory, 5 = Excellent</p>", unsafe_allow_html=True)
        
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

        required_fields = [school, children_age, programme, q1, q5]
        
        # Proper submit button using st.form_submit_button()
        submitted = st.form_submit_button("Submit Feedback", type="primary", 
                               use_container_width=True, 
                               help="Tap to submit your feedback")
        
        if submitted:
            if not all(required_fields):
                st.error("Please fill in all required fields (marked with *)")
            else:
                audio_file_path = st.session_state.audio_file if st.session_state.get('audio_file') else ""
                
                entry = {
                    "id": str(uuid.uuid4()),  # Generate a unique ID for each submission
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
                    "audio_file": audio_file_path,
                    "device_type": "mobile" if is_mobile() else "desktop"
                }
                
                if save_submission(entry):
                    st.success("Thank you for your feedback!")
                    st.balloons()
                    
                    # Clear the form and audio state
                    st.session_state.audio_file = None
                    for key in st.session_state.keys():
                        if key.startswith("audio_recorder_"):
                            st.session_state[key] = None
                    
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
    """Show admin dashboard with UUID-based deletion/restoration"""
    colors = get_theme_colors()
    st.markdown(f"<h1 style='color:{colors['text']}'>Feedback Dashboard</h1>", unsafe_allow_html=True)
    
    if create_backup():
        st.toast("Backup created successfully", icon="✅")
    
    st.markdown(f"<h2 style='color:{colors['text']}'>Feedback Management</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Active Feedback", "Deleted Feedback"])
    
    with tab1:
        df = load_submissions()
        if df.empty:
            st.info("No feedback submitted yet. Please check back later!")
        else:
            display_cols = ['timestamp', 'school', 'group_type', 'children_no', 'children_age', 'adults_present', 'id']
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
                'adults_present': 'Adults',
                'id': 'id'
            })
            
            if 'Date' in display_df.columns:
                try:
                    display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            page_size = st.selectbox('Rows per page', [5, 10, 20, 50], index=1, key='active_page_size')
            page_number = st.number_input('Page', min_value=1, max_value=max(1, len(display_df)//page_size + 1), 
                                        value=1, key='active_page')
            start_idx = (page_number - 1) * page_size
            end_idx = min(start_idx + page_size, len(display_df))
            
            table_data = display_df.iloc[start_idx:end_idx] if not display_df.empty else display_df
            
            for idx, row in table_data.iterrows():
                row_id = row['id']
                with st.expander(f"{row['Date']} - {row['Submitted by']}"):
                    st.write(f"Group Type: {row['Group Type']}")
                    st.write(f"Children: {row['Children']} (ages {row['Ages']})")
                    st.write(f"Adults: {row['Adults']}")
                    
                    # Find audio file from df using id:
                    audio_file = df.loc[df['id'] == row_id, 'audio_file'].values[0] if 'audio_file' in df.columns else None
                    if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
                        st.markdown("**Children's Voice Recording:**")
                        play_audio(audio_file)
                    else:
                        st.markdown("**No voice recording available for this submission**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Delete", key=f"del_{row_id}"):
                            st.session_state[f"pending_delete_{row_id}"] = True
                        if st.session_state.get(f"pending_delete_{row_id}", False):
                            with st.expander("⚠️ Confirm Delete", expanded=True):
                                st.warning(f"You are about to delete 1 feedback submission(s). This action cannot be undone.")
                                confirm = st.button("✅ Confirm Delete", key=f"confirm_del_{row_id}")
                                cancel = st.button("❌ Cancel", key=f"cancel_del_{row_id}")
                                if confirm:
                                    if delete_submission_by_id(row_id):
                                        st.success("Entry deleted")
                                        st.session_state[f"pending_delete_{row_id}"] = False
                                        st.rerun()
                                if cancel:
                                    st.session_state[f"pending_delete_{row_id}"] = False
                    with col2:
                        if st.button("💀 Permanent Delete", key=f"perm_del_{row_id}"):
                            st.session_state[f"pending_perm_delete_{row_id}"] = True
                        if st.session_state.get(f"pending_perm_delete_{row_id}", False):
                            with st.expander("⚠️ Confirm Permanent Delete", expanded=True):
                                st.warning(f"You are about to permanent delete 1 feedback submission(s). This action cannot be undone.")
                                confirm_perm = st.button("✅ Confirm Permanent Delete", key=f"confirm_perm_del_{row_id}")
                                cancel_perm = st.button("❌ Cancel", key=f"cancel_perm_del_{row_id}")
                                if confirm_perm:
                                    if delete_submission_by_id(row_id, permanent=True):
                                        st.success("Entry permanently deleted")
                                        st.session_state[f"pending_perm_delete_{row_id}"] = False
                                        st.rerun()
                                if cancel_perm:
                                    st.session_state[f"pending_perm_delete_{row_id}"] = False
    
    with tab2:
        deleted_df = load_deleted_entries()
        if not deleted_df.empty:
            deleted_display = deleted_df[['timestamp', 'school', 'group_type', 'id']].copy()
            deleted_display = deleted_display.rename(columns={
                'timestamp': 'Date',
                'school': 'Submitted by',
                'group_type': 'Group Type',
                'id': 'id'
            })
            
            if 'Date' in deleted_display.columns:
                try:
                    deleted_display['Date'] = pd.to_datetime(deleted_display['Date']).dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            deleted_page_size = st.selectbox('Rows per page', [5, 10], index=0, key='deleted_page_size')
            deleted_page_number = st.number_input('Page', min_value=1, 
                                                max_value=max(1, len(deleted_display)//deleted_page_size + 1), 
                                                value=1, key='deleted_page')
            deleted_start_idx = (deleted_page_number - 1) * deleted_page_size
            deleted_end_idx = min(deleted_start_idx + deleted_page_size, len(deleted_display))
            
            deleted_table_data = deleted_display.iloc[deleted_start_idx:deleted_end_idx]
            
            for idx, row in deleted_table_data.iterrows():
                row_id = row['id']
                with st.expander(f"{row['Date']} - {row['Submitted by']}"):
                    st.write(f"Group Type: {row['Group Type']}")
                    
                    audio_file = deleted_df.loc[deleted_df['id'] == row_id, 'audio_file'].values[0] if 'audio_file' in deleted_df.columns else None
                    if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
                        st.markdown("**Children's Voice Recording:**")
                        play_audio(audio_file)
                    else:
                        st.markdown("**No voice recording available for this submission**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("↩️ Restore", key=f"restore_{row_id}"):
                            st.session_state[f"pending_restore_{row_id}"] = True
                        if st.session_state.get(f"pending_restore_{row_id}", False):
                            with st.expander("⚠️ Confirm Restore", expanded=True):
                                st.warning("You are about to restore 1 feedback submission(s). This action cannot be undone.")
                                confirm_restore = st.button("✅ Confirm Restore", key=f"confirm_restore_{row_id}")
                                cancel_restore = st.button("❌ Cancel", key=f"cancel_restore_{row_id}")
                                if confirm_restore:
                                    if restore_deleted_entry_by_id(row_id):
                                        st.success("Entry restored")
                                        st.session_state[f"pending_restore_{row_id}"] = False
                                        st.rerun()
                                if cancel_restore:
                                    st.session_state[f"pending_restore_{row_id}"] = False
                    with col2:
                        if st.button("💀 Permanent Delete", key=f"perm_del_deleted_{row_id}"):
                            st.session_state[f"pending_perm_delete_deleted_{row_id}"] = True
                        if st.session_state.get(f"pending_perm_delete_deleted_{row_id}", False):
                            with st.expander("⚠️ Confirm Permanent Delete", expanded=True):
                                st.warning("You are about to permanent delete 1 feedback submission(s). This action cannot be undone.")
                                confirm_perm = st.button("✅ Confirm Permanent Delete", key=f"confirm_perm_del_deleted_{row_id}")
                                cancel_perm = st.button("❌ Cancel", key=f"cancel_perm_del_deleted_{row_id}")
                                if confirm_perm:
                                    if permanently_delete_deleted_entry_by_id(row_id):  # Changed to use the new function
                                        st.success("Entry permanently deleted")
                                        st.session_state[f"pending_perm_delete_deleted_{row_id}"] = False
                                        st.rerun()
                                if cancel_perm:
                                    st.session_state[f"pending_perm_delete_deleted_{row_id}"] = False
        else:
            st.info("No deleted entries to display")
    
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

        st.markdown(
            f"""
            <div style='
                background: {colors['card_bg']};
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
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
    """Generate star rating display"""
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
    """Main application function"""
    st.set_page_config(
        page_title="Play Africa Feedback",
        page_icon=":children_crossing:",
        layout="wide",
        initial_sidebar_state="auto"
    )

    st.markdown(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">',
        unsafe_allow_html=True
    )

    # Initialize session state for mobile detection
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = is_mobile()
    
    # Custom CSS styling
    st.markdown(f"""
    <style>
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
        
        div[data-testid="stMarkdownContainer"] > div {{
            transition: transform 0.3s ease;
        }}
        
        div[data-testid="stMarkdownContainer"] > div:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
        }}
        
        .star-rating {{
            color: #F18F01;
            letter-spacing: 2px;
        }}
        
        @media (max-width: 768px) {{
            .stTextInput input, .stTextArea textarea, .stSelectbox select {{
                font-size: 16px !important;
                padding: 12px !important;
            }}
            
            .stButton>button {{
                width: 100% !important;
                padding: 12px !important;
                font-size: 16px !important;
            }}
            
            .main .block-container {{
                padding: 1rem !important;
            }}
            
            [data-testid="stSidebar"] {{
                width: 100% !important;
            }}
            
            .lottie-animation {{
                display: none;
            }}
            
            .stForm {{
                padding: 0.5rem !important;
            }}
            
            .stSlider {{
                margin-top: 0.5rem !important;
                margin-bottom: 0.5rem !important;
            }}
            
            div[data-testid="stMarkdownContainer"] > div {{
                padding: 15px !important;
                margin-bottom: 15px !important;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)

    # Initialize audio session state
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None

    # JavaScript message handler for audio recorder
    st.markdown("""
    <script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'audioData') {
            window.parent.streamlitBridge.setComponentValue({
                [`audio_data_${event.data.componentKey}`]: event.data.data,
                [`audio_filename_${event.data.componentKey}`]: event.data.filename,
                [`audio_error_${event.data.componentKey}`]: null
            });
        }
        if (event.data.type === 'streamlitError') {
            window.parent.streamlitBridge.setComponentValue({
                [`audio_data_${event.data.componentKey}`]: null,
                [`audio_error_${event.data.componentKey}`]: event.data.error
            });
        }
    });
    </script>
    """, unsafe_allow_html=True)

    # Handle authentication
    if not authenticate():
        return

    # Sidebar navigation
    with st.sidebar:
        try:
            st.image("play_logo.jpeg", width=200)  # Replaced Lottie animation with play logo
        except Exception as e:
            st.warning(f"Play logo not found: {str(e)}")
        
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

    # Main content routing
    if menu == "Home":
        show_home()
    elif menu == "Visitor Feedback":
        show_feedback()
    elif menu == "Review Feedback" and st.session_state.role == "admin":
        show_dashboard()

if __name__ == "__main__":
    main()