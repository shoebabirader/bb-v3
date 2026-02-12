"""Start the bot with console output logged to file."""

import subprocess
import sys

print("Starting bot with console logging...")
print("Console output will be saved to: logs/console_output.log")
print("Press Ctrl+C to stop the bot")
print("=" * 80)

# Start the bot and redirect output to file
with open("logs/console_output.log", "w", encoding="utf-8") as f:
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8"
    )
    
    try:
        for line in process.stdout:
            # Print to console
            print(line, end="")
            # Write to file
            f.write(line)
            f.flush()
    except KeyboardInterrupt:
        print("\n\nStopping bot...")
        process.terminate()
        process.wait()
        print("Bot stopped.")
