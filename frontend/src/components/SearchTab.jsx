import { useState } from 'react'
import './SearchTab.css'

const API_BASE_URL = 'http://localhost:8000'

function SearchTab() {
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [isSearching, setIsSearching] = useState(false)
    const [downloadingIds, setDownloadingIds] = useState(new Set())
    const [error, setError] = useState('')

    const handleSearch = async (e) => {
        e.preventDefault()
        if (!searchQuery.trim()) return

        setIsSearching(true)
        setError('')

        try {
            const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(searchQuery)}`)
            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || 'Search failed')
            }

            setSearchResults(data.results || [])
        } catch (err) {
            setError(err.message || 'Failed to search. Please try again.')
            setSearchResults([])
        } finally {
            setIsSearching(false)
        }
    }

    const handleDownload = async (videoId, title) => {
        setDownloadingIds(prev => new Set([...prev, videoId]))
        setError('')

        try {
            // Encode the YouTube URL
            const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`
            const encodedUrl = btoa(youtubeUrl)

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
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `${title.replace(/[^a-z0-9]/gi, '_')}.mp3`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)

        } catch (err) {
            setError(err.message || 'Download failed. Please try again.')
        } finally {
            setDownloadingIds(prev => {
                const newSet = new Set(prev)
                newSet.delete(videoId)
                return newSet
            })
        }
    }

    return (
        <div className="search-tab">
            <div className="search-header">
                <h2 className="search-title">Search & Download Music</h2>
                <p className="search-description">
                    Simply search for any song,
                    and download high-quality MP3 files instantly.
                </p>
            </div>

            <form onSubmit={handleSearch} className="search-form">
                <div className="search-input-group">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search for songs, artists, or albums..."
                        className="search-input"
                        disabled={isSearching}
                    />
                    <button
                        type="submit"
                        className="search-button"
                        disabled={isSearching || !searchQuery.trim()}
                    >
                        {isSearching ? (
                            <span className="loading-spinner"></span>
                        ) : null}
                        {isSearching ? 'Searching...' : 'Search'}
                    </button>
                </div>
            </form>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {searchResults.length > 0 && (
                <div className="search-results">
                    <h3 className="results-title">Search Results</h3>
                    <div className="results-list">
                        {searchResults.map((result) => (
                            <div key={result.video_id} className="result-item">
                                <div className="result-thumbnail">
                                    <img
                                        src={`https://img.youtube.com/vi/${result.video_id}/mqdefault.jpg`}
                                        alt={result.title}
                                        className="thumbnail-image"
                                    />
                                    <div className="duration-badge">{result.duration}</div>
                                </div>

                                <div className="result-info">
                                    <h4 className="result-title">{result.title}</h4>
                                    <p className="result-channel">{result.channel}</p>
                                </div>

                                <button
                                    onClick={() => handleDownload(result.video_id, result.title)}
                                    disabled={downloadingIds.has(result.video_id)}
                                    className="download-button"
                                >
                                    {downloadingIds.has(result.video_id) ? (
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
                        ))}
                    </div>
                </div>
            )}

            {!isSearching && searchQuery && searchResults.length === 0 && !error && (
                <div className="no-results">
                    <p>No results found for "{searchQuery}"</p>
                    <p>Try different keywords or check your spelling.</p>
                </div>
            )}
        </div>
    )
}

export default SearchTab
