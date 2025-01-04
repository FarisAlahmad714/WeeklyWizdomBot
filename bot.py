import asyncio
from telethon import TelegramClient, events
from decouple import config

# Load credentials from the .env file
API_ID = config('API_ID', cast=int)
API_HASH = config('API_HASH')
BOT_TOKEN = config('BOT_TOKEN')
PHONE_NUMBER = config('PHONE_NUMBER')
USER_GROUP_ID = config('USER_GROUP_ID', cast=int)
TARGET_USER_IDS = [int(id.strip()) for id in config('TARGET_USER_IDS').split(',') if id.strip().isdigit()]
NOTIFICATION_TARGET = config('NOTIFICATION_TARGET', cast=int)

# Initialize Telegram clients
user_client = TelegramClient('user_session', API_ID, API_HASH)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)


async def start_user_client():
    # Start user client
    await user_client.start(phone=PHONE_NUMBER)
    if not await user_client.is_user_authorized():
        code = input("Enter the verification code: ")
        await user_client.sign_in(PHONE_NUMBER, code)

    print("Listening started with the user account...")

    # Attach handler for new messages
    @user_client.on(events.NewMessage(chats=USER_GROUP_ID))
    async def user_handler(event):
        sender = await event.get_sender()
        sender_id = sender.id

        if sender_id in TARGET_USER_IDS:  # Check if sender is in the list of target users
            original_text = event.message.text
            print(f"Captured message from target user ({sender_id}): {original_text}")

            # Forward the message to the notification target
            await bot_client.send_message(NOTIFICATION_TARGET, f"Message from {sender_id}: {original_text}")
            print(f"Message forwarded to the Notification Target ({NOTIFICATION_TARGET}) via bot.")


async def start_bot_client():
    # Start bot client
    await bot_client.start(bot_token=BOT_TOKEN)
    print("Bot account connected...")


async def main():
    # Run both clients concurrently
    try:
        await asyncio.gather(start_user_client(), start_bot_client())
        await user_client.run_until_disconnected()
        await bot_client.run_until_disconnected()
    except asyncio.CancelledError:
        print("Shutting down gracefully...")


if __name__ == "__main__":
    asyncio.run(main())
