# -*- coding: utf-8 -*-
"""
cli.py: Command-line interface for the Python code analyzer.
"""

import argparse
import json
import os
import sys
from typing import Dict, Any, Optional

# Attempt import for clipboard functionality
try:
    import pyperclip
    HAS_PYPERCLIP: bool = True
except ImportError:
    HAS_PYPERCLIP = False

# Import necessary functions from other modules in the package
from .file_handler import analyze_py_file
from .report import generate_json_report
# CodeAnalyzer might not be needed directly if file_handler returns it
# from .analyzer import CodeAnalyzer


def main() -> None:
    """Handles command-line arguments, runs analysis, and outputs JSON."""
    parser = argparse.ArgumentParser(
        description="Analyze the structure of a Python file and output results as JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Example Usage:
  python -m pyanalyzer my_module.py
  python -m pyanalyzer path/to/your_script.py -o report.json
  python -m pyanalyzer script.py --copy --no-pretty

Outputs a JSON object detailing the file's structure."""
    )
    parser.add_argument("filepath", help="Path to the Python file (.py) to analyze.")
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Optional path to write the JSON output file. If omitted, prints to stdout."
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help=f"Copy the generated JSON report to the clipboard {'(requires pyperclip)' if not HAS_PYPERCLIP else ''}.",
    )
    parser.add_argument(
        "--pretty",
        action=argparse.BooleanOptionalAction, # Allows --pretty / --no-pretty
        default=True,
        help="Output formatted (pretty-printed) JSON [default: True]. Use --no-pretty for compact output.",
    )

    args = parser.parse_args()
    filepath = args.filepath
    output_path = args.output
    copy_to_clipboard = args.copy
    pretty_print = args.pretty

    # --- Analysis ---
    analyzer = analyze_py_file(filepath)

    # --- Report Generation ---
    report_data = generate_json_report(analyzer, filepath)

    # --- JSON Output ---
    json_indent = 2 if pretty_print else None
    json_output: Optional[str] = None
    try:
        # Ensure non-ASCII characters are preserved, sort top-level keys for consistency
        json_output = json.dumps(report_data, indent=json_indent, ensure_ascii=False, sort_keys=True)
    except TypeError as e:
        error_msg = f"Fatal Error: Could not serialize analysis results to JSON: {e}"
        print(error_msg, file=sys.stderr)
        # Output minimal error JSON directly
        minimal_error = json.dumps({
            "filepath": os.path.abspath(filepath) if filepath else None,
            "analysis_error": report_data.get("analysis_error") or error_msg
            }, indent=2, ensure_ascii=False, sort_keys=True)
        print(minimal_error, file=sys.stderr)
        sys.exit(1) # Exit with error code if serialization fails

    # --- Write/Print Output ---
    output_written = False
    if output_path:
        try:
            # Ensure directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir: # Only create if path includes a directory part
                os.makedirs(output_dir, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Analysis report written to '{os.path.abspath(output_path)}'")
            output_written = True
        except IOError as e:
            print(f"Error: Could not write to output file '{output_path}': {e}", file=sys.stderr)
            # Fallback to stdout if file write failed
            print("\n--- JSON Report (Fallback to stdout) ---", file=sys.stderr)
            print(json_output)
            print("--- End JSON Report ---", file=sys.stderr)
            output_written = True # Still consider it "output"
    else:
        # Print JSON to standard output
        print(json_output)
        output_written = True

    # --- Clipboard Handling ---
    if copy_to_clipboard:
        if not HAS_PYPERCLIP:
            print("\nWarning: --copy specified, but 'pyperclip' library not found/imported.", file=sys.stderr)
            print("         Install it to enable clipboard functionality: pip install pyperclip", file=sys.stderr)
        elif not json_output:
             print("\nWarning: Cannot copy to clipboard because JSON generation failed.", file=sys.stderr)
        else:
            try:
                pyperclip.copy(json_output)
                # Print confirmation to stderr to avoid mixing with stdout JSON
                if not output_path: # Add newline if printing to stdout to separate confirmation
                     print(file=sys.stderr) # Separate from JSON output on stdout
                print("JSON report copied to clipboard.", file=sys.stderr)
            except Exception as e:
                # Catch potential pyperclip errors (e.g., no display environment)
                print(f"\nWarning: Could not copy report to clipboard: {type(e).__name__}: {e}", file=sys.stderr)

    # --- Exit Code ---
    # Exit with 1 if there was an analysis error reported, 0 otherwise.
    exit_code = 1 if report_data.get("analysis_error") else 0
    sys.exit(exit_code)

# Note: The if __name__ == "__main__": block is removed here
# because the entry point will be handled by __main__.py