Okay, here is a `README.md` file for your `PyAnalysis` project, based on the provided code structure and functionality.

```markdown
# PyAnalysis: Python Code Structure Analyzer

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your_username/pyanalysis) 
[![PyPI version](https://img.shields.io/pypi/v/pyanalysis)](https://pypi.org/project/pyanalysis/) 
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

PyAnalysis is a command-line tool and library designed to analyze the structure of Python source code files. It leverages Python's built-in Abstract Syntax Trees (AST) module to parse the code and extracts detailed information about its components. The results are presented in a clean, structured JSON format.

This tool is useful for:

*   Understanding the layout and components of unfamiliar Python modules.
*   Generating code documentation inputs.
*   Programmatic analysis of Python codebases.
*   Educational purposes for learning about ASTs and code structure.

## Features

*   **AST-Based Analysis:** Parses Python code using the `ast` module for accurate structural representation.
*   **Comprehensive Extraction:** Identifies and extracts information about:
    *   Module-level docstrings.
    *   Imports (`import x`, `import x as y`).
    *   From-imports (`from x import y`, `from x import y as z`).
    *   Global constants (following `SCREAMING_SNAKE_CASE` convention).
    *   Global variables.
    *   Functions (top-level and nested):
        *   Parameters (name, type hint, default value, kind - positional-only, keyword-only, varargs, etc.).
        *   Return type hints.
        *   Decorators.
        *   Docstrings.
        *   Local variables declared within the function.
    *   Classes (top-level and nested):
        *   Base classes (inheritance).
        *   Decorators.
        *   Methods (instance methods, class methods, static methods, properties).
        *   Class variables.
        *   Instance variables (identified via `self.x` assignments).
        *   Docstrings.
    *   Detection of `if __name__ == "__main__":` blocks.
*   **JSON Output:** Provides results in a structured JSON format, suitable for machine reading or easy human inspection.
*   **CLI Interface:** Easy-to-use command-line tool.
*   **Output Options:**
    *   Print JSON to standard output.
    *   Write JSON to a specified file.
    *   Control JSON formatting (pretty-printed or compact).
    *   Optionally copy the JSON output to the clipboard (requires `pyperclip`).
*   **Error Handling:** Gracefully handles file not found errors, syntax errors during parsing, and internal analysis errors, reporting them within the JSON output.
*   **Library Usage:** Core components can be imported and used programmatically.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your_username/pyanalysis.git # Replace with actual URL
    cd pyanalysis
    ```

2.  **Install the package:**
    Using pip, you can install the package locally. This makes the `python -m pyanalyzer` command available in your environment.
    ```bash
    pip install .
    ```
    *   Alternatively, for development: `pip install -e .`

3.  **Optional Dependencies:**
    To use the `--copy` feature, you need to install `pyperclip`:
    ```bash
    pip install pyperclip
    ```

## Usage

### Command-Line Interface (CLI)

The primary way to use PyAnalysis is via the command line.

```bash
python -m pyanalyzer <filepath> [options]
```

**Arguments:**

*   `filepath`: Path to the Python file (`.py`) to analyze.

**Options:**

*   `-o FILE`, `--output FILE`: Path to write the JSON output file. If omitted, prints to stdout.
*   `--copy`: Copy the generated JSON report to the clipboard (requires `pyperclip`).
*   `--pretty` / `--no-pretty`: Output formatted (pretty-printed) JSON (default) or compact JSON (`--no-pretty`).

**Examples:**

```bash
# Analyze a file and print pretty JSON to stdout
python -m pyanalyzer path/to/your_script.py

# Analyze a file and save compact JSON to report.json
python -m pyanalyzer my_module.py -o report.json --no-pretty

# Analyze a file, print pretty JSON to stdout, and copy it to the clipboard
python -m pyanalyzer script.py --copy
```

### Library Usage

You can also use PyAnalysis programmatically within your Python scripts.

```python
import json
from pyanalyzer import analyze_py_file, generate_json_report

filepath = "path/to/your_module.py"

try:
    # 1. Analyze the file
    analyzer_instance = analyze_py_file(filepath)

    # 2. Generate the report dictionary
    # The generate_json_report function handles sorting and cleaning None values
    report_data = generate_json_report(analyzer_instance, filepath)

    # 3. Process the report (e.g., print as JSON)
    if report_data.get("analysis_error"):
        print(f"Analysis Error: {report_data['analysis_error']}", file=sys.stderr)
        # Handle error appropriately

    json_output = json.dumps(report_data, indent=2, ensure_ascii=False)
    print(json_output)

except Exception as e:
    print(f"An unexpected error occurred: {e}")

```

## Output Format

The tool outputs a JSON object containing the analysis results. Keys with `None` values are automatically removed from the output for clarity, unless it's the `analysis_error` field itself. Lists of variables, imports, etc., are sorted by line number and then by name for consistent output.

**Top-Level Keys:**

*   `filepath`: Absolute path to the analyzed file.
*   `analysis_error`: String containing an error message if file/syntax/analysis errors occurred, otherwise omitted.
*   `module_docstring`: The docstring of the module, if present.
*   `imports`: List of `import x` statements. Each item has `name`, `alias`, `line`.
*   `from_imports`: Dictionary where keys are module names (`.` prefix for relative imports) and values are lists of imported items. Each item has `name`, `alias`, `line`.
*   `constants`: List of module-level variables identified as constants (SCREAMING_SNAKE_CASE). Each item has `name`, `type` (if annotated), `line`.
*   `global_vars`: List of other module-level variables. Each item has `name`, `type` (if annotated), `line`.
*   `functions`: Dictionary of top-level functions. Keys are function names. See Function/Class Structure below.
*   `classes`: Dictionary of top-level classes. Keys are class names. See Function/Class Structure below.
*   `has_main_block`: Boolean indicating if an `if __name__ == "__main__":` block was detected.

**Function/Class Structure (Simplified):**

Items within `functions` and `classes` (and their nested counterparts like `methods`, `nested_functions`, `nested_classes`) follow a similar structure:

```json
{
  "name": "function_or_class_name",
  "line": 10,
  "docstring": "Optional docstring...",
  "decorators": ["@decorator1", ...],
  // Function-specific:
  "params": [
    {"name": "arg1", "type": "int", "default": null, "kind": "POSITIONAL_OR_KEYWORD"},
    {"name": "arg2", "type": "str", "default": "'default'", "kind": "POSITIONAL_OR_KEYWORD"},
    // ... other parameter kinds
  ],
  "return_type": "Optional[str]",
  "local_vars": [...], // Variables defined inside
  "nested_functions": {...},
  "nested_classes": {...},
  // Class-specific:
  "base_classes": ["ParentClass", ...],
  "methods": { // Includes instance, class, static methods, properties
      "my_method": { ... /* recursive structure */ }
   },
  "class_vars": [...],
  "instance_vars": [...] // Variables assigned via self.x or cls.x
}
```

**Example JSON Output (Snippet):**

```json
{
  "filepath": "/path/to/example.py",
  "module_docstring": "An example module.",
  "has_main_block": true,
  "imports": [
    {
      "name": "os",
      "alias": null,
      "line": 3
    }
  ],
  "from_imports": {
    "typing": [
      {
        "name": "List",
        "alias": null,
        "line": 4
      },
      {
        "name": "Optional",
        "alias": null,
        "line": 4
      }
    ]
  },
  "constants": [
    {
      "name": "MAX_RETRIES",
      "type": "int",
      "line": 6
    }
  ],
  "functions": {
    "process_data": {
      "name": "process_data",
      "line": 9,
      "docstring": "Processes the input data.",
      "params": [
        {
          "name": "data",
          "type": "List[str]",
          "default": null,
          "kind": "POSITIONAL_OR_KEYWORD"
        },
        {
          "name": "retries",
          "type": "int",
          "default": "MAX_RETRIES",
          "kind": "POSITIONAL_OR_KEYWORD"
        }
      ],
      "return_type": "Optional[bool]",
      "decorators": [],
      "local_vars": [
        {
          "name": "result",
          "type": null,
          "line": 11
        }
      ],
      "nested_functions": {},
      "nested_classes": {}
    }
  },
  "classes": {
     "MyClass": {
        "name": "MyClass",
        "line": 15,
        "docstring": "An example class.",
        "base_classes": [],
        "decorators": [],
        "methods": {
           "__init__": { ... },
           "get_value": { ... }
        },
        "class_vars": [
           { "name": "default_name", "type": "str", "line": 16 }
        ],
        "instance_vars": [
           { "name": "value", "type": "int", "line": 20 }
        ],
        "nested_classes": {}
     }
  }
  // analysis_error would be here if something went wrong
}
```

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue on the GitHub repository. If you'd like to contribute code:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Add tests for your changes (if applicable).
5.  Ensure tests pass and code meets quality standards.
6.  Commit your changes (`git commit -am 'Add some feature'`).
7.  Push to the branch (`git push origin feature/your-feature-name`).
8.  Open a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
```

**Before publishing:**

1.  **Replace Placeholders:** Update `your_username/pyanalysis` with the actual GitHub repository URL. Add real CI/CD badges if you set them up. Choose and add a `LICENSE` file (e.g., MIT) and ensure the badge and text reflect your choice. If you publish to PyPI, update the PyPI badge link.
2.  **Review:** Read through the generated README to ensure it accurately reflects the project's current state and is easy to understand.
3.  **Add `LICENSE` file:** Create a `LICENSE` file in the root of your project containing the text of the license you chose (e.g., MIT).