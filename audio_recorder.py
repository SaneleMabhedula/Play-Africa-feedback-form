import os
from datetime import datetime
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
import queue
from pydub import AudioSegment
import numpy as np

def audio_recorder():
    """Audio recorder component with fixes for local development"""
    st.markdown("### Children's Voice Recording")
    
    # Initialize session state
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None
    if 'last_audio_file' not in st.session_state:
        st.session_state.last_audio_file = None
    
    # Restore previous recording if exists
    if st.session_state.get('last_audio_file') and os.path.exists(st.session_state.last_audio_file):
        st.session_state.audio_file = st.session_state.last_audio_file

    # Audio processing queue
    audio_queue = queue.Queue()

    def audio_frame_callback(frame: av.AudioFrame) -> av.AudioFrame:
        audio_queue.put(frame.to_ndarray())
        return frame

    # WebRTC configuration
    webrtc_ctx = webrtc_streamer(
        key="play-africa-recorder",
        mode=WebRtcMode.SENDRECV,
        audio_frame_callback=audio_frame_callback,
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
        media_stream_constraints={
            "audio": {
                "sampleRate": 44100,
                "noiseSuppression": True,
                "echoCancellation": True,
            },
            "video": False
        }
    )

    # Save recording when stopped
    if webrtc_ctx and not webrtc_ctx.state.playing and not audio_queue.empty():
        st.info("Saving recording...")
        
        try:
            os.makedirs("data/audio", exist_ok=True)
            audio_path = os.path.abspath(os.path.join("data/audio", 
                f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"))
            
            # Combine audio chunks with proper metadata
            audio_array = np.concatenate(list(audio_queue.queue))
            audio_segment = AudioSegment(
                audio_array.tobytes(),
                frame_rate=44100,
                sample_width=2,  # 16-bit
                channels=1       # Mono
            )
            audio_segment.export(audio_path, format="wav", bitrate="128k")
            
            # Update session state
            st.session_state.audio_file = audio_path
            st.session_state.last_audio_file = audio_path
            st.success(f"Recording saved to: {audio_path}")
            st.rerun()  # Refresh to show new recording
            
        except Exception as e:
            st.error(f"Error saving recording: {str(e)}")

    # Fallback upload option with duplication fix
    st.markdown("**If microphone doesn't work, upload audio instead:**")
    upload = st.file_uploader("Upload audio file", type=["wav", "mp3", "m4a"], 
                            key="audio_uploader")
    
    if upload:
        try:
            # Check for duplicate upload
            if 'last_upload' in st.session_state and st.session_state.last_upload == upload.name:
                st.warning("This file was already uploaded")
                return
                
            os.makedirs("data/audio", exist_ok=True)
            ext = upload.name.split('.')[-1].lower()
            audio_path = os.path.abspath(os.path.join("data/audio", 
                f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"))
            
            with open(audio_path, "wb") as f:
                f.write(upload.getvalue())
                
            st.session_state.audio_file = audio_path
            st.session_state.last_audio_file = audio_path
            st.session_state.last_upload = upload.name
            st.success(f"Audio saved to: {audio_path}")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error processing upload: {str(e)}")

    # Debug info (can be removed in production)
    with st.expander("Debug Info", expanded=False):
        st.write("Current audio file:", st.session_state.get('audio_file'))
        st.write("Last audio file:", st.session_state.get('last_audio_file'))
        if st.session_state.get('audio_file'):
            st.write("File exists:", os.path.exists(st.session_state.audio_file))