import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws/transcribe")

# Page configuration
st.set_page_config(page_title="Live Transcriptions", layout="centered")
st.header("Live Audio Transcription")

# Initialize session state
if "recording" not in st.session_state:
    st.session_state.recording = False
if "transcript" not in st.session_state:
    st.session_state.transcript = ""

# JavaScript for audio recording and WebSocket
js_code = f"""
<script>
let mediaRecorder;
let socket;
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const transcriptArea = document.getElementById('transcriptArea');

function startRecording() {{
    navigator.mediaDevices.getUserMedia({{ audio: true }})
        .then(stream => {{
            mediaRecorder = new MediaRecorder(stream, {{ mimeType: 'audio/webm' }});
            socket = new WebSocket('{BACKEND_WS_URL}');
            
            socket.onopen = () => {{
                console.log('WebSocket connected');
                startButton.disabled = true;
                stopButton.disabled = false;
                mediaRecorder.start(1000); // Send chunks every 1s
            }};
            
            socket.onmessage = (event) => {{
                transcriptArea.value += event.data + '\\n';
            }};
            
            socket.onclose = () => {{
                console.log('WebSocket closed');
                startButton.disabled = false;
                stopButton.disabled = true;
            }};
            
            socket.onerror = (error) => {{
                console.error('WebSocket error:', error);
                transcriptArea.value += 'Error: WebSocket connection failed\\n';
            }};
            
            mediaRecorder.ondataavailable = (event) => {{
                if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {{
                    socket.send(event.data);
                }}
            }};
        }})
        .catch(error => {{
            console.error('Microphone access error:', error);
            transcriptArea.value += 'Error: Could not access microphone\\n';
        }});
}}

function stopRecording() {{
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }}
    if (socket && socket.readyState === WebSocket.OPEN) {{
        socket.close();
    }}
    startButton.disabled = false;
    stopButton.disabled = true;
}}
</script>
<div>
    <button id="startButton" onclick="startRecording()">Start Recording</button>
    <button id="stopButton" onclick="stopRecording()" disabled>Stop Recording</button>
</div>
<textarea id="transcriptArea" rows="10" style="width: 100%; margin-top: 10px;" readonly></textarea>
"""

# Render HTML/JavaScript component
components.html(js_code, height=400)

# Streamlit controls
col1, col2 = st.columns(2)
with col1:
    if st.button("Clear Transcript"):
        st.session_state.transcript = ""
        st.rerun()
with col2:
    if st.button("Back to Home"):
        st.switch_page("app.py")

# Display transcript (sync with JS)
transcript_area = st.empty()
transcript_area.text_area("Live Transcript", st.session_state.transcript, disabled=True)