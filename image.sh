#!/usr/bin/env bash
# Upload an image to S3 and copy the <img> tag for it to the clipboard.
#
#   ./image.sh ~/Pictures/IMG_1234.JPG              -> /images/img_1234.jpg
#   ./image.sh ~/Pictures/IMG_1234.JPG baker-summit  -> /images/baker-summit.jpg
#   ./image.sh -f ...                                 replace an image that already exists
#
# Pages reference it as <img src="/images/NAME">; the build points that at the bucket.

set -euo pipefail

BUCKET=${S3_CONTENT_BUCKET:-smr-webdev-content}

force=false
if [[ ${1:-} == "-f" ]]; then force=true; shift; fi

file=${1:-}
[[ -f $file ]] || { echo "Usage: $0 [-f] <image file> [name]" >&2; exit 1; }

ext=$(echo "${file##*.}" | tr '[:upper:]' '[:lower:]')
[[ $ext == "jpeg" ]] && ext="jpg"
case $ext in
    jpg|png|gif|webp|svg|avif) ;;
    *) echo "Not an image type I know: .$ext" >&2; exit 1 ;;
esac

# Name: the one given, or the file's own name, as lowercase-with-dashes.
base=${2:-$(basename "${file%.*}")}
name=$(echo "$base" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9_' '-' | sed 's/^-//; s/-$//')
[[ -n $name ]] || { echo "Couldn't make a name from '$base'" >&2; exit 1; }
key="images/${name}.${ext}"

if ! $force && aws s3api head-object --bucket "$BUCKET" --key "$key" >/dev/null 2>&1; then
    echo "s3://${BUCKET}/${key} already exists. Pick another name, or use -f to replace it." >&2
    exit 1
fi

# aws s3 cp sets Content-Type from the extension. Browsers may keep a replaced image
# for up to a day, so prefer a new name over -f for images already on the site.
aws s3 cp "$file" "s3://${BUCKET}/${key}" --cache-control "public, max-age=86400" --only-show-errors

tag="<img src=\"/${key}\" alt=\"\">"
echo "Uploaded s3://${BUCKET}/${key}"
echo "$tag"
if command -v pbcopy >/dev/null; then
    printf '%s' "$tag" | pbcopy
    echo "(copied to clipboard; fill in the alt text)"
fi
