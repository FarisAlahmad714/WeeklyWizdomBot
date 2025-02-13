import sys
import asyncio
from telethon import TelegramClient
from decouple import config
import logging

# Force immediate flushing of print statements
sys.stdout.reconfigure(line_buffering=True)

print("Script starting...")

# Basic config setup
API_ID = config('API_ID', cast=int)
API_HASH = config('API_HASH')
BOT_TOKEN = config('BOT_TOKEN')
PHONE_NUMBER = config('PHONE_NUMBER')

print(f"Config loaded. API_ID: {API_ID}")

async def main():
    print("Entering main function")
    try:
        client = TelegramClient('bot_session', API_ID, API_HASH)
        print("Client created")
        
        await client.start(bot_token=BOT_TOKEN)
        print("Bot started")
        
        # Send a test message
        await client.send_message('me', 'Bot is running')
        print("Test message sent")
        
        await client.run_until_disconnected()
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise e

if __name__ == "__main__":
    print("Starting bot...")
    asyncio.run(main())