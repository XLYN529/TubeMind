import os
import glob
import tempfile
import yt_dlp  # <--- NEW LIBRARY
from pinecone import Pinecone
from groq import Groq

# --- CLIENT SETUP ---
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index = pc.Index("videodb")

# --- HELPER: MAP-REDUCE SUMMARY ---
def generate_smart_summary(full_text):
    """
    Summarizes text of ANY length using Map-Reduce.
    """
    CHUNK_SIZE = 20000  
    
    # CASE A: Short Video 
    if len(full_text) < CHUNK_SIZE:
        print("⚡ Text is short. Summarizing directly...")
        prompt = f"Summarize this video transcript in detail:\n{full_text}"
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        return res.choices[0].message.content

    # CASE B: Long Video 
    print(f"📚 Text is long ({len(full_text)} chars). Using Map-Reduce...")
    
    chunks = [full_text[i:i+CHUNK_SIZE] for i in range(0, len(full_text), CHUNK_SIZE)]
    partial_summaries = []
    
    for i, chunk in enumerate(chunks):
        print(f"   - Summarizing part {i+1}/{len(chunks)}...")
        prompt = f"Summarize this segment of a video transcript in detail:\n{chunk}"
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        partial_summaries.append(res.choices[0].message.content)

    print("   - Combining summaries...")
    combined_text = " ".join(partial_summaries)
    
    final_prompt = f"""
    Here are summaries of different parts of a video, in chronological order.
    Combine them into one cohesive, comprehensive summary of the entire video.
    
    Partial Summaries:
    {combined_text}
    """
    
    final_res = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": final_prompt}],
        model="llama-3.3-70b-versatile"
    )
    
    return final_res.choices[0].message.content

# --- MAIN PROCESS FUNCTION ---
def process_video(youtube_url):
    print(f"🎬 Processing: {youtube_url}")
    
    video_title = "Unknown Video"
    video_id = "unknown_id"
    transcription = None
    
    # --- STEP 1: DOWNLOAD WITH YT-DLP ---
    with tempfile.TemporaryDirectory() as temp_dir:
        
        # =========================================================
        # 🛡️ SECURITY FIX: RECONSTRUCT COOKIES FROM ENV VARIABLE
        # This allows you to keep the repo PUBLIC but cookies PRIVATE
        # =========================================================
        if os.environ.get("YOUTUBE_COOKIES"):
            print("🍪 Found YOUTUBE_COOKIES env var. Creating cookies.txt...")
            with open("cookies.txt", "w") as f:
                f.write(os.environ.get("YOUTUBE_COOKIES"))
        # =========================================================

        # 1. Configure yt-dlp
        ydl_opts = {
            'format': 'bestaudio',   
            'format_sort': [
                '+size',      # 1. Pick the smallest file first
                '+abr',       # 2. If sizes are equal, pick lowest bitrate
                'acodec:opus' # 3. Prefer Opus (best efficiency for small files)
            ],
            'outtmpl': f'{temp_dir}/%(id)s.%(ext)s', 
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [],
            extractor_args': {
                'youtube': {
                    'player_client': ['web', 'mweb'],
                    'skip': ['dash', 'hls'] 
                }
            }
        }
        

        # 2. Tell yt-dlp to use the file we just created
        if os.path.exists("cookies.txt"):
            print("🍪 Using cookies.txt for authentication.")
            ydl_opts['cookiefile'] = "cookies.txt"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract Info & Download
                print("⬇️ Downloading with yt-dlp...")
                info = ydl.extract_info(youtube_url, download=True)
                
                video_title = info.get('title', 'Unknown')
                video_id = info.get('id')
                
                # Find the file (Extension might be webm, m4a, opus...)
                downloaded_file = glob.glob(f"{temp_dir}/{video_id}.*")[0]
                print(f"✅ Downloaded: {downloaded_file}")
                
                # --- STEP 2: TRANSCRIBE ---
                print("👂 Transcribing...")
                with open(downloaded_file, "rb") as file:
                    transcription = groq_client.audio.transcriptions.create(
                        file=(downloaded_file, file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json", 
                    )

        except Exception as e:
            print(f"❌ Download/Transcription Error: {e}")
            return None, None

    # --- STEP 3: GENERATE SUMMARY ---
    print("📝 Generating Summary...")
    full_text = " ".join([s['text'] for s in transcription.segments])
    
    try:
        ai_summary = generate_smart_summary(full_text)
        print(f"✅ Summary Generated ({len(ai_summary)} chars)")
    except Exception as e:
        print(f"⚠️ Summary failed: {e}")
        ai_summary = "Summary unavailable."

    # --- STEP 4: PREPARE RECORDS ---
    print("🧠 Preparing records...")
    records = []
    
    # A. Summary Card
    records.append({
        "id": "global_summary", 
        "text": ai_summary,
        "start_time": 0.0,
        "end_time": 0.0,
        "url": youtube_url,
        "title": "SUMMARY_CARD"
    })

    # B. Video Chunks
    current_text = ""
    chunk_start = 0.0
    
    for segment in transcription.segments:
        text = segment['text']
        start = segment['start']
        end = segment['end']
        
        if current_text == "":
            chunk_start = start
            
        if len(current_text) + len(text) >= 1000:
            records.append({
                "id": f"{video_id}_{len(records)}", 
                "text": current_text.strip(),
                "start_time": chunk_start,
                "end_time": end,
                "url": youtube_url,
                "title": video_title
            })
            current_text = ""
            chunk_start = start 
        
        current_text += " " + text
    
    if current_text:
        records.append({
            "id": f"{video_id}_{len(records)}",
            "text": current_text.strip(),
            "start_time": chunk_start,
            "end_time": transcription.segments[-1]['end'],
            "url": youtube_url,
            "title": video_title
        })

    # --- STEP 5: UPLOAD ---
    try:
        index.upsert_records(namespace=video_id, records=records)
        print(f"🎉 SUCCESS! Saved {len(records)} records.")
        return video_id, video_title
        
    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return None, None
