/**
 * Main App Component for AI Workflow Engine - AG-UI Frontend
 */

import React, { useState } from 'react'
import { DocumentProcessor } from './components/DocumentProcessor'
import { ReviewQueue } from './components/ReviewQueue'
import './App.css'

type ActiveTab = 'processor' | 'review'

function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('processor')
  const [workflowResults, setWorkflowResults] = useState<any[]>([])
  
  const handleWorkflowComplete = (result: any) => {
    setWorkflowResults(prev => [...prev, result])
    
    // If workflow needs review, switch to review tab
    if (result?.state?.human_review_required) {
      setActiveTab('review')
    }
  }
  
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <h1>🤖 AI Workflow Engine</h1>
            <span className="subtitle">Powered by AG-UI Protocol</span>
          </div>
          
          <nav className="main-nav">
            <button 
              className={`nav-btn ${activeTab === 'processor' ? 'active' : ''}`}
              onClick={() => setActiveTab('processor')}
            >
              📄 Document Processor
            </button>
            <button 
              className={`nav-btn ${activeTab === 'review' ? 'active' : ''}`}
              onClick={() => setActiveTab('review')}
            >
              📋 Review Queue
            </button>
          </nav>
          
          <div className="header-stats">
            <div className="stat-item">
              <span className="stat-label">Processed:</span>
              <span className="stat-value">{workflowResults.length}</span>
            </div>
          </div>
        </div>
      </header>
      
      <main className="app-main">
        <div className="main-content">
          {activeTab === 'processor' && (
            <div className="tab-content">
              <DocumentProcessor onWorkflowComplete={handleWorkflowComplete} />
            </div>
          )}
          
          {activeTab === 'review' && (
            <div className="tab-content">
              <ReviewQueue />
            </div>
          )}
        </div>
      </main>
      
      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-info">
            <p>
              🚀 Real-time AI document processing with human-in-the-loop capabilities
            </p>
            <p>
              <strong>Features:</strong> Streaming responses • Interactive review • 
              Multi-format support • State persistence
            </p>
          </div>
          
          <div className="connection-status">
            <div className="status-indicator online">
              <span className="status-dot"></span>
              AG-UI Server Connected
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App