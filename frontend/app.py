import streamlit as st
import requests
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize session state
if "file" not in st.session_state:
    st.session_state.file = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "lecture_id" not in st.session_state:
    st.session_state.lecture_id = None
if "uploading" not in st.session_state:
    st.session_state.uploading = False
if "progress" not in st.session_state:
    st.session_state.progress = 0

# Page configuration
st.set_page_config(page_title="Lecture Summarizer", layout="centered")

# Header with navigation
col1, col2 = st.columns([4, 1])
with col1:
    st.header("Upload Lecture Audio")
with col2:
    if st.button("Live Transcriptions"):
        st.switch_page("pages/live_transcriptions.py")

# File uploader
uploaded_file = st.file_uploader(
    "Drag and drop your audio file here, or click to select (MP3, WAV, or AAC, max 25MB)",
    type=["mp3", "wav", "aac"],
    accept_multiple_files=False
)

# Update file in session state
if uploaded_file is not None:
    if uploaded_file.size > 25 * 1024 * 1024:
        st.error("File is too large (max 25MB).")
        st.session_state.file = None
    else:
        st.session_state.file = uploaded_file
        st.write(f"Selected: {uploaded_file.name}")

# Buttons
col1, col2 = st.columns(2)
with col1:
    upload_button = st.button("Upload & Process", disabled=st.session_state.uploading or not st.session_state.file)
with col2:
    reset_button = st.button("Reset", disabled=st.session_state.uploading)

# Handle reset
if reset_button:
    st.session_state.file = None
    st.session_state.summary = None
    st.session_state.lecture_id = None
    st.session_state.uploading = False
    st.session_state.progress = 0
    st.rerun()

# Handle upload
if upload_button and st.session_state.file:
    st.session_state.uploading = True
    st.session_state.progress = 10
    progress_bar = st.progress(st.session_state.progress)
    
    try:
        # Simulate progress
        for i in range(10, 91, 10):
            st.session_state.progress = i
            progress_bar.progress(i)
            time.sleep(0.5)

        # Upload file to backend
        files = {"audio": (st.session_state.file.name, st.session_state.file.getvalue(), st.session_state.file.type)}
        response = requests.post(f"{BACKEND_URL}/upload", files=files)

        # progress_bar.progress(100)

        if response.status_code != 200:
            raise Exception(f"Upload failed: {response.text}")

        result = response.json()
        if "error" in result:
            raise Exception(result["error"])

        # st.session_state.summary = result["summary"]
        st.session_state.lecture_id = result["lecture_id"]
        st.session_state.transcript = result["transcript"]
        st.success("Audio processed successfully!")
    except Exception as e:
        st.error(str(e))
    finally:
        st.session_state.uploading = False
        st.session_state.progress = 0
        progress_bar.progress(0)

# Display summary
if st.session_state.summary:
    with st.expander("View Summary"):
        st.text(st.session_state.summary)
    
    if st.session_state.lecture_id:
        if st.button("Ask Questions"):
            st.query_params["lecture_id"] = st.session_state.lecture_id
            st.switch_page("pages/chat.py")