#!/usr/bin/env bash
# Create a file for a blog with frontmatter template.

DATE=$(date +%Y-%m-%d)

create_file() {
    [[ -z $1 ]] && { echo "Got empty or invalid file name." >&2; exit 1; }
    dir=${BLOG_DIR:-site/blog}
    path="${dir}/$1.html"
    [[ -f $path ]] && 
    { echo "A file named $1 already exists at ${dir}" >&2 ; exit 1; } 
    if ! cat <<EOF > "$path"
---
title: ""
date: $DATE
tags: ["", ""]
description: ""
---

EOF
    then
        echo "Failed to write file ${path}"
        exit 1
    fi
    ${EDITOR:-code} "$path"
}

if [[ -n $1 ]]; then
    create_file "$1"
else
    read -rp "File name: " file_name
    create_file "$file_name"
fi