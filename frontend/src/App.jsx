import { useState } from 'react'
import './App.css'
import SearchTab from './components/SearchTab'
import UrlTab from './components/UrlTab'
import logo from './assets/logotsmusicl.png'

function App() {
  const [activeTab, setActiveTab] = useState('search')

  return (
    <div className="app">
      <header className="header">
        <div className="container">
          <div className="logo">
            <img src={logo} alt="FastMusic Logo" className="logo-image" />
            <div className="logo-text">
              <h1 className="logo-title">FastMusic</h1>
              {/* <p className="subtitle">Download your favorite music from YouTube</p> */}
            </div>
          </div>

          <div className="tabs">
            <button
              className={`tab ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => setActiveTab('search')}
            >
              Search & Download
            </button>
            <button
              className={`tab ${activeTab === 'url' ? 'active' : ''}`}
              onClick={() => setActiveTab('url')}
            >
              Download from URL
            </button>
          </div>
        </div>
      </header>

      <main className="main">
        <div className="container">
          <div className="tab-content">
            {activeTab === 'search' && <SearchTab />}
            {activeTab === 'url' && <UrlTab />}
          </div>
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p>Sail the seas</p>
        </div>
      </footer>
    </div>
  )
}

export default App
