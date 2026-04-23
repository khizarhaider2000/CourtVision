#!/bin/bash
# Uploads locally-fetched NBA data files to EC2.
#
# Usage:
#   bash scripts/sync_to_ec2.sh /path/to/key.pem
#
# Example:
#   bash scripts/sync_to_ec2.sh ~/Downloads/fastapi_key.pem

set -e

KEY=${1:?"Usage: bash scripts/sync_to_ec2.sh /path/to/key.pem"}
EC2_USER="ubuntu"
EC2_HOST="52.15.49.162"
REMOTE_PATH="~/CourtVision/backend/data/"

# Ensure remote data dir exists
ssh -i "$KEY" "${EC2_USER}@${EC2_HOST}" "mkdir -p ~/CourtVision/backend/data"

echo "Syncing backend/data/ → ${EC2_USER}@${EC2_HOST}:${REMOTE_PATH}"
rsync -avz --progress \
  -e "ssh -i ${KEY}" \
  backend/data/ \
  "${EC2_USER}@${EC2_HOST}:${REMOTE_PATH}"

echo ""
echo "Sync complete. Restart uvicorn on EC2 if it's already running."
