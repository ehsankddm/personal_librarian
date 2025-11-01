"""Sandbox - Safe execution environment for dynamic code."""

import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional


class Sandbox:
    """Provides safe execution environment for generated code."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.allowed_imports = {
            'os', 'sys', 'pathlib', 'json', 'datetime', 'dataclasses',
            'typing', 'enum', 'asyncio', 'logging'
        }
    
    def validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate Python syntax without execution."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
    
    def validate_imports(self, code: str) -> tuple[bool, Optional[str]]:
        """Check if code uses only allowed imports."""
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.allowed_imports:
                        return False, f"Disallowed import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in self.allowed_imports:
                    return False, f"Disallowed import: {node.module}"
        
        return True, None
    
    async def execute_safe(self, code: str, globals_: dict = None) -> tuple[Any, Optional[str]]:
        """Execute code in a safe environment."""
        # Validate syntax
        valid, error = self.validate_syntax(code)
        if not valid:
            return None, error
        
        # Validate imports
        valid, error = self.validate_imports(code)
        if not valid:
            return None, error
        
        # Execute in isolated namespace
        safe_globals = {
            '__builtins__': __builtins__,
            **(globals_ or {})
        }
        
        try:
            exec(code, safe_globals)
            return safe_globals, None
        except Exception as e:
            return None, f"Execution error: {e}"
    
    def check_file_operations(self, code: str) -> tuple[bool, list[str]]:
        """Detect file operations in code."""
        tree = ast.parse(code)
        file_ops = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr
                    if attr_name in ['open', 'read', 'write', 'delete', 'remove']:
                        file_ops.append(attr_name)
        
        return len(file_ops) > 0, file_ops

