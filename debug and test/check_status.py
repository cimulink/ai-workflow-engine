#!/usr/bin/env python3
"""
Quick script to check workflow status in database
"""

import sqlite3
import json
from pathlib import Path

def check_database_status():
    """Check what's in the database"""
    db_path = "./checkpoints/workflow.db"
    
    if not Path(db_path).exists():
        print("No database found yet")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}")
        
        # Check checkpoints
        cursor.execute("PRAGMA table_info(checkpoints)")
        columns = cursor.fetchall()
        print(f"Checkpoint columns: {[col[1] for col in columns]}")
        
        cursor.execute("SELECT thread_id, checkpoint FROM checkpoints LIMIT 5")
        rows = cursor.fetchall()
        
        print(f"\nFound {len(rows)} recent checkpoints:")
        for thread_id, checkpoint_data in rows:
            if checkpoint_data:
                try:
                    checkpoint = json.loads(checkpoint_data)
                    if 'channel_values' in checkpoint:
                        state = checkpoint['channel_values']
                        # Find workflow state
                        for key, value in state.items():
                            if isinstance(value, dict) and 'status' in value:
                                status = value.get('status')
                                doc_id = value.get('id', thread_id)
                                reason = value.get('reason_for_review', '')
                                print(f"  Document {doc_id}: {status}")
                                if reason:
                                    print(f"    Reason: {reason}")
                                break
                except Exception as e:
                    print(f"  {thread_id}: Error parsing checkpoint - {e}")
            else:
                print(f"  {thread_id}: No checkpoint data")
        
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    check_database_status()