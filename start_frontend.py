#!/usr/bin/env python3
"""
Startup script for AG-UI frontend
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🎨 Starting AI Workflow Engine - AG-UI Frontend")
    print("=" * 60)
    
    # Check if frontend directory exists
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("📦 Installing frontend dependencies...")
        os.chdir("frontend")
        try:
            subprocess.run(["npm", "install"], check=True)
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies. Make sure npm is installed.")
            return
        except FileNotFoundError:
            print("❌ npm not found. Please install Node.js and npm first.")
            return
    else:
        os.chdir("frontend")
    
    print("🌐 Starting frontend development server on http://localhost:3000")
    print("🔄 Server will auto-reload on code changes")
    print("🔌 Will proxy API requests to backend at http://localhost:8000")
    print("")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Start the development server
        subprocess.run(["npm", "run", "dev"])
    except KeyboardInterrupt:
        print("\n👋 Frontend server stopped by user")
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")

if __name__ == "__main__":
    main()