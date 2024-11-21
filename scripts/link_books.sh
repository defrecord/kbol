#!/usr/bin/env bash
set -euo pipefail

BOOKS_PATH="$HOME/Books"
TARGET_DIR="data/books"
mkdir -p "$TARGET_DIR"

# Define categories with descriptive arrays
declare -a LANGUAGES=(
    "*Clojure*" "*Python*" "*Scala*" "*Elixir*" "*Julia*" 
    "*JavaScript*" "*TypeScript*" "*Ruby*" "*Kotlin*" "*Go*"
    "*Node*" "*Dart*" "*WebAssembly*" "*elixir*" "*erlang*"
    "*DSL*" "*Domain*" "*Language*"
)

declare -a ARCHITECTURE=(
    "*Architecture*" "*Microservice*" "*Domain-Driven*" "*System*"
    "*API*" "*Design*" "*Pattern*" "*Flow*" "*Evolution*"
    "*Service*" "*Scale*" "*Scalable*" "*Distributed*"
    "*Infrastructure*" "*Platform*" "*Cloud*"
)

declare -a COMPUTER_SCIENCE=(
    "*Algorithm*" "*Data_Structure*" "*Computer_Science*"
    "*Type-Driven*" "*Functional*" "*Programming*" "*DSL*"
    "*Quantum*" "*Crypto*" "*Math*" "*Geometry*"
    "*Computation*" "*Logic*" "*Theory*" "*Graph*"
    "*Classic*Computer*" "*Grokking*"
)

declare -a AI_ML=(
    "*Learning*" "*AI*" "*Deep*" "*Neural*" "*MLOps*"
    "*Bayesian*" "*Quantum*" "*Data*" "*Analysis*"
    "*Statistics*" "*Optimization*" "*Model*" "*Machine*"
    "*Artificial*" "*Intelligence*" "*Pattern*Recognition*"
)

declare -a INFRASTRUCTURE=(
    "*Kubernetes*" "*GraphQL*" "*Infrastructure*" "*DevOps*"
    "*Cloud*" "*Observability*" "*Platform*" "*Container*"
    "*Operation*" "*Deployment*" "*Service*" "*Orchestrat*"
    "*Docker*" "*Terraform*" "*Pipeline*"
)

declare -a DEVELOPMENT=(
    "*Test*" "*test*" "*Debug*" "*Performance*" "*Security*"
    "*Practice*" "*Professional*" "*Refactor*" "*Clean*"
    "*Engineering*" "*Developer*" "*Software*" "*software*" "*Code*"
    "*Programming*" "*programming*" "*Implementation*"
)

declare -a PHILOSOPHY=(
    "*mit*"  # MIT Press Essential Knowledge series
)

declare -a DATA=(
    "*Data*" "*Analytics*" "*Database*" "*SQL*" "*NoSQL*"
    "*Graph*" "*Stream*" "*Pipeline*" "*ETL*" "*Analysis*"
    "*Mining*" "*Warehouse*" "*Lake*" "*Intelligence*"
)

get_filesize() {
    local file="$1"
    wc -c < "$file"
}

format_size() {
    local size="$1"
    local scale=1024
    local units=("B" "KiB" "MiB" "GiB")
    local unit=0
    
    while ((size > scale && unit < ${#units[@]} - 1)); do
        size=$((size / scale))
        unit=$((unit + 1))
    done
    
    echo "${size}${units[$unit]}"
}

link_if_matches() {
    local book="$1"
    local filename=$(basename "$book")
    local matched=0
    local filesize
    
    # Skip known non-technical PDFs
    if [[ "$filename" =~ ^[0-9]{9,} ]]; then
        return
    fi
    
    # Get file size
    filesize=$(get_filesize "$book")
    
    # Skip if file is too small
    if [ "$filesize" -lt 100000 ]; then  # Skip files smaller than 100KB
        echo "[SKIPPED: TOO SMALL] $filename ($(format_size $filesize))"
        return
    fi
    
    # Try to match against patterns
    for pattern in "${LANGUAGES[@]}" "${ARCHITECTURE[@]}" "${COMPUTER_SCIENCE[@]}" \
                  "${AI_ML[@]}" "${INFRASTRUCTURE[@]}" "${DEVELOPMENT[@]}" \
                  "${PHILOSOPHY[@]}" "${DATA[@]}"; do
        if [[ "$filename" == ${pattern} ]]; then
            if [ -L "$TARGET_DIR/$filename" ]; then
                rm "$TARGET_DIR/$filename"
            fi
            ln -sf "$book" "$TARGET_DIR/$filename"
            echo "[LINKED] $filename ($(format_size $filesize))"
            matched=1
            break
        fi
    done
    
    if [[ $matched -eq 0 ]]; then
        echo "[SKIPPED] $filename ($(format_size $filesize))"
    fi
}

echo "Linking books to $TARGET_DIR..."
echo "================================"

# First, clean up any broken symlinks
find "$TARGET_DIR" -type l ! -exec test -e {} \; -delete

# Process all PDF files
for book in "$BOOKS_PATH"/*.pdf; do
    link_if_matches "$book"
done

echo "================================"
echo "Verifying links..."
poetry run python scripts/verify_paths.py

echo "Done!"
