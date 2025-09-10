/**
 * AG-UI Client Configuration for the Document Workflow Engine
 */

import { AgentClient } from '@ag-ui/client'

export interface DocumentProcessorState {
  workflow_id?: string
  status?: string
  current_step?: string
  extracted_data?: Record<string, any>
  validation_result?: {
    is_valid: boolean
    needs_review: boolean
    reasons: string[]
  }
  human_review_required?: boolean
}

export interface WorkflowMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface PendingWorkflow {
  workflow_id: string
  status: string
  extracted_data: Record<string, any>
  validation_reasons: string[]
  created_at: string
  updated_at: string
}

// AG-UI Client configuration
export const agentConfig = {
  agentUrl: 'http://localhost:8000/agent',
  headers: {
    'Content-Type': 'application/json',
  }
}

// API helper functions
export async function getPendingWorkflows(): Promise<PendingWorkflow[]> {
  const response = await fetch('/api/workflows/pending')
  if (!response.ok) {
    throw new Error('Failed to fetch pending workflows')
  }
  const data = await response.json()
  return data.pending_workflows
}

export async function approveWorkflow(
  workflowId: string, 
  updatedData?: Record<string, any>
): Promise<void> {
  const response = await fetch(`/api/workflows/${workflowId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      workflow_id: workflowId,
      action: 'approve',
      updated_data: updatedData
    })
  })
  
  if (!response.ok) {
    throw new Error('Failed to approve workflow')
  }
}

export async function rejectWorkflow(workflowId: string): Promise<void> {
  const response = await fetch(`/api/workflows/${workflowId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to reject workflow')
  }
}

export async function getWorkflowDetails(workflowId: string): Promise<any> {
  const response = await fetch(`/api/workflows/${workflowId}`)
  if (!response.ok) {
    throw new Error('Failed to fetch workflow details')
  }
  return response.json()
}