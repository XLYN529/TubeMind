import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="TubeMind")
st.title("TubeMind ")

API_URL = os.getenv("API_URL","http://127.0.0.1:8000")

# --- 1. SESSION STATE ---
if "video_id" not in st.session_state:
    st.session_state.video_id = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "video_library" not in st.session_state:
    st.session_state.video_library = [] 

if "url_input" not in st.session_state:
    st.session_state.url_input = ""

# --- 2. THE CALLBACK FUNCTION ---
# This function runs BEFORE the page reloads. 
# It handles the logic without crashing the widget state.
def process_video_callback():
    # Get the URL directly from the state
    url = st.session_state.url_input
    
    if not url:
        st.error("Please enter a URL")
        return

    # We use a placeholder for status messages inside the sidebar
    status_msg = st.sidebar.empty() 
    status_msg.info(" Processing... please wait.")

    try:
        response = requests.post(f"{API_URL}/process", json={"url": url})
        
        if response.status_code == 200:
            data = response.json()
            new_id = data.get("video_id")
            new_title = data.get("video_title")
            
            # Switch to new video
            st.session_state.video_id = new_id
            st.session_state.chat_history = [] 
            
            # Add to Library
            if not any(v['id'] == new_id for v in st.session_state.video_library):
                st.session_state.video_library.append({
                    "id": new_id, 
                    "title": new_title
                })
            
            status_msg.success(" Done!")
            
            # THE MAGIC FIX:
            # We clear the input HERE, inside the callback.
            # Since this runs BEFORE the text_input widget is drawn again, it works perfectly.
            st.session_state.url_input = "" 
            
        else:
            status_msg.error(f" Error: {response.text}")

    except Exception as e:
        status_msg.error(f" Connection Error: {e}")

# --- 3. SIDEBAR (The View) ---
with st.sidebar:
    st.header("Add New Video")
    
    # 1. The Input Widget
    # We bind it to 'url_input' so the callback can read/clear it.
    st.text_input("YouTube URL", key="url_input")
    
    # 2. The Button
    # Instead of 'if st.button:', we use 'on_click=' to trigger our callback.
    st.button("Process Video", on_click=process_video_callback)

    # --- THE EPHEMERAL LIBRARY ---
    if len(st.session_state.video_library) > 0:
        st.markdown("---")
        st.header("Session Library")
        
        for video in st.session_state.video_library:
            if video['id'] == st.session_state.video_id:
                st.button(f" {video['title']}", key=video['id'], disabled=True)
            else:
                if st.button(video['title'], key=video['id']):
                    st.session_state.video_id = video['id']
                    st.session_state.chat_history = []
                    st.rerun()

# --- 4. CHAT INTERFACE (Same as before) ---
if st.session_state.video_id:
    # ... (Keep your existing chat interface code here) ...
    # Simple pass to show where it goes:
    current_video = next((v for v in st.session_state.video_library if v['id'] == st.session_state.video_id), None)
    if current_video:
        st.caption(f"Chatting with: **{current_video['title']}**")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about the video..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

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
else:
    st.info(" Paste a URL to start a temporary session.")
