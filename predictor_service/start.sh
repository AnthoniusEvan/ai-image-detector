#!/bin/bash
set -e

cd /home/ubuntu/ai-image-predictor/predictor_service

# Stop old container if any
if [ "$(sudo docker ps -aq -f name=predictor_service)" ]; then
  sudo docker rm -f predictor_service || true
fi

# Run from prebuilt local image
sudo docker compose up
