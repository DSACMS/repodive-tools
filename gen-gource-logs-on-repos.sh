#!/bin/bash

# Variables
GITHUB_API_URL="https://api.github.com"
ORGANIZATION="CMSGov"
TOKEN=$GITHUB_TOKEN  # Set your environment variable to your GitHub Token

# Function to fetch repositories from the organization
fetch_repositories() {
    curl -s -H "Authorization: token $TOKEN" "$GITHUB_API_URL/orgs/$ORGANIZATION/repos?per_page=100&page=$1"
}

GOURCE_LOG_LOC=$(readlink -f ./gource_logs)
cd $1

# Iterate through pages of repositories
page=1
while true; do
    # Fetch repositories for the current page
    response=$(fetch_repositories $page)
    
    # Check if the response contains repositories
    echo $response
    if [[ $response == "[ \n ]" ]]; then
        echo "No more repositories found."
        break
    fi
    
    repo_names=$(echo "$response" | jq -r '.[] | .name')

    for repo in $repo_names; do
        echo "Processing repository: $repo"
        # Add your code to process each repository here
        # For example:
        clone_url=$(echo "$response" | jq -r ".[] | select(.name == \"$repo\") | .clone_url")
        echo "Cloning repository from: $clone_url"
        git clone $clone_url || echo "failed or already exits"
        cd $repo
        git pull
        cd ..
        gource --output-custom-log "$GOURCE_LOG_LOC/pecos_${repo}.log" $1/$repo
        sed -i -r -E "s#(.+)\|#\1|/$repo#" "$GOURCE_LOG_LOC/pecos_${repo}.log"

    done
    
    # Increment page number for the next iteration
    page=$((page + 1))
done
