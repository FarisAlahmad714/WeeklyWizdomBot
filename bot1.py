print("Bot starting - Railway deployment")
import asyncio
from telethon import TelegramClient, events
from decouple import config
from datetime import datetime
import pytz
import logging

# Telethon imports for forum topics
from telethon.tl.functions.channels import GetForumTopicsRequest
from telethon.tl.types import InputChannel

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration class to load environment variables
class Config:
    API_ID = config('API_ID', cast=int)
    API_HASH = config('API_HASH')
    BOT_TOKEN = config('BOT_TOKEN')
    PHONE_NUMBER = config('PHONE_NUMBER')
    USER_GROUP_ID = config('USER_GROUP_ID', cast=int)  # Example: -1002083186778
    TARGET_USER_IDS = [int(id.strip()) for id in config('TARGET_USER_IDS').split(',') if id.strip().isdigit()]
    NOTIFICATION_TARGET = config('NOTIFICATION_TARGET', cast=int)
    TIMEZONE = pytz.timezone('US/Pacific')

# Telegram Monitor class with thread/topic name support
class TelegramMonitor:
    def __init__(self):
        self.user_client = TelegramClient('user_session', Config.API_ID, Config.API_HASH)
        self.bot_client = TelegramClient('bot_session', Config.API_ID, Config.API_HASH)
        self.message_cache = {}  # Cache to prevent duplicate processing

    def format_timestamp(self, dt):
        """Convert UTC time to Pacific Time with emojis for time of day."""
        pacific_time = dt.astimezone(Config.TIMEZONE)
        hour = pacific_time.hour
        time_emoji = "🌙" if 0 <= hour < 6 else "🌅" if 6 <= hour < 12 else "☀️" if 12 <= hour < 18 else "🌆"
        return f"{time_emoji} {pacific_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"

    async def get_forum_topic_title(self, chat, topic_id):
        """
        Use Telethon's GetForumTopicsRequest to fetch the actual forum topic
        title (e.g., 'Fox's Den') given a topic ID.
        """
        try:
            # Convert chat to an InputChannel
            input_channel = InputChannel(chat.id, chat.access_hash)
            # Request the topic info
            result = await self.user_client(GetForumTopicsRequest(
                channel=input_channel,
                q='',                # no search query
                offset_date=None,
                offset_id=0,
                offset_topic=topic_id,
                limit=1
            ))
            # If we got at least one topic back, return its title
            if result.topics and len(result.topics) > 0:
                return result.topics[0].title
        except Exception as e:
            logger.error(f"Failed to retrieve forum topic name: {e}")

        # If anything fails or no topic found, fallback
        return f"Unnamed Topic ({topic_id})"

    async def get_topic_name(self, chat, topic_id):
        """
        Existing method you had. We now only use it for fallback or for older
        approach (reply_to=...) if you wish. But for forum topics, we have a
        dedicated approach above.
        """
        try:
            # Fallback logic (likely only relevant for non-forum or older approach)
            async for message in self.user_client.iter_messages(chat.id, reply_to=topic_id, limit=1):
                return message.text or f"Unnamed Topic ({topic_id})"
        except Exception as e:
            logger.error(f"Error retrieving topic name for thread ID {topic_id}: {e}")
        return f"Unnamed Topic ({topic_id})"

    async def format_message(self, event, sender, chat):
        """Format the message to include thread/topic details."""
        try:
            message_text = event.message.text if event.message.text else '[No text content]'

            # Check if chat is a forum
            if getattr(chat, 'forum', False):
                # It's a forum; use the forum_topic_id
                thread_id = getattr(event.message, 'forum_topic_id', None)
                if thread_id:
                    # Retrieve the real topic title:
                    topic_name = await self.get_forum_topic_title(chat, thread_id)
                else:
                    topic_name = "No Topic"
            else:
                # Non-forum: no real 'topic' concept
                thread_id = None
                topic_name = "No Topic"  # or use any fallback text

            # Check if the message is from a channel or group
            is_channel = hasattr(event.message, 'post') and event.message.post
            source_type = "Channel" if is_channel else "Group"
            
            formatted_message = (
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
        """Handle new messages from the monitored group."""
        try:
            sender = await event.get_sender()
            logger.info(f"New message received from user ID: {sender.id if sender else 'Unknown'}")
            logger.info(f"Target user IDs: {Config.TARGET_USER_IDS}")
            
            if not sender:
                logger.warning("No sender found for message")
                return
                
            if sender.id not in Config.TARGET_USER_IDS:
                logger.info(f"Message from {sender.id} ignored - not in target users")
                return

            chat = await event.get_chat()
            logger.info(f"Message is in chat/group: {chat.id}")
            message_hash = f"{sender.id}:{event.message.id}"
            
            # Prevent duplicate processing of messages
            if message_hash in self.message_cache:
                logger.info(f"Duplicate message detected: {message_hash}")
                return
                
            self.message_cache[message_hash] = datetime.now()
            logger.info("Formatting message...")
            formatted_message = await self.format_message(event, sender, chat)

            # Forward the message to the notification target
            logger.info(f"Sending message to notification target: {Config.NOTIFICATION_TARGET}")
            await self.bot_client.send_message(
                Config.NOTIFICATION_TARGET,
                formatted_message,
                parse_mode="markdown"
            )
            logger.info(f"Message successfully forwarded from {getattr(sender, 'username', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            # Print full traceback for better debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
                

    async def start(self):
        """Start the Telegram monitor."""
        try:
            await self.user_client.start(phone=Config.PHONE_NUMBER)
            await self.bot_client.start(bot_token=Config.BOT_TOKEN)
            
            logger.info("Clients started successfully")
            logger.info(f"Monitoring group ID: {Config.USER_GROUP_ID}")
            logger.info(f"Target user IDs: {Config.TARGET_USER_IDS}")
            logger.info(f"Notification target: {Config.NOTIFICATION_TARGET}")

            @self.user_client.on(events.NewMessage(chats=Config.USER_GROUP_ID))
            async def message_handler(event):
                await self.handle_new_message(event)

            logger.info("Monitor started successfully")
            
            # Test message to notification channel
            await self.bot_client.send_message(
                Config.NOTIFICATION_TARGET,
                "🟢 Bot started and monitoring messages",
                parse_mode="markdown"
            )
            
            await self.user_client.run_until_disconnected()

        except Exception as e:
            logger.error(f"Error starting monitor: {e}", exc_info=True)
        finally:
            await self.user_client.disconnect()
            await self.bot_client.disconnect()