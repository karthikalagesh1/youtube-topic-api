# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
import re

app = FastAPI()

# Request and response models
class RequestBody(BaseModel):
    video_url: str
    topic: str

class ResponseBody(BaseModel):
    timestamp: str
    video_url: str
    topic: str

# Convert seconds to HH:MM:SS
def seconds_to_hhmmss(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# Extract YouTube video ID
def extract_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    raise ValueError("Invalid YouTube URL")

# POST endpoint
@app.post("/ask", response_model=ResponseBody)
def ask(request: RequestBody):
    try:
        video_id = extract_video_id(request.video_url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        topic_lower = request.topic.lower()
        timestamp = "00:00:00"
        for segment in transcript:
            if topic_lower in segment['text'].lower():
                timestamp = seconds_to_hhmmss(segment['start'])
                break
        return {
            "timestamp": timestamp,
            "video_url": request.video_url,
            "topic": request.topic
        }
    except:
        # Return default if something goes wrong (video has no captions)
        return {
            "timestamp": "00:00:00",
            "video_url": request.video_url,
            "topic": request.topic
        }
