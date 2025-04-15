# -*- coding: utf-8 -*-
"""
report.py: Generates the final JSON report from analysis results.
"""

import os
import traceback
from typing import Dict, Any, List, Union
from collections import defaultdict
from .analyzer import CodeAnalyzer
from .models import AnalysisStats

# --- Helper Functions ---

def _sort_variable_lists(scope_dict: Dict[str, Any]) -> None:
    """Recursively sorts variable lists within a scope dictionary by line, then name."""
    sort_key = lambda x: (x.get('line', 0), str(x.get('name', '')))

    # Sort simple lists of variables/imports
    for key in ["constants", "global_vars", "class_vars", "instance_vars", "local_vars", "imports"]:
        if key in scope_dict and isinstance(scope_dict[key], list):
            try: # Add error handling for unexpected item types during sort
                scope_dict[key] = sorted(scope_dict[key], key=sort_key)
            except TypeError:
                 # Handle or log cases where items might not have 'line' or 'name'
                 pass # Or log a warning

    # Sort from_imports values (which are lists)
    if "from_imports" in scope_dict and isinstance(scope_dict["from_imports"], dict):
         for mod, imports in scope_dict["from_imports"].items():
             if isinstance(imports, list):
                  try:
                      scope_dict["from_imports"][mod] = sorted(imports, key=sort_key)
                  except TypeError:
                      pass # Or log

    # Recurse into nested scopes (functions, classes, methods)
    for key in ["functions", "methods", "nested_functions", "classes", "nested_classes"]:
        if key in scope_dict and isinstance(scope_dict[key], dict):
            # Also sort the dictionary keys (names of functions/classes) for consistency
            sorted_items = sorted(scope_dict[key].items())
            scope_dict[key] = {} # Clear and re-insert sorted
            for name, details in sorted_items:
                if isinstance(details, dict):
                    _sort_variable_lists(details) # Recurse into the nested scope's details
                scope_dict[key][name] = details # Add back the processed (and sorted) item

def _clean_none_values(item: Any) -> Any:
    """
    Recursively removes keys with None values from dictionaries and None items from lists.
    """
    if isinstance(item, dict):
        # Create new dict, only adding keys whose values are not None after cleaning
        cleaned_dict = {}
        for k, v in item.items():
            if v is not None:
                cleaned_value = _clean_none_values(v)
                # Keep the key even if the cleaned value is an empty dict/list,
                # only omit if the original value was None.
                cleaned_dict[k] = cleaned_value
        return cleaned_dict
        # Alternate implementation: Omit key if original value was None
        # return {k: _clean_none_values(v) for k, v in item.items() if v is not None}
    elif isinstance(item, list):
        # Create new list, only adding items that are not None after cleaning
        cleaned_list = []
        for i in item:
            if i is not None:
                cleaned_item = _clean_none_values(i)
                cleaned_list.append(cleaned_item)
        return cleaned_list
        # Alternate implementation: Omit item if original was None
        # return [_clean_none_values(i) for i in item if i is not None]
    else:
        return item # Return non-dict/list items as is


# --- Main Report Generation ---

def generate_json_report(analyzer: CodeAnalyzer, filepath: str) -> Dict[str, Any]:
    """
    Generates a dictionary suitable for JSON serialization from the analyzer results,
    excluding keys with None values.

    Args:
        analyzer: The completed CodeAnalyzer instance.
        filepath: The path to the analyzed file (used for metadata).

    Returns:
        A dictionary containing the structured analysis report, cleaned of None values.
    """
    # Start with the absolute filepath and any analysis error
    report: Dict[str, Any] = {
        "filepath": os.path.abspath(filepath) if filepath else None,
        "analysis_error": analyzer.syntax_error, # Use the dedicated error attribute
    }

    # If a syntax error occurred early, return minimal info (cleaned)
    if analyzer.syntax_error:
        return _clean_none_values(report)

    # Merge the collected stats, overwriting analysis_error if it was None in stats
    # Ensure we don't accidentally overwrite a real error with None from stats
    stats_copy = analyzer.stats.copy()
    if "analysis_error" in stats_copy and stats_copy["analysis_error"] is None and report["analysis_error"] is not None:
        del stats_copy["analysis_error"] # Don't overwrite a real error
    report.update(stats_copy)

    try:
        # Convert defaultdict for from_imports to regular dict for JSON
        if "from_imports" in report and isinstance(report["from_imports"], defaultdict):
             report["from_imports"] = dict(report["from_imports"])

        # Sort variable lists and nested structures recursively
        _sort_variable_lists(report)

    except Exception as e:
         # Catch errors during the report finalization/sorting phase
         err_trace = traceback.format_exc()
         report["analysis_error"] = (f"Error during report generation: "
                                     f"{type(e).__name__}: {e}\nTraceback:\n{err_trace}")
         # Return the report with the error, but still attempt cleaning
         return _clean_none_values(report)

    # Clean None values recursively before returning
    cleaned_report = _clean_none_values(report)

    return cleaned_report