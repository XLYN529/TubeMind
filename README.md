Here is a professional, comprehensive `README.md` for your project. You can copy-paste this directly into your GitHub repository.

---

#  TubeMind: The AI Video Tutor

**Turn any YouTube video into an interactive learning session.**

TubeMind is an AI-powered RAG (Retrieval-Augmented Generation) application that allows users to chat with YouTube videos. It downloads audio, generates transcripts, indexes content into a vector database, and uses LLMs to answer questions with precise timestamped citations.

---

##  Features

*  Universal Video Support:** Works with any public YouTube URL.
*  Instant Transcription:** Uses Groq's Whisper-large-v3 for lightning-fast, accurate audio-to-text conversion.
*  "Global Context" Engine:** Automatically generates a comprehensive summary of the entire video using a Map-Reduce strategy, ensuring the AI understands the "big picture" alongside specific details.
*  Hybrid Search:** Combines semantic vector search (Pinecone) with global context injection to answer both specific ("What did he say at 5:00?") and overarching ("What is the main topic?") questions.
*  Ephemeral Sessions:** No login required. Chat history and processed videos live in your browser session and vanish when you close the tab for privacy and speed.
*  Namespace Isolation:** Every video is stored in its own isolated namespace, preventing data overlap between users or videos.

---

## 🛠️ Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io/) (Python-based UI)
* **Backend API:** [FastAPI](https://fastapi.tiangolo.com/)
* **Vector Database:** [Pinecone](https://www.pinecone.io/) (Serverless Inference)
* **LLM & Transcription:** [Groq](https://groq.com/) (Llama-3-70b & Whisper-large-v3)
* **Video Processing:** [pytubefix](https://github.com/JuanBindez/pytubefix)
* **Deployment:** Render (Backend) + Streamlit Cloud (Frontend)

---

## 🏗️ Architecture

The app follows a split-architecture design:

1. **Streamlit Frontend:** Handles user inputs and session state (history). Sends JSON requests to the API.
2. **FastAPI Backend:** Acts as the traffic controller.
3. **Cloud Indexer (Worker):**
* Downloads audio via `pytubefix`.
* Transcribes via Groq Whisper.
* Generates a summary via Map-Reduce (Llama-3).
* Chunks text and uploads to Pinecone.


4. **The Brain (Worker):**
* Fetches the summary card + specific chunks from Pinecone.
* Constructs a hybrid prompt.
* Returns the AI answer with timestamps.



---

## 📦 Installation & Setup

### Prerequisites

* Python 3.9+
* API Keys for **Groq** and **Pinecone**

### 1. Clone the Repository

```bash
git clone https://github.com/XLYN529/TubeMind.git
cd tubemind

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```ini
GROQ_API_KEY=gsk_your_groq_key_here
PINECONE_API_KEY=pcsk_your_pinecone_key_here

```

---


## 📂 Project Structure

```text
/tubemind
├── API.py             # FastAPI entry point (The Manager)
├── brain.py           # RAG Logic: Search & Answer generation (The Thinker)
├── indexer.py         # Ingestion Logic: Download -> Transcribe -> Index (The Worker)
├── UI.py              # Streamlit UI & Session Management
├── requirements.txt   # Python dependencies
└── .env              

```


## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)