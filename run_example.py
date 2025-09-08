#!/usr/bin/env python3
"""
Example script to demonstrate the complete workflow of the Resilient AI Workflow Engine.
"""

import time
import subprocess
import sys
import os

def main():
    print("Resilient AI Workflow Engine - Example Run")
    print("=" * 50)
    
    # Step 1: Submit a document
    print("\n1. Submitting a sample document...")
    result = subprocess.run([
        sys.executable, "submit.py", 
        "--file", "sample_invoice.txt"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error submitting document: {result.stderr}")
        return
    
    print("Document submitted successfully!")
    
    # Step 2: Show database was created
    print("\n2. Checking database...")
    if os.path.exists("workflow.db"):
        print("Database created successfully!")
    else:
        print("Database not found!")
    
    print("\n3. To run the complete workflow, execute the following commands in separate terminals:")
    print("\nTerminal 1 (Workflow Engine):")
    print("  python engine.py")
    print("\nTerminal 2 (Review UI):")
    print("  streamlit run ui.py")
    print("\nTo submit more documents:")
    print("  python submit.py --file sample_invoice.txt")
    print("  python submit.py --content \"Your document content here\"")
    
    print("\nNote: The full workflow requires an OpenAI API key set in the environment variables.")

if __name__ == "__main__":
    main()