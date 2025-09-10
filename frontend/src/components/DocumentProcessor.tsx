/**
 * DocumentProcessor Component - Main document submission and processing interface
 */

import React, { useState } from 'react'
import { useAgent, DocumentProcessorState } from '../lib/ag-ui-client-fixed'

interface DocumentProcessorProps {
  onWorkflowComplete?: (result: any) => void
}

export function DocumentProcessor({ onWorkflowComplete }: DocumentProcessorProps) {
  const [document, setDocument] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  
  const { sendMessage, messages, isRunning, state } = useAgent<DocumentProcessorState>({
    agentUrl: 'http://localhost:8000/agent',
    onRunFinished: (result) => {
      setIsProcessing(false)
      onWorkflowComplete?.(result)
    },
    onRunStarted: () => {
      setIsProcessing(true)
    }
  })
  
  const handleSubmit = async () => {
    if (!document.trim()) return
    
    setIsProcessing(true)
    await sendMessage({
      role: 'user',
      content: document
    })
  }
  
  const handleSampleInvoice = () => {
    const sampleInvoice = `INVOICE

From: Acme Consulting Services
Address: 123 Business St, Corporate City, CC 12345
Phone: (555) 123-4567

Bill To: ABC Corporation
Address: 456 Client Ave, Customer Town, CT 67890

Invoice Number: INV-2024-001
Date: September 8, 2024
Due Date: October 8, 2024

Description of Services:
- Strategic consulting services (40 hours @ $75/hour): $3,000.00
- Project management fee: $500.00
- Travel expenses: $250.00

Subtotal: $3,750.00
Tax (8.5%): $318.75
Total Amount Due: $4,068.75

Payment Terms: Net 30 days
Payment Methods: Check, Wire Transfer, ACH

Thank you for your business!`
    
    setDocument(sampleInvoice)
  }
  
  const handleSampleTicket = () => {
    const sampleTicket = `Support Ticket #12345

From: angry.customer@email.com
Subject: URGENT - Complete system failure!!!
Priority: High
Created: 2024-09-09 14:30:00

Dear Support Team,

I am absolutely FURIOUS! Your software has completely crashed our entire operation and we're losing thousands of dollars every minute this continues. This is completely unacceptable!

The security dashboard is showing multiple vulnerability alerts and our authentication system appears to be compromised. This is a CRITICAL security issue that needs immediate attention.

I demand immediate escalation to your senior technical team and expect a resolution within the hour or we will be seeking legal action.

This level of service is completely unacceptable for a premium customer like ourselves.

Extremely frustrated,
John Doe
CEO, Important Corp`
    
    setDocument(sampleTicket)
  }
  
  return (
    <div className="document-processor">
      <div className="header">
        <h1>🤖 AI Document Processor</h1>
        <p>Submit documents for intelligent processing with real-time streaming</p>
      </div>
      
      <div className="input-section">
        <div className="sample-buttons">
          <button onClick={handleSampleInvoice} className="sample-btn">
            📄 Load Sample Invoice ($4,068.75)
          </button>
          <button onClick={handleSampleTicket} className="sample-btn">
            🎫 Load Sample Support Ticket (Irate Customer)
          </button>
        </div>
        
        <textarea
          value={document}
          onChange={(e) => setDocument(e.target.value)}
          placeholder="Paste your document content here (invoice, support ticket, contract, etc.)..."
          className="document-input"
          rows={15}
        />
        
        <button 
          onClick={handleSubmit}
          disabled={!document.trim() || isProcessing}
          className={`submit-btn ${isProcessing ? 'processing' : ''}`}
        >
          {isProcessing ? '⏳ Processing...' : '🚀 Process Document'}
        </button>
      </div>
      
      <div className="processing-stream">
        <h3>📡 Processing Stream</h3>
        <div className="messages">
          {messages.map((message, idx) => (
            <div key={idx} className={`message ${message.role}`}>
              <div className="message-content">
                {message.content}
              </div>
            </div>
          ))}
        </div>
        
        {isRunning && (
          <div className="processing-indicator">
            <div className="spinner"></div>
            <span>AI agent is working...</span>
          </div>
        )}
      </div>
      
      {state && (
        <div className="workflow-state">
          <h3>📊 Workflow State</h3>
          <div className="state-details">
            {state.workflow_id && (
              <div className="state-item">
                <strong>Workflow ID:</strong> {state.workflow_id}
              </div>
            )}
            {state.status && (
              <div className="state-item">
                <strong>Status:</strong> 
                <span className={`status-badge ${state.status}`}>
                  {state.status}
                </span>
              </div>
            )}
            {state.current_step && (
              <div className="state-item">
                <strong>Current Step:</strong> {state.current_step}
              </div>
            )}
            {state.extracted_data && Object.keys(state.extracted_data).length > 0 && (
              <div className="state-item">
                <strong>Extracted Data:</strong>
                <pre className="extracted-data">
                  {JSON.stringify(state.extracted_data, null, 2)}
                </pre>
              </div>
            )}
            {state.validation_result && (
              <div className="state-item">
                <strong>Validation:</strong>
                <div className={`validation-result ${state.validation_result.is_valid ? 'valid' : 'invalid'}`}>
                  {state.validation_result.is_valid ? '✅ Valid' : '❌ Needs Review'}
                  {state.validation_result.reasons && state.validation_result.reasons.length > 0 && (
                    <ul className="validation-reasons">
                      {state.validation_result.reasons.map((reason, i) => (
                        <li key={i}>{reason}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}