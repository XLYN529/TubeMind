import os
import tempfile
from pinecone import Pinecone
from groq import Groq
from pytubefix import YouTube 

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index = pc.Index("videodb")

def generate_smart_summary(full_text):
    """
    Summarizes text of ANY length using Map-Reduce.
    1. If short: Summarize directly.
    2. If long: Split -> Summarize chunks -> Combine -> Final Summary.
    """
    CHUNK_SIZE = 20000  
    
    # CASE A: Short Video 
    if len(full_text) < CHUNK_SIZE:
        #print(" Text is short. Summarizing directly...")
        prompt = f"Summarize this video transcript in detail make sure to not leave anything from the transcript\n{full_text}"
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        return res.choices[0].message.content

    # CASE B: Long Video 
    #print(f" Text is long ({len(full_text)} chars). Using Map-Reduce...")
    
    # 1. MAP: Chunk the text
    chunks = [full_text[i:i+CHUNK_SIZE] for i in range(0, len(full_text), CHUNK_SIZE)]
    partial_summaries = []
    
    # 2. SUMMARIZE EACH CHUNK
    for i, chunk in enumerate(chunks):
        #print(f"   - Summarizing part {i+1}/{len(chunks)}...")
        prompt = f"Summarize this segment of a video transcript in detail make sure to not leave anything:\n{chunk}"
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )
        partial_summaries.append(res.choices[0].message.content)

    # 3. REDUCE: Combine partial summaries into one Master Summary
    #print("   - Combining summaries...")
    combined_text = " ".join(partial_summaries)
    
    final_prompt = f"""
    Here are summaries of different parts of a video, in chronological order.
    Combine them into one cohesive, comprehensive summary of the entire video.
    
    Partial Summaries:
    {combined_text}
    """
    
    final_res = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": final_prompt}],
        model="meta-llama/llama-4-scout-17b-16e-instruct"
    )
    
    return final_res.choices[0].message.content

def process_video(youtube_url):
    #print(f"Processing: {youtube_url}")
    
    # DOWNLOAD & TRANSCRIBE
    with tempfile.TemporaryDirectory() as temp_dir:
        yt = YouTube(youtube_url, client='WEB')
        stream = yt.streams.filter(only_audio=True).first()
        downloaded_path = stream.download(output_path=temp_dir)
        
        with open(downloaded_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(downloaded_path, file.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json", 
            )

    # GENERATE SUMMARY
    #print(" Generating Summary...")
    full_text = " ".join([s['text'] for s in transcription.segments])
    
    try:
        # Call our new smart helper function
        ai_summary = generate_smart_summary(full_text)
        #print(f" Final Summary Generated ({len(ai_summary)} chars)")
    except Exception as e:
        #print(f"⚠️ Summary failed: {e}")
        ai_summary = "Summary unavailable."

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
        #print(f"🎉 SUCCESS! Saved {len(records)} records to namespace '{video_id}'")
        return video_id, yt.title
        
    except Exception as e:
        #print(f"❌ Error uploading: {e}")
        return None, None
