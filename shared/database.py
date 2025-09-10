"""
Shared database operations for the AI Workflow Engine.
"""

import sqlite3
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from .types import AgentState, WorkflowStatus, WorkflowEvent


class WorkflowDatabase:
    """Shared database operations for workflow management"""
    
    def __init__(self, db_path: str = "./checkpoints/workflow.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_ag_ui_tables()
    
    def init_ag_ui_tables(self):
        """Initialize AG-UI specific tables alongside LangGraph tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # AG-UI workflow states table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ag_ui_workflows (
                workflow_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                current_step TEXT NOT NULL,
                document_content TEXT NOT NULL,
                extracted_data TEXT,  -- JSON
                validation_result TEXT,  -- JSON
                human_review_required BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # AG-UI workflow events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ag_ui_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,  -- JSON
                step_name TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (workflow_id) REFERENCES ag_ui_workflows (workflow_id)
            )
        """)
        
        # AG-UI human review queue
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ag_ui_review_queue (
                workflow_id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                assigned_to TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (workflow_id) REFERENCES ag_ui_workflows (workflow_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_agent_state(self, state: AgentState) -> None:
        """Save AG-UI agent state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Handle status field (could be enum or string)
        status_value = state.status.value if hasattr(state.status, 'value') else str(state.status)
        
        cursor.execute("""
            INSERT OR REPLACE INTO ag_ui_workflows (
                workflow_id, status, current_step, document_content,
                extracted_data, validation_result, human_review_required,
                error_message, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state.workflow_id,
            status_value,
            state.current_step,
            state.document_content,
            state.extracted_data.model_dump_json() if state.extracted_data else None,
            state.validation_result.model_dump_json() if state.validation_result else None,
            state.human_review_required,
            state.error_message,
            state.created_at.isoformat(),
            state.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_agent_state(self, workflow_id: str) -> Optional[AgentState]:
        """Get AG-UI agent state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ag_ui_workflows WHERE workflow_id = ?
        """, (workflow_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Convert row to AgentState
        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))
        
        # Parse JSON fields
        if data['extracted_data']:
            from .types import DocumentExtractedData
            data['extracted_data'] = DocumentExtractedData.model_validate_json(data['extracted_data'])
        
        if data['validation_result']:
            from .types import ValidationResult
            data['validation_result'] = ValidationResult.model_validate_json(data['validation_result'])
        
        # Convert timestamps
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Get workflow events
        data['workflow_history'] = self.get_workflow_events(workflow_id)
        
        return AgentState(**data)
    
    def add_workflow_event(self, event: WorkflowEvent) -> None:
        """Add workflow event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ag_ui_events (
                workflow_id, event_type, data, step_name, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            event.workflow_id,
            event.event_type,
            json.dumps(event.data),
            event.step_name,
            event.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def get_workflow_events(self, workflow_id: str) -> List[WorkflowEvent]:
        """Get all events for a workflow"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workflow_id, event_type, data, step_name, timestamp
            FROM ag_ui_events 
            WHERE workflow_id = ?
            ORDER BY timestamp ASC
        """, (workflow_id,))
        
        events = []
        for row in cursor.fetchall():
            events.append(WorkflowEvent(
                workflow_id=row[0],
                event_type=row[1],
                data=json.loads(row[2]),
                step_name=row[3],
                timestamp=row[4]
            ))
        
        conn.close()
        return events
    
    def get_pending_reviews(self) -> List[str]:
        """Get workflows pending human review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workflow_id FROM ag_ui_workflows 
            WHERE human_review_required = TRUE 
            AND status = ?
        """, (WorkflowStatus.PENDING_REVIEW.value,))
        
        workflow_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return workflow_ids
    
    def add_to_review_queue(self, workflow_id: str, reason: str, priority: int = 0) -> None:
        """Add workflow to human review queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO ag_ui_review_queue (
                workflow_id, reason, priority, created_at
            ) VALUES (?, ?, ?, ?)
        """, (workflow_id, reason, priority, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def remove_from_review_queue(self, workflow_id: str) -> None:
        """Remove workflow from review queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM ag_ui_review_queue WHERE workflow_id = ?
        """, (workflow_id,))
        
        conn.commit()
        conn.close()