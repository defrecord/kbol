#!/bin/bash
set -euo pipefail

# Test with a single PDF
echo "Testing with first PDF..."
python -m kbol data/books/*.pdf | head -n 5
