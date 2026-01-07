import os
import tempfile
from pinecone import Pinecone
from groq import Groq
from pytubefix import YouTube 

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index = pc.Index("videodb")

def process_video(youtube_url):
    print(f"🎬 Processing: {youtube_url}")
    
    # --- 1. DOWNLOAD & TRANSCRIBE --- 
    # (I'll keep this short since you have this part working perfectly)
    with tempfile.TemporaryDirectory() as temp_dir:
        yt = YouTube(youtube_url)
        stream = yt.streams.filter(only_audio=True).first()
        downloaded_path = stream.download(output_path=temp_dir)
        
        with open(downloaded_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(downloaded_path, file.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json", 
            )

    # --- 2. GENERATE SUMMARY ---
    print("📝 Generating Summary...")
    full_text = " ".join([s['text'] for s in transcription.segments])[:25000] 
    
    summary_prompt = f"Summarize this video transcript in as much detail as possible , make sure to not miss naything thats mentioned in the transcript\n{full_text}"
    summary_res = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": summary_prompt}],
        model="meta-llama/llama-4-scout-17b-16e-instruct"
    )
    ai_summary = summary_res.choices[0].message.content

    # --- 3. PREPARE RECORDS (Summary + Chunks) ---
    print("🧠 Preparing records...")
    records = []
    video_id = yt.video_id 
    
    # A. Add the "Super Chunk" (The Summary)
    # We give it a hardcoded ID "global_summary" so we can find it easily later.
    records.append({
        "id": "global_summary", 
        "text": ai_summary,
        "start_time": 0.0,
        "end_time": 0.0,
        "url": youtube_url,
        "title": "SUMMARY_CARD"
    })

    # B. Add the Regular Chunks
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
                "id": f"{video_id}_{len(records)}", # Unique ID
                "text": current_text.strip(),
                "start_time": chunk_start,
                "end_time": end,
                "url": youtube_url,
                "title": yt.title
            })
            current_text = ""
            chunk_start = start 
        
        current_text += " " + text
    
    # Add leftover chunk
    if current_text:
        records.append({
            "id": f"{video_id}_{len(records)}",
            "text": current_text.strip(),
            "start_time": chunk_start,
            "end_time": transcription.segments[-1]['end'],
            "url": youtube_url,
            "title": yt.title
        })

    # --- 4. UPLOAD EVERYTHING TO ONE NAMESPACE ---
    try:
        # This saves BOTH the summary and the chunks into the 'video_id' folder
        index.upsert_records(namespace=video_id, records=records)
        print(f"🎉 SUCCESS! Saved {len(records)} records to namespace '{video_id}'")
        return video_id, yt.title
        
    except Exception as e:
        print(f"❌ Error uploading: {e}")
        return None, None