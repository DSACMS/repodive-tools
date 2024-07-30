#!/bin/bash

# Directory containing the text files
TEXT_DIR=$(readlink -f ./shortlog_reports)

# Temporary file to hold concatenated content
TEMP_FILE=$(mktemp)

# Ensure the directory exists
if [ ! -d "$TEXT_DIR" ]; then
    echo "Directory not found: $TEXT_DIR"
    exit 1
fi

# Concatenate all text files in the directory
for FILE in "$TEXT_DIR"/*.txt; do
    if [ -f "$FILE" ]; then
        cat "$FILE" >> "$TEMP_FILE"
    fi
done

# Use awk to process the concatenated content
awk -F'\t' '
{
    key = $2
    sum[key] += $1
}
END {
    for (k in sum) {
        print sum[k] "\t" k
    }
}
' "$TEMP_FILE" > merged_output.txt

# Print a message indicating where the output was saved
echo "Merged output saved to merged_output.txt"

cat merged_output.txt | sort --reverse -n > shortlog-breakdown.txt

# Clean up the temporary file
rm "$TEMP_FILE"
