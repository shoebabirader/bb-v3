"""Check if signal generation is enabled."""
from src.config import Config
from src.risk_manager import RiskManager
from src.position_sizer import PositionSizer

print("="*70)
print("SIGNAL GENERATION CHECK")
print("="*70)

# Load config
config = Config.load_from_file('config/config.json')

# Create risk manager
position_sizer = PositionSizer(config)
risk_manager = RiskManager(config, position_sizer)

# Check if signal generation is enabled
is_enabled = risk_manager.is_signal_generation_enabled()

print(f"\nSignal Generation Enabled: {is_enabled}")

if not is_enabled:
    print("\n✗ SIGNAL GENERATION IS DISABLED!")
    print("  This is why trades aren't executing even when signals are detected.")
    print("\n  Possible reasons:")
    print("  - Panic close was triggered")
    print("  - Signal generation was manually disabled")
    print("\n  To fix: Restart the bot")
else:
    print("\n✓ Signal generation is enabled")
    print("  The issue must be something else")

print(f"\n{'='*70}")
