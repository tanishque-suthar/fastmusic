import { useState } from 'react'
import './UrlTab.css'
import { cleanTitle } from '../utils/titleUtils'

const API_BASE_URL = 'http://localhost:8000'

function UrlTab() {
    const [url, setUrl] = useState('')
    const [isDownloading, setIsDownloading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
    const [selectedQuality, setSelectedQuality] = useState('256')

    const qualityOptions = [
        { value: '128', label: 'Low (128 kbps)', description: 'Smaller file size' },
        { value: '192', label: 'Medium (192 kbps)', description: 'Good balance' },
        { value: '256', label: 'High (256 kbps)', description: 'Recommended' },
        { value: '320', label: 'Very High (320 kbps)', description: 'Best quality' }
    ]

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

            const requestData = {
                encoded_url: encodedUrl,
                quality: selectedQuality
            }

            console.log('Frontend sending request data:', requestData)
            console.log('Selected quality:', selectedQuality)
            console.log('Encoded URL:', encodedUrl)
            console.log('Original URL:', url.trim())

            const response = await fetch(`${API_BASE_URL}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
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
                    // Clean the filename by removing underscores and UIDs
                    const originalFilename = filenameMatch[1]
                    const nameWithoutExt = originalFilename.replace(/\.(mp3|mp4|wav|m4a)$/i, '')
                    const cleanedName = cleanTitle(nameWithoutExt)
                    const extension = originalFilename.match(/\.(mp3|mp4|wav|m4a)$/i)?.[0] || '.mp3'
                    filename = cleanedName + extension
                    console.log(`Cleaned filename: ${filename}`)
                    console.log(`Original filename: ${originalFilename}`)
                    console.log(`Name without extension: ${nameWithoutExt}`)
                    console.log(`Cleaned name: ${cleanedName}`)
                    console.log(`Extension: ${extension}`)
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

                <div className="quality-selector">
                    <label htmlFor="quality-select-url" className="quality-label">
                        Audio Quality:
                    </label>
                    <select
                        id="quality-select-url"
                        value={selectedQuality}
                        onChange={(e) => setSelectedQuality(e.target.value)}
                        className="quality-select"
                    >
                        {qualityOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label} - {option.description}
                            </option>
                        ))}
                    </select>
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
