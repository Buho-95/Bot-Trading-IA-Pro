#!/usr/bin/env python3
"""
Telegram Bot Setup Helper
Guides users through setting up Telegram notifications
"""

from notifications import setup_telegram_config

def main():
    """Run the setup guide"""
    print("🤖 Trading Bot - Telegram Setup")
    print("=" * 40)
    setup_telegram_config()
    
    input("\nPress Enter after you've configured your bot...")
    
    # Test the configuration
    try:
        from notifications import TelegramNotifier
        notifier = TelegramNotifier()
        
        if notifier.enabled:
            print("✅ Testing Telegram connection...")
            if notifier.send_notification("🧪 Test message from Trading Bot Setup"):
                print("✅ Telegram notifications are working!")
                print("🎉 Your bot is ready to send notifications!")
            else:
                print("❌ Failed to send test message")
                print("Please check your bot token and chat ID")
        else:
            print("❌ Telegram not properly configured")
            print("Please check your environment variables")
    
    except Exception as e:
        print(f"❌ Error testing Telegram: {e}")

if __name__ == "__main__":
    main()
