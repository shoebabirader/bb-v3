"""Fix Unicode encoding errors in Windows console by replacing Unicode characters with ASCII."""

import os
import sys

def fix_file(filepath):
    """Replace Unicode characters with ASCII equivalents in a file."""
    print(f"Fixing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count replacements
    replacements = {
        '✓': '[OK]',
        '✗': '[X]',
        '⚠️': '[WARNING]',
        '⚠': '[WARNING]',
        'ℹ': '[i]'
    }
    
    total_changes = 0
    for old, new in replacements.items():
        count = content.count(old)
        if count > 0:
            print(f"  Replacing {count} instances of '{old}' with '{new}'")
            content = content.replace(old, new)
            total_changes += count
    
    if total_changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Fixed {total_changes} Unicode characters")
    else:
        print(f"  No changes needed")
    
    return total_changes

def main():
    """Fix all Python files in src/ directory."""
    print("=" * 80)
    print("FIXING UNICODE ENCODING ERRORS")
    print("=" * 80)
    print()
    
    files_to_fix = [
        'src/trading_bot.py',
        'src/order_executor.py',
        'src/ui_display.py'
    ]
    
    total_fixed = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            fixed = fix_file(filepath)
            total_fixed += fixed
        else:
            print(f"Warning: {filepath} not found")
    
    print()
    print("=" * 80)
    print(f"COMPLETE: Fixed {total_fixed} Unicode characters total")
    print("=" * 80)
    print()
    print("The bot should now run without encoding errors on Windows!")
    print("Restart the bot with: python main.py")

if __name__ == "__main__":
    main()
