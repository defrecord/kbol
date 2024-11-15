#!/usr/bin/env bash
set -euo pipefail

echo "Loading programming books..."
poetry run python -m kbol load-books

echo "Testing the knowledge base..."
echo "Query: What are the key concepts in functional programming from the Clojure books?"
poetry run python -m kbol query "What are the key concepts in functional programming from the Clojure books?"
