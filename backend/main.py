import os
import uuid
import base64
from pathlib import Path
from typing import Optional, List
import shutil
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator
import uvicorn
import yt_dlp

app = FastAPI(title="FastMusic API", description="Download audio from YouTube URLs")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],  # Vite dev server and other common ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # Expose this header to frontend
)

# Create downloads directory if it doesn't exist
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

class AudioQuality(str, Enum):
    LOW = "128"      # Low quality (128 kbps)
    MEDIUM = "192"   # Medium quality (192 kbps)
    HIGH = "256"     # High quality (256 kbps)
    VERY_HIGH = "320"  # Very high quality (320 kbps)
    
    @classmethod
    def default(cls):
        return cls.HIGH  # Default to high quality

class YouTubeRequest(BaseModel):
    encoded_url: str
    quality: Optional[AudioQuality] = AudioQuality.default()
    
class DownloadResponse(BaseModel):
    message: str
    filename: str

class SearchResult(BaseModel):
    video_id: str
    title: str
    channel: str
    duration: str
    
class SearchResponse(BaseModel):
    results: List[SearchResult]

def cleanup_file(file_path: str):
    """Background task to clean up downloaded files after serving"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass  # Ignore cleanup errors

def format_duration(seconds):
    """Convert seconds to MM:SS format"""
    if not seconds:
        return "Unknown"
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "Unknown"

@app.get("/search", response_model=SearchResponse)
async def search_youtube(q: str = Query(..., description="Search query")):
    """
    Search for YouTube videos and return top 5 results
    """
    try:
        if not q or len(q.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Search query cannot be empty"
            )
        
        # Configure yt-dlp options for search
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'ignoreerrors': True,
        }
        
        search_results = []
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for top 5 results
                search_query = f"ytsearch5:{q}"
                search_info = ydl.extract_info(search_query, download=False)
                
                if not search_info or 'entries' not in search_info:
                    return SearchResponse(results=[])
                
                for entry in search_info['entries']:
                    if entry and entry.get('id'):
                        # Use basic search data only - much faster
                        search_results.append(SearchResult(
                            video_id=entry['id'],
                            title=entry.get('title', 'Unknown Title'),
                            channel=entry.get('uploader', 'Unknown Channel'),
                            duration=format_duration(entry.get('duration'))
                        ))
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Search failed: {str(e)}"
            )
        
        return SearchResponse(results=search_results)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during search: {str(e)}"
        )

@app.post("/download", response_model=DownloadResponse)
async def download_youtube_audio(request: YouTubeRequest, background_tasks: BackgroundTasks):
    """
    Download audio from a YouTube URL (base64 encoded) and return as MP3 file
    """
    try:
        # Decode the base64 encoded URL
        try:
            decoded_bytes = base64.b64decode(request.encoded_url)
            youtube_url = decoded_bytes.decode('utf-8')
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 encoded URL: {str(e)}"
            )
        
        # Generate unique filename to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        output_template = DOWNLOADS_DIR / f"%(title)s_{unique_id}.%(ext)s"
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_template),
            'extractaudio': True,
            'audioformat': 'mp3',
            'audioquality': 0,  # Best quality
            'embed_metadata': True,
            'add_metadata': True,
            'noplaylist': True,
            'trim_filenames': 100,
            'socket_timeout': 300,  # 5 minute timeout
            'retries': 3,
            'ignoreerrors': False,
            'no_warnings': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': request.quality.value,
            }],
        }
        
        # Download using yt-dlp
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to validate URL
                # info = ydl.extract_info(youtube_url, download=False)
                # if not info:
                #     raise HTTPException(
                #         status_code=400,
                #         detail="Could not extract video information"
                #     )
                
                # Download the audio
                ydl.download([youtube_url])
                
        except yt_dlp.DownloadError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to download audio: {str(e)}"
            )
        except yt_dlp.ExtractorError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract video information: {str(e)}"
            )
        except Exception as e:
            if "timeout" in str(e).lower():
                raise HTTPException(
                    status_code=408,
                    detail="Download timeout - video may be too long or connection is slow"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Download failed: {str(e)}"
            )
        
        # Find the downloaded file
        downloaded_files = list(DOWNLOADS_DIR.glob(f"*_{unique_id}.mp3"))
        
        if not downloaded_files:
            raise HTTPException(
                status_code=500,
                detail="Downloaded file not found"
            )
        
        downloaded_file = downloaded_files[0]
        
        # Schedule file cleanup after response is sent
        background_tasks.add_task(cleanup_file, str(downloaded_file))
        
        return FileResponse(
            path=str(downloaded_file),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f'attachment; filename="{downloaded_file.name}"'}
        )
        
    except Exception as e:
        # Handle any unexpected errors
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "FastMusic API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)