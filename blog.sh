#! /bin/bash
# Create a file for a blog with frontmatter template.

DATE=$(date +%Y-%m-%d)

function create_file() {
    if [[ -z $1 ]]; then
        echo "Got empty or invalid file name."
        exit 1
    fi
    dir=${BLOG_DIR:-site/blog}
    path="${dir}/$1.html"
    if [[ -f $path ]]; then
        echo "A file named $1 already exists at ${dir}"
        exit 1
    fi
    if touch "$path"; then
        echo "${path} created"
    else
        echo "Failed to write file ${path}"
        exit 1
    fi
    cat <<EOF > "$path"
---
title: ""
date: $DATE
tags: ["", ""]
description: ""
---

EOF
}

if [[ -n $1 ]]; then
    create_file "$1"
else
    read -rp "File name: " file_name
    create_file "$file_name"
fi
    