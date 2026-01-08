# TubeMind

TubeMind is an AI-powered retrieval application that transforms YouTube videos into interactive knowledge bases. It allows users to query video content through a chat interface, providing answers grounded in specific timestamps and transcripts.

The system utilizes a Retrieval-Augmented Generation (RAG) pipeline to download audio, generate accurate transcripts, index content into a vector database, and synthesize answers using Large Language Models (LLMs). It is designed to run completely in the cloud, utilizing a split frontend/backend architecture.

## Features

* **Robust Video Ingestion:** Utilizes `yt-dlp` for industry-standard video extraction, supporting secure cookie-based authentication to bypass bot detection limits on cloud servers.
* **Global Context Awareness:** Implements a Map-Reduce summarization strategy. The system summarizes the video in chunks and combines them into a master summary, allowing the AI to answer high-level questions ("What is the main argument?") as well as specific details.
* **Persistent Chat Archives:** Users can process multiple videos in a single session. The application maintains separate chat histories for each video, allowing users to switch contexts seamlessly without losing progress.
* **Hybrid Search:** Retrieves answers by combining the "Global Summary" (for context) with specific vector search results (for precision), ensuring comprehensive answers.
* **Namespace Isolation:** Video data is stored in isolated namespaces within the vector database, preventing data leakage between different video contexts.

## Technical Architecture

The application operates on a split-stack design to ensure scalability and security:

1. **Frontend (Streamlit):**
* Manages user session state and chat archives.
* Communicates with the backend via RESTful API calls.
* Displays real-time processing feedback.


2. **Backend (FastAPI):**
* Acts as the central orchestrator for data flow.
* Exposes endpoints for video processing, querying, and memory management.


3. **Ingestion Worker (Cloud Indexer):**
* **Download:** Extracts audio using `yt-dlp`. If the server IP is flagged, it automatically reconstructs authentication cookies from environment variables.
* **Compression:** Checks file size against API limits. If necessary, converts audio to Mono/16kHz/32k bitrate to reduce size by ~90%.
* **Transcription:** Uses Groq's Whisper-large-v3 for transcription.
* **Indexing:** Vectors are generated and stored in Pinecone.


4. **Inference Engine (The Brain):**
* Fetches the "Summary Card" directly by ID for context.
* Performs semantic search for specific segments.
* Synthesizes the final response using Llama-3-70b.



## Tech Stack

* **Frontend:** Streamlit
* **Backend:** FastAPI, Uvicorn
* **Vector Database:** Pinecone
* **LLM & Speech-to-Text:** Groq (Llama-3, Whisper-large-v3)
* **Video Extraction:** yt-dlp
* **Deployment:** Render (Backend), Streamlit Cloud (Frontend)

## Installation & Setup

### Prerequisites

* Python 3.9+
* API Keys for **Groq** and **Pinecone**
* (Optional) A `cookies.txt` file from YouTube for cloud authentication

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/TubeMind.git
cd tubemind

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```ini
GROQ_API_KEY=gsk_your_groq_key...
PINECONE_API_KEY=pcsk_your_pinecone_key...
API_URL=http://127.0.0.1:8000

```

### 4. Running Locally

**Start the Backend:**

```bash
uvicorn API:api --reload

```

**Start the Frontend:**

```bash
streamlit run UI.py

```

## Cloud Deployment (Render & Streamlit)

For production deployment, the application requires specific configuration to handle YouTube's bot detection:

1. **Authentication:** To bypass YouTube 403/Bot errors, export your YouTube cookies to Netscape format. Copy the content of the file and save it as an environment variable named `YOUTUBE_COOKIES` on the Render dashboard. The application will automatically reconstruct the file at runtime.
2. **Frontend (Streamlit Cloud):** Deploy `UI.py` and set the `API_URL` secret to point to your Render backend URL.

## Project Structure

```text
/tubemind
├── API.py              # FastAPI entry point
├── brain.py            # RAG Logic: Search & Answer generation
├── indexer.py    # Ingestion: Download (yt-dlp) -> Compress -> Index
├── UI.py         # Streamlit UI & Archive Management
├── requirements.txt    # Dependencies
└── .gitignore          # Security exclusions (cookies.txt, .env)

```

## License

[MIT](https://choosealicense.com/licenses/mit/)