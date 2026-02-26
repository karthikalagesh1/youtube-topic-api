# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import re
import yt_dlp
import whisper
import tempfile
import os

app = FastAPI()

# Request / Response models
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

# Download audio using yt-dlp
def download_audio(video_url, output_path):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

# Search for topic in transcript segments
def search_topic_in_segments(segments, topic):
    topic_lower = topic.lower()
    for seg in segments:
        if topic_lower in seg['text'].lower():
            return seconds_to_hhmmss(seg['start'])
    return "00:00:00"

@app.post("/ask", response_model=ResponseBody)
def ask(request: RequestBody):
    video_id = extract_video_id(request.video_url)
    timestamp = "00:00:00"

    # 1️⃣ Try YouTube transcript first
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        timestamp = search_topic_in_segments(transcript, request.topic)
    except TranscriptsDisabled:
        # 2️⃣ Fallback to Whisper if no transcript
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.mp3")
            download_audio(request.video_url, audio_path)
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, verbose=False)
            # Whisper returns segments with start times
            if "segments" in result:
                for seg in result["segments"]:
                    if request.topic.lower() in seg["text"].lower():
                        timestamp = seconds_to_hhmmss(seg["start"])
                        break

    return {
        "timestamp": timestamp,
        "video_url": request.video_url,
        "topic": request.topic
    }
