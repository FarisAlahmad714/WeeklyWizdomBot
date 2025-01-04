from telethon import TelegramClient

API_ID = 22848718
API_HASH = 'ff7c9769d2260c27607f9a71ef53fbe1'
PHONE_NUMBER = '+17143862366'  # Your Telegram phone number, including the country code

client = TelegramClient('user_session', API_ID, API_HASH)

async def main():
    # Start the client and log in
    await client.start(phone=PHONE_NUMBER)

    # Fetch all dialogs (chats, groups, channels)
    async for dialog in client.iter_dialogs():
        print(f"Name: {dialog.name}, ID: {dialog.id}")

# Run the script
with client:
    client.loop.run_until_complete(main())
