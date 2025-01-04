import asyncio
from telethon import TelegramClient, events
from decouple import config
from datetime import datetime
import pytz

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


# Convert UTC to Pacific Time
def convert_to_pacific(utc_time):
    pacific = pytz.timezone('US/Pacific')
    pacific_dt = utc_time.astimezone(pacific)
    return pacific_dt.strftime('%Y-%m-%d %H:%M:%S %Z')  # Example: '2025-01-04 08:06:30 PST'


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
            # Extract sender name
            sender_name = sender.username if sender.username else sender.first_name

            # Get the group/channel name
            chat_name = event.chat.title if hasattr(event.chat, 'title') else "Private Chat"

            # Format the time
            message_time = event.date  # This is already a timezone-aware datetime
            pacific_time = convert_to_pacific(message_time)

            # Extract message content
            message_text = event.message.text

            # Handle replies (if any)
            if event.is_reply:
                reply = await event.get_reply_message()
                reply_sender = await reply.get_sender()
                reply_text = reply.text
                reply_username = reply_sender.username if reply_sender.username else reply_sender.first_name
            else:
                reply_text = "No reply"
                reply_username = "None"

            # Beautify and format the message
            formatted_message = (
                f"🌟 **New Message Alert** 🌟\n\n"
                f"📌 **Channel/Group**: `{chat_name}`\n"
                f"🔔 **From**: @{sender_name}\n"
                f"🕒 **Time (Pacific)**: {pacific_time}\n\n"
                f"↪️ **Replying to @{reply_username}**:\n"
                f"> {reply_text}\n\n"
                f"💬 **Message**:\n"
                f"{message_text}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

            # Print to console for debugging
            print(formatted_message)

            # Forward the message to the notification target
            await bot_client.send_message(NOTIFICATION_TARGET, formatted_message, parse_mode="markdown")
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
