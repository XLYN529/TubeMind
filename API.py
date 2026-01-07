from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# IMPORT CHANGE: We now use the combined cloud_indexer script
# Ensure your script is named 'cloud_indexer.py' or adjust this import!
from indexer import process_video 
from brain import get_answer

class URLRequest(BaseModel):
    url: str

class QuestionRequest(BaseModel):
    question: str
    video_id: str  

api = FastAPI()

@api.post("/process")
async def process_video_endpoint(item: URLRequest):
    try:
        video_id, video_title = process_video(item.url)
        
        if not video_id:
            return {"status": "error", "message": "Processing failed."}

        return {
            "status": "success", 
            "message": "Video processed!",
            "video_id": video_id,
            "video_title": video_title # <--- SENDING THIS TO FRONTEND
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@api.post("/ask")
async def ask_question_endpoint(item: QuestionRequest): 
    answer = get_answer(item.question, item.video_id)
    return {"answer": answer} 

@api.get("/")
def home():
    return {"message": "TubeMind API is alive"}
