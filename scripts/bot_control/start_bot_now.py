"""Start bot with proper UTF-8 encoding."""
import sys
import os

# Force UTF-8 encoding for stdout/stderr
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Now import and run the bot
from src.trading_bot import main

if __name__ == "__main__":
    main()
