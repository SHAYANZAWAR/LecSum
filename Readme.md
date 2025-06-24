# lecSum

**lecSum** is an LLM-powered application that lets you get summaries and chat with your audio recordings of classroom lectures, meetings, and more.

## Features

- 🎤 **Audio Upload:** Upload your recorded lectures or meetings.
- 📝 **Automatic Transcription:** Uses [OpenAI Whisper](https://github.com/openai/whisper) (runs locally) to transcribe your audio to text.
- 🧠 **Summarization & Q&A:** Summarize your lectures or ask questions about the content using [DeepSeek R1](https://deepseek.com/).
- 💬 **Chat Interface:** Interact with your lecture content as if chatting with an AI assistant.

## Tech Stack

- **Backend:** Python (FastAPI), OpenAI Whisper (local), DeepSeek R1 API
- **Frontend:** Basic using Streamlit.

## Status

🚧 **This project is under active development.**  
Planned features include:
- Improved audio preprocessing before transcription (noise reduction, silence trimming, etc.)
- Live transcription support
- On-the-go question suggestions and interactive ideas

## Getting Started

1. Clone the repo.
2. Set up the backend environment (see `backend/`).
3. Place your audio files in the appropriate folder.
4. Run the backend and interact via the API or frontend (when available).

## License

MIT

---

*Stay tuned for updates and new features!*