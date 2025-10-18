#!/bin/bash
cd "$(dirname "$0")"

TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_DIR="logs"
LOGFILE="$LOG_DIR/train_$TIMESTAMP.log"

# Ensure the logs directory exists
mkdir -p "$LOG_DIR"

# Activate virtual environment (venv is one level up)
source ../venv/bin/activate

echo "$(date '+%Y-%m-%d %H:%M:%S') - Virtual environment activated, starting training..." >> "$LOGFILE"

# Define cleanup function for safe shutdown
cleanup() {
    STATUS=$?
    if [ $STATUS -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Training completed successfully, shutting down EC2..." >> "$LOGFILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Training failed (exit code $STATUS), shutting down EC2..." >> "$LOGFILE"
    fi
    sudo shutdown -h +60
}

# Register trap safely
trap cleanup EXIT

# Run training script and timestamp output
python3 train.py 2>&1 | while IFS= read -r line; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $line"
done >> "$LOGFILE"
