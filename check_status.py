#!/usr/bin/env python3
"""
Script to check the status of documents in the workflow.
"""

import sqlite3
import json

def check_document_status(document_id=None):
    """Check the status of documents in the workflow."""
    try:
        conn = sqlite3.connect("workflow.db")
        cursor = conn.cursor()
        
        if document_id:
            # Check specific document in documents table
            cursor.execute("SELECT document_id, status FROM documents WHERE document_id = ?", (document_id,))
            doc_rows = cursor.fetchall()
            
            # Check specific document in checkpoints table
            cursor.execute("SELECT thread_id, metadata FROM checkpoints_v2 WHERE thread_id = ?", (document_id,))
            checkpoint_rows = cursor.fetchall()
        else:
            # Check all documents in documents table
            cursor.execute("SELECT document_id, status FROM documents")
            doc_rows = cursor.fetchall()
            
            # Check all documents in checkpoints table
            cursor.execute("SELECT thread_id, metadata FROM checkpoints_v2")
            checkpoint_rows = cursor.fetchall()
        
        print("Documents Table:")
        print(f"{'Document ID':<40} {'Status':<20}")
        print("-" * 60)
        
        if doc_rows:
            for row in doc_rows:
                doc_id, status = row
                print(f"{doc_id:<40} {status:<20}")
        else:
            print("No documents found in documents table.")
        
        print("\nCheckpoints Table:")
        print(f"{'Document ID':<40} {'Status':<20}")
        print("-" * 60)
        
        if checkpoint_rows:
            for row in checkpoint_rows:
                thread_id, metadata = row
                status = "Unknown"
                
                # Try to extract status from metadata
                if metadata:
                    try:
                        metadata_dict = json.loads(metadata)
                        # Look for status in metadata
                        if isinstance(metadata_dict, dict):
                            status = metadata_dict.get("status", "Unknown")
                    except:
                        pass
                
                print(f"{thread_id:<40} {status:<20}")
        else:
            print("No documents found in checkpoints table.")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking document status: {e}")

def main():
    import sys
    
    if len(sys.argv) > 1:
        document_id = sys.argv[1]
        check_document_status(document_id)
    else:
        check_document_status()

if __name__ == "__main__":
    main()