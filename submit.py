#!/usr/bin/env python3
"""
Submission script for the Resilient AI Workflow Engine.
This script allows users to submit new documents to the workflow engine.
"""

import sys
import argparse
from engine import submit_document

def main():
    parser = argparse.ArgumentParser(description="Submit a document to the AI Workflow Engine")
    parser.add_argument("--content", type=str, help="Document content as a string")
    parser.add_argument("--file", type=str, help="Path to a file containing the document content")
    
    args = parser.parse_args()
    
    # Get the document content
    if args.content:
        content = args.content
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File {args.file} not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file {args.file}: {e}")
            sys.exit(1)
    else:
        print("Error: Either --content or --file must be provided")
        sys.exit(1)
    
    # Submit the document
    document_id = submit_document(content)
    print(f"Document submitted successfully with ID: {document_id}")
    print("To process this document, run the engine with: python engine.py")

if __name__ == "__main__":
    main()