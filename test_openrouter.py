#!/usr/bin/env python3
"""
Test script to verify OpenRouter integration.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

def test_openrouter():
    """Test the OpenRouter integration."""
    # Get the API key and model from environment variables
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
    
    print(f"OPENROUTER_API_KEY: {openrouter_api_key}")
    print(f"OPENROUTER_MODEL: {openrouter_model}")
    
    if not openrouter_api_key:
        print("Error: OPENROUTER_API_KEY not found in environment variables")
        return False
    
    if openrouter_api_key == "your_openrouter_api_key_here":
        print("Error: Please update the OPENROUTER_API_KEY in the .env file")
        return False
    
    try:
        # Initialize the LLM with OpenRouter
        llm = ChatOpenAI(
            model=openrouter_model,
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0
        )
        
        # Test the LLM with a simple prompt
        response = llm.invoke("Say hello world")
        print(f"OpenRouter test successful!")
        print(f"Model: {openrouter_model}")
        print(f"Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"Error testing OpenRouter integration: {e}")
        return False

if __name__ == "__main__":
    test_openrouter()