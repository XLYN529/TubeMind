import os
from dotenv import load_dotenv
from pinecone import Pinecone
from groq import Groq

load_dotenv()

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index = pc.Index("videodb")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def format_timestamp(seconds):
    """Converts seconds (e.g., 125) to HH:MM:SS format."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def get_answer(question, video_id):
    """
    Retrieves answer using Hybrid Search:
    1. Fetches 'Global Context' (Summary) for high-level understanding.
    2. Searches 'Specific Chunks' for detailed answers.
    """
    #print(f"🤔 Brain searching inside Namespace: {video_id}...")

    # --- STEP 1: FETCH GLOBAL CONTEXT (The Summary) ---
    # We search specifically for the summary card we created in the indexer.
    global_context = "Summary not available."
    try:
        # Instead of searching, we FETCH the specific ID we saved.
        # This is faster and avoids the "filter" error.
        fetch_response = index.fetch(ids=["global_summary"], namespace=video_id)
        
        # Pinecone fetch returns a dictionary like {'vectors': {'global_summary': {...}}}
        if fetch_response and 'vectors' in fetch_response and 'global_summary' in fetch_response['vectors']:
            # Depending on your SDK version, metadata might be in 'metadata' or 'fields'
            data = fetch_response['vectors']['global_summary']
            # Try 'metadata' first (standard), then 'fields' (inference API)
            meta = data.get('metadata') or data.get('fields')
            
            if meta:
                global_context = meta.get('text', "")
                print("✅ Global Context Loaded.")
        else:
            print("⚠️ No Global Context found (Old video?).")

    except Exception as e:
        print(f"⚠️ Error fetching summary: {e}")

    # --- STEP 2: SEARCH FOR SPECIFIC DETAILS ---
    try:
        results = index.search_records(
            namespace=video_id,
            query={"inputs": {"text": question}, "top_k": 5}, 
            fields=["text", "start_time", "end_time"]
        )
    except Exception as e:
        return f"❌ Database Error: {e}"

    # Format the specific chunks
    retrieved_chunks = []
    hits = results.get('result', {}).get('hits', [])
    
    for hit in hits:
        fields = hit.get('fields', {})
        text = fields.get('text', '')
        start = fields.get('start_time', 0.0)
        
        # We attach the timestamp to the text so the AI can cite it
        retrieved_chunks.append(f"[{format_timestamp(start)}] {text}")

    # Join them into one block of text
    specific_context = "\n\n".join(retrieved_chunks)

    # --- STEP 3: THE HYBRID PROMPT ---
    # We give the AI both the Summary and the Details.
    
    system_prompt = f"""
    You are an expert AI Video Tutor.
    
    --- GLOBAL CONTEXT (Video Summary) ---
    {global_context}
    
    --- SPECIFIC SEARCH RESULTS ---
    {specific_context}
    
    INSTRUCTIONS:
    1. If the user asks general questions (e.g. "What is the video about?", "Summary"), use the GLOBAL CONTEXT.
    2. If the user asks specific questions, use the SPECIFIC SEARCH RESULTS.Define terms, or provide examples to make the answer easier to understand.
    ENHANCEMENT: You may use your own general knowledge to explain concepts,
    3. Always cite timestamps (e.g. [05:20]) if you are using information from a specific chunk.
    4. If the answer is not in the video, say "I couldn't find that in the video.
    """
    
    user_message = f"Question: {question}"
    
    # --- STEP 4: GENERATE ANSWER ---
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            # 'versatile' is usually better for RAG than 'scout', but 'scout' works too.
            model="llama-3.3-70b-versatile", 
        )
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        return f" LLM Error: {e}"

# --- TEST AREA ---
if __name__ == "__main__":
    # You must provide a valid video_id from your database to test this!
    # Example: get_answer("What is this about?", "dQw4w9WgXcQ")
    pass
