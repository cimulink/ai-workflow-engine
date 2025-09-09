#!/usr/bin/env python3
"""
Setup validation script to ensure all components work correctly.
"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are available"""
    print("Checking dependencies...")
    
    required_packages = [
        ('langgraph', 'LangGraph'),
        ('langchain', 'LangChain'),  
        ('langchain_openai', 'LangChain OpenAI'),
        ('streamlit', 'Streamlit'),
        ('sqlite3', 'SQLite3'),
        ('requests', 'Requests'),
        ('dotenv', 'Python Dotenv')
    ]
    
    missing_packages = []
    
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"  [OK] {name}")
        except ImportError:
            print(f"  [MISSING] {name}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("All dependencies available!")
    return True

def check_files():
    """Check if all required files exist"""
    print("\nChecking project files...")
    
    required_files = [
        'engine.py',
        'submit.py', 
        'ui.py',
        'test_workflow.py',
        'requirements.txt',
        '.env.example'
    ]
    
    missing_files = []
    
    for file_name in required_files:
        if Path(file_name).exists():
            print(f"  [OK] {file_name}")
        else:
            print(f"  [MISSING] {file_name}")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"\nMissing files: {', '.join(missing_files)}")
        return False
    
    print("All project files present!")
    return True

def check_imports():
    """Test importing core modules"""
    print("\nTesting module imports...")
    
    try:
        from engine import WorkflowState, DocumentProcessor, create_workflow
        print("  [OK] Engine components")
    except Exception as e:
        print(f"  [ERROR] Engine components: {e}")
        return False
    
    try:
        import submit
        print("  [OK] Submit module")
    except Exception as e:
        print(f"  [ERROR] Submit module: {e}")
        return False
    
    print("All modules import successfully!")
    return True

def check_environment():
    """Check environment configuration"""
    print("\nChecking environment...")
    
    # Check if .env exists
    if Path('.env').exists():
        print("  [OK] .env file found")
        
        # Load and check for API key
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            if os.getenv('OPENROUTER_API_KEY'):
                print("  [OK] OPENROUTER_API_KEY configured")
                model = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat-v3.1:free')
                print(f"  [OK] Using model: {model}")
                return True
            else:
                print("  [WARNING] OPENROUTER_API_KEY not set in .env")
                print("    Please add: OPENROUTER_API_KEY=your_api_key_here")
                return False
        except Exception as e:
            print(f"  [ERROR] Error loading .env: {e}")
            return False
    else:
        print("  [WARNING] .env file not found")
        print("    Copy .env.example to .env and configure your API key")
        return False

def test_basic_workflow():
    """Test basic workflow creation without API calls"""
    print("\nTesting basic workflow setup...")
    
    try:
        from engine import create_workflow, setup_database
        
        # Test workflow creation
        workflow = create_workflow()
        print("  [OK] Workflow graph created")
        
        # Test database setup  
        checkpointer = setup_database()
        print("  [OK] Database checkpointer initialized")
        
        # Test compilation
        app = workflow.compile(checkpointer=checkpointer)
        print("  [OK] Workflow compiled successfully")
        
        print("Basic workflow setup working!")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Workflow setup error: {e}")
        return False

def main():
    """Run all validation checks"""
    print("=" * 60)
    print("AI Workflow Engine - Setup Validation")
    print("=" * 60)
    
    checks = [
        check_dependencies(),
        check_files(), 
        check_imports(),
        check_environment(),
        test_basic_workflow()
    ]
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(checks)
    total = len(checks)
    
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] All checks passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Run: python submit.py --sample")
        print("2. Run: streamlit run ui.py") 
        print("3. Run: python test_workflow.py")
    else:
        print(f"\n[WARNING] {total - passed} check(s) failed. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())