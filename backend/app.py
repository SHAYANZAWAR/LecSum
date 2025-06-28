from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import whisper
import os
import uuid
from dotenv import load_dotenv
import tempfile
import asyncio
from pydub import AudioSegment
import shutil
import requests
from typing import Optional
from audio_processing import process_audio 
import json
import time

# Configure pydub to find ffmpeg
AudioSegment.ffmpeg = "/usr/bin/ffmpeg"  # Linux/Mac; adjust path as needed
# Windows example: AudioSegment.ffmpeg = "C:\\ffmpeg\\bin\\ffmpeg.exe"

# Initialize FastAPI app
app = FastAPI(title="Lecture Summarizer Backend")

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize Whisper
whisper_model = whisper.load_model("base")

# Initialize DeepSeek via OpenRouter
class DeepSeekClient:
    def __init__(self, api_key: Optional[str]):
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set in .env")
        self.api_key = api_key
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Lecture Summarizer" 
        }
    
    def summarize(self, text: str, retries: int = 3, backoff: float = 1.0) -> str:
        payload = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [
                {"role": "system", "content": "You are a helpful AI that summarizes text."},
                {"role": "user", "content": f"The given text is transcribed from the audio recording in a classroom, Summarize it in 100-200 words (Do not include any reasoning steps, or explanations-just the summary):\n{text}"}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        for attempt in range(retries):
            try:
                # Log request
                print(f"DeepSeek API request (attempt {attempt + 1}): {self.endpoint}, Headers: {self.headers}, Payload: {json.dumps(payload)}")
                
                response = requests.post(self.endpoint, headers=self.headers, json=payload)
                response.raise_for_status()

                # Log response
                print(f"DeepSeek API response: {response.status_code}, {response.text}")

                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.HTTPError as e:
                if response.status_code == 403:
                    print(f"DeepSeek API error: 403 Forbidden - Likely invalid API key or restricted access.")
                    raise HTTPException(
                        status_code=500,
                        detail="DeepSeek summarization error: 403 Forbidden. Check OPENROUTER_API_KEY at openrouter.ai."
                    )
                elif response.status_code == 429:
                    # Rate limit: retry with backoff
                    print(f"Rate limit hit, retrying in {backoff * (2 ** attempt)} seconds...")
                    time.sleep(backoff * (2 ** attempt))
                    continue
                else:
                    print(f"DeepSeek API error: {response.status_code}, {response.text}")
                    raise HTTPException(status_code=500, detail=f"DeepSeek summarization error: {str(e)}")
            except Exception as e:
                print(f"DeepSeek API unexpected error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"DeepSeek summarization error: {str(e)}")
        
        raise HTTPException(status_code=500, detail="DeepSeek summarization failed after retries.")
    
    def answer(self, question: str, context: str) -> str:
        payload = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [
                {"role": "system", "content": "You are a helpful AI that answers questions based on provided context."},
                {"role": "user", "content": f"Context: {context}\nQuestion: {question}"}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DeepSeek Q&A error: {str(e)}")

deepseek_client = DeepSeekClient(OPENROUTER_API_KEY)


class OllamaTranscriptionClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "gemma3n:e4b"

    def transcribe(self, file_path: str, language: str = "English") -> str:
        # Read audio file as bytes
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
        # Ollama's /api/generate expects a prompt, so we use a transcription prompt
        prompt = (
            f"Transcribe the following audio file to {language} text. "
            "Only output the transcription, nothing else."
        )
        
        files = {
            "file": (os.path.basename(file_path), audio_bytes, "audio/wav")
        }
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(f"{self.base_url}/api/generate", data=data, files=files)
        response.raise_for_status()
        return response.json()["response"]

ollama_transcriber = OllamaTranscriptionClient()

def transcribe_audio(file_path: str) -> str:
    """Transcribe audio using Ollama Gemma3n:e4b."""
    try:
        return ollama_transcriber.transcribe(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

@app.post("/upload")
async def upload_audio(audio: UploadFile = File(...)):
    # Validate file type
    if audio.content_type not in ["audio/mpeg", "audio/wav", "audio/aac", "audio/mp4", "audio/vnd.dlna.adts"]:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Only MP3, WAV, or AAC allowed. {audio.content_type} provided.")
    
    # Validate file size (25MB)
    content = await audio.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large (max 25MB).")
    
    # Save file
    lecture_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{lecture_id}_{audio.filename}")
    with open(file_path, "wb") as f:
        f.write(content)
    # save the processed audio file
    print(f"File saved: {file_path}")
    file_path = process_audio(file_path, f"{lecture_id}.mp3")
    
    try:
        
        # Transcribe with local Whisper
        transcript = transcribe_audio(file_path)
        
                 
        # Summarize with DeepSeek
        summary = deepseek_client.summarize(transcript)
        # print(f"Summary generated: {summary}")
        # Store transcript and summary
        # with open(os.path.join(UPLOAD_DIR, f"{lecture_id}_summary.txt"), "w") as f:
        #     f.write(summary)
        
        return {
            "lecture_id": lecture_id,
            "summary": summary,
            "transcript": transcript,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Optionally clean up file
        pass

@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    temp_dir = tempfile.mkdtemp()
    audio_chunks = []
    chunk_count = 0
    last_transcription = ""

    try:
        while True:
            # Receive audio chunk
            data = await websocket.receive_bytes()
            if not data:
                break

            # Save chunk as WebM
            chunk_path = os.path.join(temp_dir, f"chunk_{chunk_count}.webm")
            with open(chunk_path, "wb") as f:
                f.write(data)
            
            # Convert WebM to WAV
            audio = AudioSegment.from_file(chunk_path, format="webm")
            wav_path = os.path.join(temp_dir, f"chunk_{chunk_count}.wav")
            audio.export(wav_path, format="wav")
            audio_chunks.append(wav_path)
            chunk_count += 1

            # Transcribe every 5 chunks (approx. 5 seconds)
            if chunk_count % 5 == 0:
                # Combine chunks
                combined_audio = AudioSegment.empty()
                for chunk in audio_chunks:
                    combined_audio += AudioSegment.from_wav(chunk)
                
                combined_path = os.path.join(temp_dir, "combined.wav")
                combined_audio.export(combined_path, format="wav")

                # Transcribe with local Whisper
                transcript = transcribe_audio(combined_path)

                # Send only new transcription
                if transcript != last_transcription:
                    await websocket.send_text(transcript)
                    last_transcription = transcript

                # Keep last 10 chunks
                if len(audio_chunks) > 10:
                    old_chunk = audio_chunks.pop(0)
                    os.remove(old_chunk)
                
                await asyncio.sleep(0.1)

    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        await websocket.close()