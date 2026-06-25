#!/bin/bash
# Wrapper для запуска evaluation tools с venv

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

# Activate venv
source "$VENV_DIR/bin/activate"

# Run command
"$@"
