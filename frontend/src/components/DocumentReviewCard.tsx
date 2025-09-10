/**
 * DocumentReviewCard Component - Individual document review interface
 */

import React, { useState } from 'react'
import { approveWorkflow, rejectWorkflow, PendingWorkflow } from '../lib/ag-ui-client-fixed'

interface DocumentReviewCardProps {
  review: PendingWorkflow
  onReviewComplete: (workflowId: string) => void
}

export function DocumentReviewCard({ review, onReviewComplete }: DocumentReviewCardProps) {
  const [editedData, setEditedData] = useState(review.extracted_data)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const handleFieldChange = (key: string, value: any) => {
    setEditedData(prev => ({ ...prev, [key]: value }))
    setError(null) // Clear any previous errors
  }
  
  const handleApprove = async () => {
    try {
      setIsSubmitting(true)
      setError(null)
      
      // Check if data was modified
      const hasChanges = JSON.stringify(editedData) !== JSON.stringify(review.extracted_data)
      
      await approveWorkflow(
        review.workflow_id, 
        hasChanges ? editedData : undefined
      )
      
      onReviewComplete(review.workflow_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve workflow')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const handleReject = async () => {
    try {
      setIsSubmitting(true)
      setError(null)
      
      await rejectWorkflow(review.workflow_id)
      onReviewComplete(review.workflow_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject workflow')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const renderFieldEditor = (key: string, value: any) => {
    const fieldName = key.replace('_', ' ').toUpperCase()
    
    // Handle different field types
    if (key === 'total_amount' || key === 'amount') {
      return (
        <div className="field-group">
          <label className="field-label">{fieldName}</label>
          <input
            type="number"
            step="0.01"
            value={value || ''}
            onChange={(e) => handleFieldChange(key, parseFloat(e.target.value) || 0)}
            className="field-input number-input"
            placeholder="0.00"
          />
        </div>
      )
    }
    
    if (key === 'sentiment') {
      return (
        <div className="field-group">
          <label className="field-label">{fieldName}</label>
          <select
            value={value || ''}
            onChange={(e) => handleFieldChange(key, e.target.value)}
            className="field-input select-input"
          >
            <option value="">Select sentiment</option>
            <option value="Happy">Happy</option>
            <option value="Neutral">Neutral</option>
            <option value="Frustrated">Frustrated</option>
            <option value="Irate">Irate</option>
          </select>
        </div>
      )
    }
    
    if (key === 'urgency') {
      return (
        <div className="field-group">
          <label className="field-label">{fieldName}</label>
          <select
            value={value || ''}
            onChange={(e) => handleFieldChange(key, e.target.value)}
            className="field-input select-input"
          >
            <option value="">Select urgency</option>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
        </div>
      )
    }
    
    // Default text input
    return (
      <div className="field-group">
        <label className="field-label">{fieldName}</label>
        <input
          type="text"
          value={value || ''}
          onChange={(e) => handleFieldChange(key, e.target.value)}
          className="field-input text-input"
          placeholder={`Enter ${fieldName.toLowerCase()}`}
        />
      </div>
    )
  }
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }
  
  return (
    <div className="review-card">
      <div className="card-header">
        <div className="card-title">
          <h3>📄 Document {review.workflow_id}</h3>
          <span className={`status-badge ${review.status}`}>
            {review.status}
          </span>
        </div>
        
        <div className="review-reasons">
          <strong>Issues requiring review:</strong>
          <div className="reason-list">
            {review.validation_reasons.map((reason, index) => (
              <span key={index} className="reason-badge">
                ⚠️ {reason}
              </span>
            ))}
          </div>
        </div>
        
        <div className="timestamps">
          <small>Created: {formatDate(review.created_at)}</small>
          <small>Updated: {formatDate(review.updated_at)}</small>
        </div>
      </div>
      
      <div className="card-content">
        <div className="extracted-data-section">
          <div className="section-header">
            <h4>✏️ Extracted Data</h4>
            <small>Review and edit the information below</small>
          </div>
          
          <div className="fields-grid">
            {Object.entries(editedData).map(([key, value]) => (
              <div key={key}>
                {renderFieldEditor(key, value)}
              </div>
            ))}
          </div>
        </div>
        
        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}
      </div>
      
      <div className="card-actions">
        <div className="action-buttons">
          <button 
            onClick={handleApprove}
            disabled={isSubmitting}
            className="approve-btn primary-btn"
          >
            {isSubmitting ? '⏳ Approving...' : '✅ Approve & Continue'}
          </button>
          
          <button 
            onClick={handleReject}
            disabled={isSubmitting}
            className="reject-btn secondary-btn"
          >
            {isSubmitting ? '⏳ Rejecting...' : '❌ Reject'}
          </button>
        </div>
        
        <div className="additional-actions">
          <button 
            onClick={() => setShowOriginal(!showOriginal)}
            className="toggle-btn"
          >
            {showOriginal ? '📄 Hide Original' : '📄 Show Original'}
          </button>
        </div>
      </div>
      
      {showOriginal && (
        <div className="original-content">
          <h4>📄 Original Document Content</h4>
          <pre className="content-preview">
            {/* We'd need to fetch the original content from the API */}
            Original document content would be displayed here...
          </pre>
        </div>
      )}
    </div>
  )
}