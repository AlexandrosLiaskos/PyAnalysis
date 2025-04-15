# -*- coding: utf-8 -*-
"""
file_handler.py: Handles reading, parsing, and initiating analysis of Python files.
"""

import ast
import os
import traceback
from typing import Optional

from .analyzer import CodeAnalyzer

def analyze_py_file(filepath: str) -> CodeAnalyzer:
    """
    Reads, parses, and analyzes a Python file using CodeAnalyzer.

    Handles file existence, extension checks, and catches parsing/analysis errors.

    Args:
        filepath: The path to the Python file.

    Returns:
        A CodeAnalyzer instance containing the analysis results or error information.
    """
    analyzer = CodeAnalyzer()

    if not os.path.exists(filepath):
        analyzer.syntax_error = f"Error: File not found at '{filepath}'"
        # Update stats dictionary as well for consistency in reporting
        analyzer.stats["analysis_error"] = analyzer.syntax_error
        return analyzer
    if not os.path.isfile(filepath):
         analyzer.syntax_error = f"Error: Input path '{filepath}' is a directory, not a file."
         analyzer.stats["analysis_error"] = analyzer.syntax_error
         return analyzer
    if not filepath.lower().endswith(".py"):
        analyzer.syntax_error = f"Error: Input path '{filepath}' does not appear to be a Python file (.py extension)."
        analyzer.stats["analysis_error"] = analyzer.syntax_error
        return analyzer

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f: # Ignore decoding errors for robustness
            source_code = f.read()
        tree = ast.parse(source_code, filename=filepath)
        analyzer.visit(tree)
    except SyntaxError as e:
        error_detail = (
            f"Syntax Error: Invalid Python syntax in '{filepath}' near line {e.lineno} column {e.offset}:\n"
            f"  Detail: {e.msg}\n"
            f"  Context: {e.text.strip() if e.text else '<source line unavailable>'}"
        )
        analyzer.syntax_error = error_detail
        analyzer.stats["analysis_error"] = error_detail # Store error in stats too
    except Exception as e:
        err_trace = traceback.format_exc()
        error_detail = (f"Unexpected Analysis Error: Failed processing '{filepath}'.\n"
                         f"  Error: {type(e).__name__}: {e}\nTraceback:\n{err_trace}")
        analyzer.syntax_error = error_detail
        analyzer.stats["analysis_error"] = error_detail

    return analyzer