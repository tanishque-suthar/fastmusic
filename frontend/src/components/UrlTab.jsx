import { useState } from 'react'
import './UrlTab.css'

const API_BASE_URL = 'http://localhost:8000'

function UrlTab() {
    const [url, setUrl] = useState('')
    const [isDownloading, setIsDownloading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    const isValidYouTubeUrl = (url) => {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/
        return youtubeRegex.test(url)
    }

    const handleDownload = async (e) => {
        e.preventDefault()

        if (!url.trim()) {
            setError('Please enter a YouTube URL')
            return
        }

        if (!isValidYouTubeUrl(url)) {
            setError('Please enter a valid YouTube URL')
            return
        }

        setIsDownloading(true)
        setError('')
        setSuccess('')

        try {
            // Encode the YouTube URL
            const encodedUrl = btoa(url.trim())

            const response = await fetch(`${API_BASE_URL}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    encoded_url: encodedUrl
                })
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Download failed')
            }

            // Create download link
            const blob = await response.blob()
            const downloadUrl = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = downloadUrl

            // Try to get filename from response headers
            const contentDisposition = response.headers.get('content-disposition')
            console.log(contentDisposition)
            let filename = 'audio.mp3'
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
                if (filenameMatch) {
                    filename = filenameMatch[1]
                }
            }

            a.download = filename
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(downloadUrl)
            document.body.removeChild(a)

            setSuccess('Download completed successfully!')
            setUrl('')

        } catch (err) {
            setError(err.message || 'Download failed. Please check the URL and try again.')
        } finally {
            setIsDownloading(false)
        }
    }

    return (
        <div className="url-tab">
            <div className="url-header">
                <h2 className="url-title">Download from YouTube URL</h2>
                <p className="url-description-text">
                    Have a specific YouTube video URL? Paste it below to download it directly as a high-quality MP3 file.
                </p>
            </div>

            <form onSubmit={handleDownload} className="url-form">
                <div className="url-input-group">
                    <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="https://www.youtube.com/watch?v=..."
                        className="url-input"
                        disabled={isDownloading}
                    />
                    <button
                        type="submit"
                        className="download-button"
                        disabled={isDownloading || !url.trim()}
                    >
                        {isDownloading ? (
                            <>
                                <span className="loading-spinner"></span>
                                Downloading...
                            </>
                        ) : (
                            <>
                                Download MP3
                            </>
                        )}
                    </button>
                </div>
            </form>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {success && (
                <div className="success-message">
                    {success}
                </div>
            )}

            <div className="url-examples">
                <h4>Supported URL formats:</h4>
                <ul>
                    <li>https://www.youtube.com/watch?v=VIDEO_ID</li>
                    <li>https://youtu.be/VIDEO_ID</li>
                    <li>https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID</li>
                </ul>
            </div>
        </div>
    )
}

export default UrlTab
