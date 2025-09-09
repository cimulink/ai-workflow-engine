#!/usr/bin/env python3
"""
Test the debug functionality
"""

import os
from debug_submit import debug_submit_document

def test_debug_levels():
    """Test different debug levels"""
    
    # Test document that should require review
    test_content = "INVOICE #TEST from Debug Corp for $2,500 testing services"
    
    print("Testing different debug levels:\n")
    
    # Test BASIC level
    print("1. Testing BASIC debug level:")
    print("-" * 40)
    debug_submit_document(test_content, "debug_basic", "BASIC")
    
    print("\n\n2. Testing DETAILED debug level:")
    print("-" * 40) 
    debug_submit_document(test_content, "debug_detailed", "DETAILED")
    
    print("\n\n3. Testing VERBOSE debug level:")
    print("-" * 40)
    debug_submit_document(test_content, "debug_verbose", "VERBOSE")

if __name__ == "__main__":
    test_debug_levels()