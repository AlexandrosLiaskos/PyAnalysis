# -*- coding: utf-8 -*-
"""
__main__.py: Makes the pyanalyzer package executable.

Allows running the analyzer directly using `python -m pyanalyzer <args>`.
"""

import sys
from .cli import main

if __name__ == "__main__":
    # Check if running with '-m' which can add '-c' or script path to sys.argv
    # A simple check is often sufficient if we just want to run main()
    main()