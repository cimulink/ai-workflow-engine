/**
 * Custom AG-UI Client Implementation for the Document Workflow Engine
 */

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

export interface AgentEvent {
  type: string
  data: any
  timestamp: string
  workflow_id?: string
}

export interface PendingWorkflow {
  workflow_id: string
  status: string
  extracted_data: Record<string, any>
  validation_reasons: string[]
  created_at: string
  updated_at: string
}

import { useState, useEffect } from 'react'

// Custom hook for AG-UI agent communication
export function useAgent<T = DocumentProcessorState>(config: {
  agentUrl?: string
  onRunFinished?: (result: any) => void
  onRunStarted?: () => void
}) {
  const [messages, setMessages] = useState<WorkflowMessage[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [state, setState] = useState<T | null>(null)

  const sendMessage = async (message: WorkflowMessage) => {
    try {
      setIsRunning(true)
      config.onRunStarted?.()
      
      // Add user message to display
      setMessages(prev => [...prev, message])
      
      const response = await fetch('/agent/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [message],
          tools: [],
          state: {}
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Decode the chunk
        const chunk = new TextDecoder().decode(value)
        buffer += chunk

        // Process complete lines
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6))
              await handleAgentEvent(eventData)
            } catch (e) {
              console.error('Failed to parse event:', line, e)
            }
          }
        }
      }

      setIsRunning(false)
      config.onRunFinished?.(state)

    } catch (error) {
      console.error('Error sending message:', error)
      setIsRunning(false)
      
      // Add error message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
      }])
    }
  }

  const handleAgentEvent = async (event: AgentEvent) => {
    console.log('Agent event:', event)

    switch (event.type) {
      case 'RUN_STARTED':
        setState(prev => ({
          ...prev,
          workflow_id: event.data.workflow_id,
          status: 'processing'
        } as T))
        break

      case 'TEXT_MESSAGE_CHUNK':
        // Add assistant message chunk
        setMessages(prev => {
          const lastMessage = prev[prev.length - 1]
          if (lastMessage?.role === 'assistant') {
            // Append to existing message
            return [
              ...prev.slice(0, -1),
              { ...lastMessage, content: lastMessage.content + event.data.content }
            ]
          } else {
            // Create new assistant message
            return [...prev, { role: 'assistant', content: event.data.content }]
          }
        })
        break

      case 'TOOL_CALL_CHUNK':
        try {
          const extractedData = JSON.parse(event.data.arguments)
          setState(prev => ({
            ...prev,
            extracted_data: extractedData
          } as T))
        } catch (e) {
          console.error('Failed to parse tool arguments:', e)
        }
        break

      case 'GENERATIVE_UI':
        // Handle UI components (for review interface)
        if (event.data.component === 'DocumentReview') {
          setState(prev => ({
            ...prev,
            human_review_required: true,
            extracted_data: event.data.props.extractedData,
            validation_result: {
              is_valid: false,
              needs_review: true,
              reasons: event.data.props.reviewReasons
            }
          } as T))
        }
        break

      case 'HUMAN_INPUT_REQUIRED':
        setState(prev => ({
          ...prev,
          status: 'pending_review',
          human_review_required: true,
          validation_result: {
            is_valid: false,
            needs_review: true,
            reasons: event.data.reasons
          }
        } as T))
        break

      case 'RUN_FINISHED':
        setState(prev => ({
          ...prev,
          status: event.data.status,
          extracted_data: event.data.final_data
        } as T))
        setIsRunning(false)
        break

      case 'RUN_ERROR':
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `❌ Error: ${event.data.error}`
        }])
        setIsRunning(false)
        break
    }
  }

  return {
    sendMessage,
    messages,
    isRunning,
    state
  }
}

// Custom hook for subscribing to AG-UI events (simplified version)
export function useAgentSubscriber(config: {
  onGenerativeUI?: (event: { component: string, props: any }) => void
  onHumanInputRequired?: (event: { workflow_id: string, reasons: string[] }) => void
}) {
  // In a real implementation, this would connect to WebSocket
  // For now, we'll poll the API for updates
  
  useEffect(() => {
    // This is a simplified implementation
    // In production, you'd use WebSocket for real-time updates
    console.log('AG-UI subscriber configured', config)
  }, [])

  return {} // Return subscriber object
}


// API helper functions (same as before)
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