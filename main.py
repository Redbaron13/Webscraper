#!/usr/bin/env python3
import sys
import os

# Add the current directory (root of the project) to the Python path
# This ensures that the 'modules' package can be found.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from modules.main import cli

if __name__ == '__main__':
    cli()
