#!/usr/bin/env bash

set -e
echo "Preparing dataset..."
mkdir -p data/raw
unzip -o data/archives/OpenSSH.zip -d data/raw
echo "Dataset extracted successfully."
