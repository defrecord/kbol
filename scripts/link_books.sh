#!/usr/bin/env bash
set -euo pipefail

BOOKS_PATH="$HOME/Books"
TARGET_DIR="data/books"
mkdir -p "$TARGET_DIR"

# Define categories with descriptive arrays
declare -a LANGUAGES=(
    "*Clojure*" "*Python*" "*Scala*" "*Elixir*" "*Julia*" 
    "*JavaScript*" "*TypeScript*" "*Ruby*" "*Kotlin*" "*Go*"
)

declare -a ARCHITECTURE=(
    "*Architecture*" "*Microservice*" "*Domain-Driven*" "*System*"
    "*API*" "*Design*" "*Pattern*" "*Flow*" "*Evolution*"
)

declare -a COMPUTER_SCIENCE=(
    "*Algorithm*" "*Data_Structure*" "*Computer_Science*"
    "*Type-Driven*" "*Functional*" "*Programming*" "*DSL*"
)

declare -a AI_ML=(
    "*Learning*" "*AI*" "*Deep*" "*Neural*" "*MLOps*"
    "*Bayesian*" "*Quantum*"
)

declare -a PHILOSOPHY=(
    "*mit*"  # MIT Press Essential Knowledge series
)

link_if_matches() {
    local book="$1"
    local filename=$(basename "$book")
    local matched=0
    
    # Skip known non-technical PDFs
    if [[ "$filename" =~ ^[0-9]{9,} ]]; then
        return
    fi
    
    for pattern in "${LANGUAGES[@]}" "${ARCHITECTURE[@]}" "${COMPUTER_SCIENCE[@]}" "${AI_ML[@]}" "${PHILOSOPHY[@]}"; do
        if [[ "$filename" == ${pattern} ]]; then
            ln -sf "$book" "$TARGET_DIR/$filename"
            echo "[LINKED] $filename"
            matched=1
            break
        fi
    done
    
    if [[ $matched -eq 0 ]]; then
        echo "[SKIPPED] $filename"
    fi
}

echo "Linking books to $TARGET_DIR..."
echo "================================"

for book in "$BOOKS_PATH"/*.pdf; do
    link_if_matches "$book"
done

echo "================================"
echo "Done! Remember to run: poetry run python -m kbol process"
