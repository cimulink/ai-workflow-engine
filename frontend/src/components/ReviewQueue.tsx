/**
 * ReviewQueue Component - Real-time human review interface
 */

import React, { useState, useEffect } from 'react'
import { useAgentSubscriber, getPendingWorkflows, PendingWorkflow } from '../lib/ag-ui-client-fixed'
import { DocumentReviewCard } from './DocumentReviewCard'

export function ReviewQueue() {
  const [pendingReviews, setPendingReviews] = useState<PendingWorkflow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Subscribe to AG-UI events for real-time updates
  const subscriber = useAgentSubscriber({
    onGenerativeUI: ({ component, props }) => {
      if (component === 'DocumentReview') {
        // Add new review to queue
        const newReview: PendingWorkflow = {
          workflow_id: props.workflowId,
          status: 'pending_review',
          extracted_data: props.extractedData,
          validation_reasons: props.reviewReasons,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
        
        setPendingReviews(prev => {
          // Avoid duplicates
          const exists = prev.some(r => r.workflow_id === newReview.workflow_id)
          if (exists) return prev
          return [...prev, newReview]
        })
      }
    },
    
    onHumanInputRequired: ({ workflow_id, reasons }) => {
      // Show notification that review is needed
      showNotification(`Document ${workflow_id} needs review: ${reasons?.join(', ')}`)
    }
  })
  
  // Load pending reviews on mount
  useEffect(() => {
    loadPendingReviews()
    
    // Refresh every 30 seconds
    const interval = setInterval(loadPendingReviews, 30000)
    return () => clearInterval(interval)
  }, [])
  
  const loadPendingReviews = async () => {
    try {
      setLoading(true)
      const workflows = await getPendingWorkflows()
      setPendingReviews(workflows)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pending reviews')
    } finally {
      setLoading(false)
    }
  }
  
  const handleReviewComplete = (workflowId: string) => {
    // Remove from pending reviews
    setPendingReviews(prev => 
      prev.filter(review => review.workflow_id !== workflowId)
    )
    
    showNotification(`Document ${workflowId} review completed!`)
  }
  
  const showNotification = (message: string) => {
    // Simple notification - could be enhanced with a proper notification system
    console.log('Notification:', message)
    
    // Create a simple toast notification
    const toast = document.createElement('div')
    toast.className = 'notification-toast'
    toast.textContent = message
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #4CAF50;
      color: white;
      padding: 12px 20px;
      border-radius: 6px;
      z-index: 1000;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `
    
    document.body.appendChild(toast)
    
    setTimeout(() => {
      toast.remove()
    }, 4000)
  }
  
  if (loading && pendingReviews.length === 0) {
    return (
      <div className="review-queue loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <span>Loading pending reviews...</span>
        </div>
      </div>
    )
  }
  
  return (
    <div className="review-queue">
      <div className="queue-header">
        <h2>📋 Review Queue</h2>
        <div className="queue-stats">
          <span className="count-badge">
            {pendingReviews.length} pending
          </span>
          <button 
            onClick={loadPendingReviews}
            className="refresh-btn"
            disabled={loading}
          >
            🔄 {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>
      
      {error && (
        <div className="error-banner">
          ❌ {error}
          <button onClick={loadPendingReviews}>Retry</button>
        </div>
      )}
      
      {pendingReviews.length === 0 ? (
        <div className="empty-queue">
          <div className="empty-state">
            <div className="empty-icon">🎉</div>
            <h3>No documents pending review!</h3>
            <p>All workflows are either completed or in progress.</p>
            <div className="empty-actions">
              <h4>How to submit documents:</h4>
              <ul>
                <li>Use the Document Processor above</li>
                <li>Run: <code>python legacy/submit.py --sample</code></li>
                <li>Run: <code>python legacy/submit.py "Your content here"</code></li>
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div className="review-list">
          {pendingReviews.map(review => (
            <DocumentReviewCard
              key={review.workflow_id}
              review={review}
              onReviewComplete={handleReviewComplete}
            />
          ))}
        </div>
      )}
    </div>
  )
}