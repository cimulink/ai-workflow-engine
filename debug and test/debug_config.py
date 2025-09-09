#!/usr/bin/env python3
"""
Debug configuration for AI Workflow Engine
Provides comprehensive logging and tracing capabilities
"""

import os
import logging
import sys
from datetime import datetime
from pathlib import Path

# Debug levels
DEBUG_LEVELS = {
    'BASIC': 1,      # Basic flow information
    'DETAILED': 2,   # Detailed step-by-step logging
    'VERBOSE': 3,    # Full state dumps and API calls
    'TRACE': 4       # Maximum verbosity with timing
}

class WorkflowDebugger:
    """Enhanced debugging for workflow operations"""
    
    def __init__(self, debug_level='DETAILED', log_to_file=True):
        self.debug_level = DEBUG_LEVELS.get(debug_level.upper(), 2)
        self.start_time = datetime.now()
        
        # Setup logging
        self.setup_logging(log_to_file)
        
        # Debug flags
        self.trace_api_calls = self.debug_level >= 3
        self.trace_state_changes = self.debug_level >= 2
        self.trace_timing = self.debug_level >= 4
        self.dump_full_state = self.debug_level >= 3
        
        self.step_counter = 0
        self.api_call_counter = 0
    
    def setup_logging(self, log_to_file):
        """Configure logging with both console and file output"""
        # Create logs directory
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger('workflow_debug')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '[DEBUG] %(levelname)s [%(asctime)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler if requested
        if log_to_file:
            log_file = log_dir / f"workflow_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(levelname)s [%(asctime)s] %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
            
            print(f"[DEBUG] Debug logging to: {log_file}")
    
    def log_step(self, step_name, details=None, level='INFO'):
        """Log a workflow step"""
        self.step_counter += 1
        
        if self.debug_level >= 1:
            msg = f"STEP {self.step_counter}: {step_name}"
            if details and self.debug_level >= 2:
                msg += f" | {details}"
            
            if level == 'INFO':
                self.logger.info(msg)
            elif level == 'WARNING':
                self.logger.warning(msg)
            elif level == 'ERROR':
                self.logger.error(msg)
            else:
                self.logger.debug(msg)
    
    def log_state_change(self, from_state, to_state, reason=None):
        """Log state transitions"""
        if self.trace_state_changes:
            msg = f"STATE: {from_state} → {to_state}"
            if reason:
                msg += f" ({reason})"
            self.logger.info(msg)
    
    def log_api_call(self, service, method, request_data=None, response_data=None):
        """Log external API calls"""
        if self.trace_api_calls:
            self.api_call_counter += 1
            self.logger.info(f"API CALL {self.api_call_counter}: {service}.{method}")
            
            if request_data and self.debug_level >= 4:
                self.logger.debug(f"Request: {request_data}")
            
            if response_data and self.debug_level >= 4:
                self.logger.debug(f"Response: {response_data}")
    
    def log_validation_result(self, document_id, rules_checked, results):
        """Log validation rule results"""
        if self.debug_level >= 2:
            self.logger.info(f"VALIDATION for {document_id}:")
            for rule, result in zip(rules_checked, results):
                status = "✅ PASS" if result else "❌ FAIL"
                self.logger.info(f"  {rule}: {status}")
    
    def dump_state(self, state, label="Current State"):
        """Dump full workflow state"""
        if self.dump_full_state:
            self.logger.debug(f"=== {label} ===")
            if isinstance(state, dict):
                for key, value in state.items():
                    if key == 'content' and len(str(value)) > 100:
                        # Truncate long content
                        self.logger.debug(f"  {key}: {str(value)[:100]}...")
                    else:
                        self.logger.debug(f"  {key}: {value}")
            else:
                self.logger.debug(f"  {state}")
            self.logger.debug("=" * 50)
    
    def log_timing(self, operation, start_time, end_time=None):
        """Log operation timing"""
        if self.trace_timing:
            if end_time is None:
                end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            self.logger.info(f"[TIMING] {operation}: {duration:.2f}s")
    
    def log_error(self, error, context=None):
        """Log errors with context"""
        msg = f"ERROR: {str(error)}"
        if context:
            msg += f" | Context: {context}"
        self.logger.error(msg)
        
        # Log stack trace for verbose debugging
        if self.debug_level >= 3:
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def summary(self):
        """Print debug session summary"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(f"DEBUG SUMMARY:")
        self.logger.info(f"  Total Steps: {self.step_counter}")
        self.logger.info(f"  API Calls: {self.api_call_counter}")
        self.logger.info(f"  Total Time: {total_time:.2f}s")
        self.logger.info(f"  Debug Level: {self.debug_level}")

# Global debugger instance
_debugger = None

def get_debugger():
    """Get the global debugger instance"""
    global _debugger
    if _debugger is None:
        # Check environment variable for debug level
        debug_level = os.getenv('WORKFLOW_DEBUG_LEVEL', 'DETAILED')
        log_to_file = os.getenv('WORKFLOW_DEBUG_LOG', 'true').lower() == 'true'
        _debugger = WorkflowDebugger(debug_level, log_to_file)
    return _debugger

def set_debug_level(level):
    """Set debug level: BASIC, DETAILED, VERBOSE, TRACE"""
    global _debugger
    _debugger = WorkflowDebugger(level, True)
    return _debugger

# Convenience functions
def debug_step(step_name, details=None, level='INFO'):
    get_debugger().log_step(step_name, details, level)

def debug_state_change(from_state, to_state, reason=None):
    get_debugger().log_state_change(from_state, to_state, reason)

def debug_api_call(service, method, request_data=None, response_data=None):
    get_debugger().log_api_call(service, method, request_data, response_data)

def debug_validation(document_id, rules_checked, results):
    get_debugger().log_validation_result(document_id, rules_checked, results)

def debug_dump_state(state, label="Current State"):
    get_debugger().dump_state(state, label)

def debug_timing(operation, start_time, end_time=None):
    get_debugger().log_timing(operation, start_time, end_time)

def debug_error(error, context=None):
    get_debugger().log_error(error, context)

def debug_summary():
    get_debugger().summary()

if __name__ == "__main__":
    # Test the debugger
    debugger = WorkflowDebugger('VERBOSE')
    debugger.log_step("Test Step", "Testing debug system")
    debugger.log_state_change("received", "processing", "Starting workflow")
    debugger.log_api_call("OpenRouter", "chat_completion", {"model": "deepseek"}, {"response": "success"})
    debugger.summary()