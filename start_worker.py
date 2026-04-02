#!/usr/bin/env python3
"""
Simple script to start the trading worker
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Start the trading worker"""
    print("🚀 Starting Trading Bot Worker...")
    print("📊 This will run the autonomous trading bot in the background")
    print("⏹️ Press Ctrl+C to stop the worker")
    print("📋 Logs will be saved to 'trading_bot.log'")
    print("-" * 50)
    
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        # Start the worker
        subprocess.run([sys.executable, "worker.py"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️ Worker stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
