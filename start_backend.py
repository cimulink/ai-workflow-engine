#!/usr/bin/env python3
"""
Startup script for AG-UI backend server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Starting AI Workflow Engine - AG-UI Backend Server")
    print("=" * 60)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  Warning: .env file not found!")
        print("Please create .env file with your OPENROUTER_API_KEY")
        print("Example: echo 'OPENROUTER_API_KEY=your_key_here' > .env")
        return
    
    # Check if backend directory exists
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found!")
        return
    
    # Change to backend directory and start server
    os.chdir("backend")
    
    print("📡 Starting AG-UI server on http://localhost:8000")
    print("📋 API docs available at http://localhost:8000/docs")
    print("🔄 Server will auto-reload on code changes")
    print("")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Start the uvicorn server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "ag_ui_server_fixed:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()