#!/bin/bash

# Path to counter file
COUNTER_FILE="$HOME/.daily_script_counter"

# Initialize counter if file doesn't exist
if [ ! -f "$COUNTER_FILE" ]; then
  echo 1 > "$COUNTER_FILE"
fi

# Read current number
NUMBER=$(cat "$COUNTER_FILE")

# Call your script with the number
/Users/yourusername/scripts/my_script.sh "$NUMBER"

# Increment number
NEXT_NUMBER=$((NUMBER + 1))
echo "$NEXT_NUMBER" > "$COUNTER_FILE"
