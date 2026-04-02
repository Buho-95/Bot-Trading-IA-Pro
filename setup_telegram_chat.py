#!/usr/bin/env python3
"""
Telegram Chat ID Setup Script
Helps users get their Telegram Chat ID for notifications
"""

import requests
import os
from pathlib import Path

def load_token():
    """Load Telegram token from tokenTel.env"""
    env_path = Path("tokenTel.env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and 'TELEGRAM_BOT_TOKEN' in line:
                    return line.split('=', 1)[1].strip()
    return None

def get_chat_id(bot_token: str):
    """Get the chat ID by checking bot updates"""
    print("🔍 Getting your Chat ID...")
    print("📱 Send any message to your bot now...")
    print("⏳ Waiting for message...")
    
    # Get updates from bot
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    import time
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('result'):
                # Get the first message
                message = data['result'][0]
                chat_id = message['message']['chat']['id']
                user_info = message['message']['chat'].get('first_name', 'User')
                
                print(f"✅ Found Chat ID: {chat_id}")
                print(f"👤 User: {user_info}")
                return chat_id
            else:
                print(f"⏳ Waiting for message... ({attempt + 1}/{max_attempts})")
                time.sleep(2)
                attempt += 1
                
        except Exception as e:
            print(f"❌ Error: {e}")
            attempt += 1
            time.sleep(2)
    
    print("❌ No message received. Please make sure:")
    print("   1. You've sent a message to your bot")
    print("   2. The bot token is correct")
    print("   3. You haven't blocked the bot")
    return None

def update_env_file(chat_id: str):
    """Update tokenTel.env with chat ID"""
    env_path = Path("tokenTel.env")
    
    try:
        # Read current content
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Update chat ID
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('TELEGRAM_CHAT_ID'):
                updated_lines.append(f'TELEGRAM_CHAT_ID={chat_id}')
            else:
                updated_lines.append(line)
        
        # Write back
        with open(env_path, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print(f"✅ Updated {env_path} with your Chat ID")
        return True
        
    except Exception as e:
        print(f"❌ Error updating file: {e}")
        return False

def test_telegram_connection(bot_token: str, chat_id: str):
    """Test Telegram connection"""
    print("🧪 Testing Telegram connection...")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': '🎉 Trading Bot Telegram Setup Complete!\n\n✅ Notifications are now enabled\n📊 You will receive trading signals and model retraining alerts\n🤖 Your Trading Bot is ready!'
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        
        if response.json().get('ok'):
            print("✅ Test message sent successfully!")
            print("📱 Check your Telegram for the test message")
            return True
        else:
            print("❌ Failed to send test message")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

def main():
    """Main setup function"""
    print("🤖 Trading Bot Telegram Setup")
    print("=" * 40)
    
    # Load token
    bot_token = load_token()
    if not bot_token:
        print("❌ No Telegram token found in tokenTel.env")
        print("Please add your bot token first:")
        print("TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    print(f"✅ Bot token loaded: {bot_token[:10]}...")
    
    # Get chat ID
    chat_id = get_chat_id(bot_token)
    if not chat_id:
        print("❌ Could not get Chat ID")
        return
    
    # Update env file
    if update_env_file(chat_id):
        print("✅ Configuration updated successfully")
    else:
        print("❌ Failed to update configuration")
        return
    
    # Test connection
    if test_telegram_connection(bot_token, chat_id):
        print("\n🎉 Telegram setup completed successfully!")
        print("📊 Your trading bot will now send notifications for:")
        print("   • New trading signals (BUY/SELL)")
        print("   • Model retraining completion")
        print("   • Daily performance summaries")
        print("   • Error alerts and system status")
        print("\n✅ You're all set!")
    else:
        print("\n❌ Setup completed but test failed")
        print("Please check your bot configuration")

if __name__ == "__main__":
    main()
