#!/usr/bin/env bash
set -euo pipefail

BOOKS_PATH="$HOME/Books"
TARGET_DIR="data/books"

# Only link programming-related PDFs
for book in "${BOOKS_PATH}"/*.pdf; do
  filename=$(basename "$book")
  case $filename in
    *"Clojure"*|*"Python"*|*"Functional"*|*"Programming"*)
      ln -sf "$book" "$TARGET_DIR/$filename"
      echo "Linked: $filename"
      ;;
  esac
done
