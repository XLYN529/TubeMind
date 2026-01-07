import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="TubeMind")
st.title("TubeMind 🧠")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- 1. SESSION STATE ---
if "video_id" not in st.session_state:
    st.session_state.video_id = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "video_library" not in st.session_state:
    st.session_state.video_library = [] 

if "url_input" not in st.session_state:
    st.session_state.url_input = ""

# NEW: Archive to store chat history for EACH video separately
if "chat_archives" not in st.session_state:
    st.session_state.chat_archives = {} 

# --- 2. THE CALLBACK FUNCTION ---
def process_video_callback():
    url = st.session_state.url_input
    if not url: return

    try:
        response = requests.post(f"{API_URL}/process", json={"url": url})
        
        # 1. Check HTTP Status
        if response.status_code == 200:
            data = response.json()
            
            # 2. Check Logical Status
            if data.get("status") == "success":
                new_id = data.get("video_id")
                new_title = data.get("video_title")
                
                # A. Save Current Chat (if exists) before switching
                if st.session_state.video_id:
                    st.session_state.chat_archives[st.session_state.video_id] = st.session_state.chat_history

                # B. Switch to New Video
                st.session_state.video_id = new_id
                st.session_state.video_library.append({
                    "id": new_id, 
                    "title": new_title
                })
                
                # C. Start Fresh Chat for new video
                st.session_state.chat_history = []
                st.session_state.chat_archives[new_id] = [] # Initialize archive
                
                st.session_state.url_input = "" 
                st.success(f"Loaded: {new_title}")
                
            else:
                error_msg = data.get("message", "Unknown Error")
                st.error(f"❌ Server Error: {error_msg}")
                
        else:
            st.error(f"❌ HTTP Error: {response.text}")
            
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")

# --- 3. SIDEBAR (The View) ---
with st.sidebar:
    st.header("Add New Video")
    
    st.text_input("YouTube URL", key="url_input")
    st.button("Process Video", on_click=process_video_callback)

    # --- THE EPHEMERAL LIBRARY ---
    if len(st.session_state.video_library) > 0:
        st.markdown("---")
        st.header("Session Library")
        
        for video in st.session_state.video_library:
            # Highlight current video
            if video['id'] == st.session_state.video_id:
                st.button(f"▶ {video['title']}", key=video['id'], disabled=True)
            else:
                # SWITCH VIDEO LOGIC
                if st.button(video['title'], key=video['id']):
                    
                    # 1. SAVE: Save the chat of the video we are leaving
                    if st.session_state.video_id:
                        st.session_state.chat_archives[st.session_state.video_id] = st.session_state.chat_history
                    
                    # 2. SWITCH: Update active ID
                    st.session_state.video_id = video['id']
                    
                    # 3. LOAD: Retrieve old chat from archive
                    saved_chat = st.session_state.chat_archives.get(video['id'], [])
                    st.session_state.chat_history = saved_chat
                    
                    st.rerun()

# --- 4. CHAT INTERFACE ---
if st.session_state.video_id:
    
    # Simple pass to show what we are chatting with
    current_video = next((v for v in st.session_state.video_library if v['id'] == st.session_state.video_id), None)
    if current_video:
        st.caption(f"Chatting with: **{current_video['title']}**")
    
    # Display Chat
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("Ask about the video..."):
        # Display User Message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Generate AI Answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {"question": prompt, "video_id": st.session_state.video_id}
                    response = requests.post(f"{API_URL}/ask", json=payload)
                    
                    if response.status_code == 200:
                        ai_answer = response.json().get("answer")
                    else:
                        ai_answer = f"Error: {response.text}"
                        
                except Exception as e:
                    ai_answer = f"Connection Error: {e}"
            
            st.markdown(ai_answer)
            st.session_state.chat_history.append({"role": "assistant", "content": ai_answer})
            
            # SAVE IMMEDIATELY: Ensure this new message is saved to the archive
            st.session_state.chat_archives[st.session_state.video_id] = st.session_state.chat_history

else:
    st.info("👈 Paste a URL to start a temporary session.")
