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
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:3000", 
        "http://127.0.0.1:5173",
        "https://fastmusic.vercel.app"
    ],  # Added your deployed frontend
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
        
        # Configure yt-dlp options optimized for server environment
        # Strategy 1: Balanced approach - good features but YouTube-friendly
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
            'socket_timeout': 180,  # Reduced from 300s
            'retries': 3,  # Reduced from 5
            'fragment_retries': 3,  # Reduced from 5
            'ignoreerrors': False,
            'no_warnings': True,  # Less verbose
            # Simplified headers - less suspicious
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            # Removed extractor_args that might trigger detection
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': request.quality.value,
            }],
        }
        
        # Download using yt-dlp with multiple fallback strategies
        download_successful = False
        last_error = None
        successful_strategy = None
        
        # Strategy 1: Full headers and options
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
                download_successful = True
                successful_strategy = "Strategy 1 (Full options)"
                print(f"✅ {successful_strategy} succeeded")
                
        except Exception as e:
            last_error = e
            print(f"❌ Strategy 1 failed: {str(e)}")
            
            # Strategy 2: Minimal options with different user agent
            try:
                fallback_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': str(output_template),
                    'extractaudio': True,
                    'audioformat': 'mp3',
                    'audioquality': 0,
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 180,
                    'retries': 3,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    },
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': request.quality.value,
                    }],
                }
                
                with yt_dlp.YoutubeDL(fallback_opts) as ydl_fallback:
                    ydl_fallback.download([youtube_url])
                    download_successful = True
                    successful_strategy = "Strategy 2 (Minimal options)"
                    print(f"✅ {successful_strategy} succeeded")
                    
            except Exception as e2:
                last_error = e2
                print(f"❌ Strategy 2 failed: {str(e2)}")
                
                # Strategy 3: Ultra minimal - no postprocessing, just download
                try:
                    minimal_opts = {
                        'format': 'bestaudio[ext=m4a]/bestaudio/best',
                        'outtmpl': str(DOWNLOADS_DIR / f"%(title)s_{unique_id}.%(ext)s"),
                        'noplaylist': True,
                        'quiet': True,
                        'no_warnings': True,
                        'socket_timeout': 120,
                        'retries': 2,
                        'http_headers': {
                            'User-Agent': 'yt-dlp/2024.07.01',
                        },
                    }
                    
                    with yt_dlp.YoutubeDL(minimal_opts) as ydl_minimal:
                        ydl_minimal.download([youtube_url])
                        download_successful = True
                        successful_strategy = "Strategy 3 (Ultra minimal)"
                        print(f"✅ {successful_strategy} succeeded")
                        
                        # Convert to MP3 manually if needed
                        downloaded_files_any = list(DOWNLOADS_DIR.glob(f"*_{unique_id}.*"))
                        if downloaded_files_any:
                            original_file = downloaded_files_any[0]
                            if not original_file.suffix == '.mp3':
                                # Convert to MP3
                                mp3_file = original_file.with_suffix('.mp3')
                                try:
                                    import subprocess
                                    subprocess.run([
                                        'ffmpeg', '-i', str(original_file), 
                                        '-acodec', 'mp3', '-ab', f'{request.quality.value}k',
                                        str(mp3_file)
                                    ], check=True, capture_output=True)
                                    os.remove(original_file)  # Remove original
                                    print(f"🔄 Converted {original_file.suffix} to MP3")
                                except Exception:
                                    # If conversion fails, just rename the file
                                    original_file.rename(mp3_file)
                                    print(f"📝 Renamed {original_file.suffix} to .mp3")
                        
                except Exception as e3:
                    last_error = e3
                    print(f"❌ Strategy 3 failed: {str(e3)}")
        
        if download_successful:
            print(f"🎉 Download completed using {successful_strategy}")
        
        # Handle final errors if all strategies failed
        if not download_successful:
            print(f"💥 All strategies failed. Last error: {str(last_error)}")
            error_msg = str(last_error)
            if any(keyword in error_msg.lower() for keyword in ["bot", "precondition", "player response", "json"]):
                raise HTTPException(
                    status_code=503,
                    detail="YouTube is currently blocking automated requests. This is a temporary issue. Please try again in a few minutes or try a different video."
                )
            elif "timeout" in error_msg.lower():
                raise HTTPException(
                    status_code=408,
                    detail="Download timeout - the video may be too long or the connection is slow. Please try again."
                )
            elif isinstance(last_error, yt_dlp.DownloadError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to download audio: {error_msg}"
                )
            elif isinstance(last_error, yt_dlp.ExtractorError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to extract video information: {error_msg}"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Download failed: {error_msg}"
                )
        
        # Find the downloaded file (could be mp3 or other format that was converted)
        downloaded_files = list(DOWNLOADS_DIR.glob(f"*_{unique_id}.mp3"))
        
        # If no MP3 found, look for any file with the unique ID
        if not downloaded_files:
            downloaded_files = list(DOWNLOADS_DIR.glob(f"*_{unique_id}.*"))
        
        if not downloaded_files:
            raise HTTPException(
                status_code=500,
                detail="Downloaded file not found"
            )
        
        downloaded_file = downloaded_files[0]
        
        # Ensure the file has .mp3 extension for proper download
        if not downloaded_file.suffix == '.mp3':
            mp3_file = downloaded_file.with_suffix('.mp3')
            downloaded_file.rename(mp3_file)
            downloaded_file = mp3_file
        
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