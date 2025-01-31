#!/bin/bash
# file_contents.sh

# Function to check if file should be skipped
should_skip() {
    local file="$1"
    # Skip binary files, caches, etc
    if [[ "$file" =~ \.(pyc|pyo|pyd|so|dll|class|o|obj|exe)$ ]] || \
       [[ "$file" =~ /__pycache__/ ]] || \
       [[ "$file" =~ \.git/ ]] || \
       [[ "$file" =~ \.(jpg|png|gif|bmp|ico|svg)$ ]]; then
        return 0
    fi
    return 1
}

# Function to read file contents
read_file() {
    local file="$1"
    echo "=== File: $file ==="
    echo "Content:"
    cat "$file"
    echo -e "\n"
}

# Main function to process directory
process_directory() {
    local dir="$1"
    
    # First show directory structure
    echo "=== Directory Structure ==="
    tree "$dir"
    echo -e "\n=== File Contents ===\n"
    
    # Then process each file
    while IFS= read -r -d '' file; do
        if ! should_skip "$file"; then
            if [ -f "$file" ]; then
                read_file "$file"
            fi
        fi
    done < <(find "$dir" -type f -print0)
}

# Check if directory argument is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

# Process the directory
process_directory "$1"
