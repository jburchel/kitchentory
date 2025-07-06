#!/bin/bash
# Get latest screenshot and copy path to clipboard

# Function to find latest screenshot
get_latest_screenshot() {
    # Check multiple common screenshot locations
    LOCATIONS=(
        "$HOME/Desktop"
        "$HOME/Downloads"
        "/tmp"
        "/var/folders"
    )
    
    LATEST_FILE=""
    LATEST_TIME=0
    
    for location in "${LOCATIONS[@]}"; do
        if [ -d "$location" ]; then
            # Find screenshot files (case insensitive)
            while IFS= read -r -d '' file; do
                if [[ -f "$file" ]]; then
                    # Get file modification time
                    if [[ "$OSTYPE" == "darwin"* ]]; then
                        FILE_TIME=$(stat -f "%m" "$file" 2>/dev/null || echo 0)
                    else
                        FILE_TIME=$(stat -c "%Y" "$file" 2>/dev/null || echo 0)
                    fi
                    
                    # Check if this is newer
                    if (( FILE_TIME > LATEST_TIME )); then
                        LATEST_TIME=$FILE_TIME
                        LATEST_FILE="$file"
                    fi
                fi
            done < <(find "$location" -maxdepth 3 -iname "*screenshot*" -o -iname "*screen shot*" -o -iname "*cleanshot*" 2>/dev/null | head -20 | tr '\n' '\0')
        fi
    done
    
    echo "$LATEST_FILE"
}

# Function to copy to clipboard
copy_to_clipboard() {
    local filepath="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "$filepath" | pbcopy
        echo "📸 Copied to clipboard: $(basename "$filepath")"
        
        # Show notification
        osascript -e "display notification \"Path copied: $(basename "$filepath")\" with title \"Claude Code Screenshot\""
    elif command -v xclip >/dev/null; then
        echo "$filepath" | xclip -selection clipboard
        echo "📸 Copied to clipboard: $(basename "$filepath")"
    else
        echo "📸 Latest screenshot: $filepath"
        echo "⚠️  Could not copy to clipboard (install pbcopy or xclip)"
    fi
}

# Main execution
main() {
    echo "🔍 Finding latest screenshot..."
    
    LATEST=$(get_latest_screenshot)
    
    if [[ -n "$LATEST" && -f "$LATEST" ]]; then
        copy_to_clipboard "$LATEST"
    else
        echo "❌ No screenshots found"
        
        # Show notification
        if [[ "$OSTYPE" == "darwin"* ]]; then
            osascript -e 'display notification "No screenshots found" with title "Claude Code Screenshot"'
        fi
    fi
}

# Run the script
main "$@"