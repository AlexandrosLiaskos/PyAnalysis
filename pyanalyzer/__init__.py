# -*- coding: utf-8 -*-
"""
PyAnalyzer: A Python code structure analysis tool.

This package provides tools to analyze Python source code using Abstract Syntax Trees (AST)
and generate structured reports (e.g., JSON) detailing imports, functions, classes,
variables, and more.
"""

# Expose key components for potential library usage
from .models import ParameterKind, VarInfoDict, ImportInfoDict, ParamInfoDict
from .analyzer import CodeAnalyzer
from .file_handler import analyze_py_file
from .report import generate_json_report

# Define __all__ for explicit public API if desired
__all__ = [
    "CodeAnalyzer",
    "analyze_py_file",
    "generate_json_report",
    "ParameterKind",
    "VarInfoDict",
    "ImportInfoDict",
    "ParamInfoDict",
]

__version__ = "1.0.0" # Example version