# -*- coding: utf-8 -*-
"""
models.py: Data structures and type definitions for Python code analysis.
"""

from typing import Dict, Union, List, NewType

# --- Type Definitions ---
# Using Dicts directly for variable info storage
VarInfoDict = Dict[str, Union[str, int, None]] # { "name": ..., "type": ..., "line": ... }
ImportInfoDict = Dict[str, Union[str, int, None]] # {"name": ..., "alias": ..., "line": ...}
ParamInfoDict = Dict[str, Union[str, bool, None]] # {"name": ..., "type": ..., "default": ..., "kind": ...}

# Using NewType for slightly stronger typing if desired, but Dicts are practical here.
# VarInfo = NewType("VarInfo", Dict[str, Union[str, int, None]])
# ImportInfo = NewType("ImportInfo", Dict[str, Union[str, int, None]])
# ParamInfo = NewType("ParamInfo", Dict[str, Union[str, bool, None]])

# Parameter kinds matching inspect module for clarity
class ParameterKind:
    """String constants representing parameter kinds."""
    POSITIONAL_ONLY = "POSITIONAL_ONLY"
    POSITIONAL_OR_KEYWORD = "POSITIONAL_OR_KEYWORD"
    VAR_POSITIONAL = "VAR_POSITIONAL" # *args
    KEYWORD_ONLY = "KEYWORD_ONLY"
    VAR_KEYWORD = "VAR_KEYWORD" # **kwargs

# Type alias for the main analysis statistics dictionary
AnalysisStats = Dict[str, Union[List[ImportInfoDict],
                                Dict[str, List[ImportInfoDict]],
                                List[VarInfoDict],
                                Dict[str, Dict], # Functions/Classes
                                bool,
                                None,
                                str]] # Includes analysis_error