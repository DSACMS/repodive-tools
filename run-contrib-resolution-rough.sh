#!/bin/bash

SHORTLOG_LOC=$(readlink -f ./shortlog_reports)

# Change to the base directory
cd "$1" || { echo "Directory not found: $1"; exit 1; }

# Iterate over each directory in the base directory
for REPO_DIR in */ ; do
    # Check if it's a directory
    if [ -d "$REPO_DIR" ]; then
        # Change to the repository directory
        cd "$REPO_DIR" || continue
        
        # Check if it is a git repository
        if [ -d ".git" ]; then
            # Run git shortlog and save the output
            REPO_NAME=$(basename "$REPO_DIR")
            touch $SHORTLOG_LOC/${REPO_NAME}.txt
            echo "If the log is empty it will prompt you for a message. Just close it by using Ctrl+D"
            git shortlog -sne > "$SHORTLOG_LOC/${REPO_NAME}.txt"
            echo "Saved shortlog for $REPO_NAME to ${REPO_NAME}.txt"
        else
            echo "$REPO_DIR is not a Git repository"
        fi
        
        # Return to the base directory
        cd "$1" || exit
    fi
done
