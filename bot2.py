import asyncio
from telethon import TelegramClient, events
from decouple import config
from datetime import datetime, time
import pytz
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    API_ID = config('API_ID', cast=int)
    API_HASH = config('API_HASH')
    BOT_TOKEN = config('BOT_TOKEN')
    PHONE_NUMBER = config('PHONE_NUMBER')
    USER_GROUP_ID = config('USER_GROUP_ID', cast=int)  # -1002083186778
    TARGET_USER_IDS = [int(id.strip()) for id in config('TARGET_USER_IDS').split(',') if id.strip().isdigit()]
    NOTIFICATION_TARGET = config('NOTIFICATION_TARGET', cast=int)
    TIMEZONE = pytz.timezone('US/Pacific')
    
    # Define mute interval (7:00 AM - 7:30 AM Pacific)
    MUTE_START = time(7, 0)  # 7:00 AM
    MUTE_END = time(7, 30)   # 7:30 AM

class TelegramMonitor:
    def __init__(self):
        self.user_client = TelegramClient('user_session', Config.API_ID, Config.API_HASH)
        self.bot_client = TelegramClient('bot_session', Config.API_ID, Config.API_HASH)
        self.message_cache = {}

    def is_muted(self):
        """Check if current time is within mute period"""
        current_time = datetime.now(Config.TIMEZONE).time()
        return Config.MUTE_START <= current_time <= Config.MUTE_END

    def format_timestamp(self, dt):
        pacific_time = dt.astimezone(Config.TIMEZONE)
        hour = pacific_time.hour
        time_emoji = "🌙" if 0 <= hour < 6 else "🌅" if 6 <= hour < 12 else "☀️" if 12 <= hour < 18 else "🌆"
        return f"{time_emoji} {pacific_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"

    async def format_message(self, event, sender, chat):
        try:
            message_text = event.message.text if event.message.text else '[No text content]'
            
            # Check if message is from a channel
            is_channel = hasattr(event.message, 'post') and event.message.post
            source_type = "Channel" if is_channel else "Group"
            
            formatted_message = (
                f"🚨 **New Message** 🚨\n\n"
                f"📱 **{source_type}**: `{chat.title}`\n"
                f"👤 **From**: @{getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Unknown')}\n"
                f"⏰ **Time**: {self.format_timestamp(event.date)}\n\n"
                f"📄 **Message**:\n"
                f"{message_text}\n"
                f"━━━━━━━━━━━━━━━━"
            )
            return formatted_message
            
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return f"New message from @{getattr(sender, 'username', 'Unknown')}: {event.message.text or '[No text]'}"

    async def handle_new_message(self, event):
        try:
            # Check if we're in mute period
            if self.is_muted():
                logger.info("Message received during mute period (7:00-7:30 AM PT) - ignoring")
                return

            sender = await event.get_sender()
            if not sender or sender.id not in Config.TARGET_USER_IDS:
                return

            chat = await event.get_chat()
            message_hash = f"{sender.id}:{event.message.id}"
            
            if message_hash in self.message_cache:
                return
                
            self.message_cache[message_hash] = datetime.now()
            formatted_message = await self.format_message(event, sender, chat)

            await self.bot_client.send_message(
                Config.NOTIFICATION_TARGET,
                formatted_message,
                parse_mode="markdown"
            )
            logger.info(f"Message forwarded from {getattr(sender, 'username', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def start(self):
        try:
            await self.user_client.start(phone=Config.PHONE_NUMBER)
            await self.bot_client.start(bot_token=Config.BOT_TOKEN)

            # Monitor all messages in the group (including channel posts)
            @self.user_client.on(events.NewMessage(chats=Config.USER_GROUP_ID))
            async def message_handler(event):
                await self.handle_new_message(event)

            logger.info("Monitor started successfully")
            logger.info(f"Mute period set for {Config.MUTE_START.strftime('%I:%M %p')} - {Config.MUTE_END.strftime('%I:%M %p')} Pacific Time")
            
            await self.user_client.run_until_disconnected()

        except Exception as e:
            logger.error(f"Error starting monitor: {e}")
        finally:
            await self.user_client.disconnect()
            await self.bot_client.disconnect()

if __name__ == "__main__":
    monitor = TelegramMonitor()
    asyncio.run(monitor.start())