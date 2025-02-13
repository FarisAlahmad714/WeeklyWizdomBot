print("Bot starting - Railway deployment")
import asyncio
print("Imported asyncio")
from telethon import TelegramClient, events
print("Imported telethon")
from decouple import config
from datetime import datetime
import pytz
import logging
import sys
import traceback
print("All basic imports complete")

# Force immediate output flushing
sys.stdout.reconfigure(line_buffering=True)

# Telethon imports for forum topics
from telethon.tl.functions.channels import GetForumTopicsRequest
from telethon.tl.types import InputChannel
print("Telethon specific imports complete")

# Set up logging to be more verbose
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose logging
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    ]
)
logger = logging.getLogger(__name__)
logger.info("Logging configured")

# Configuration class to load environment variables
class Config:
    try:
        print("Loading configuration...")
        API_ID = config('API_ID', cast=int)
        API_HASH = config('API_HASH')
        BOT_TOKEN = config('BOT_TOKEN')
        PHONE_NUMBER = config('PHONE_NUMBER')
        USER_GROUP_ID = config('USER_GROUP_ID', cast=int)
        raw_user_ids = config('TARGET_USER_IDS')
        print(f"Raw TARGET_USER_IDS value: {raw_user_ids}")
        TARGET_USER_IDS = [int(id.strip()) for id in raw_user_ids.split(',') if id.strip().isdigit()]
        print(f"Parsed TARGET_USER_IDS: {TARGET_USER_IDS}")        
        NOTIFICATION_TARGET = config('NOTIFICATION_TARGET', cast=int)
        TIMEZONE = pytz.timezone('US/Pacific')
        print("Configuration loaded successfully")
        print(f"Monitoring group: {USER_GROUP_ID}")
        print(f"Target users: {TARGET_USER_IDS}")
    except Exception as e:
        print(f"Configuration error: {str(e)}")
        logger.error(f"Configuration error: {str(e)}", exc_info=True)
        raise

# Telegram Monitor class with thread/topic name support
class TelegramMonitor:
    def __init__(self):
        print("Initializing TelegramMonitor")
        self.user_client = TelegramClient('user_session', Config.API_ID, Config.API_HASH)
        self.bot_client = TelegramClient('bot_session', Config.API_ID, Config.API_HASH)
        self.message_cache = {}  # Cache to prevent duplicate processing
        print("TelegramMonitor initialized")

    def format_timestamp(self, dt):
        """Convert UTC time to Pacific Time with emojis for time of day."""
        try:
            print(f"Formatting timestamp for: {dt}")
            pacific_time = dt.astimezone(Config.TIMEZONE)
            hour = pacific_time.hour
            time_emoji = "🌙" if 0 <= hour < 6 else "🌅" if 6 <= hour < 12 else "☀️" if 12 <= hour < 18 else "🌆"
            formatted_time = f"{time_emoji} {pacific_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            print(f"Timestamp formatted: {formatted_time}")
            return formatted_time
        except Exception as e:
            print(f"Error formatting timestamp: {str(e)}")
            logger.error(f"Error formatting timestamp: {str(e)}", exc_info=True)
            return str(dt)

    async def get_forum_topic_title(self, chat, topic_id):
        """Use Telethon's GetForumTopicsRequest to fetch the actual forum topic title."""
        try:
            print(f"Getting forum topic title for topic_id: {topic_id}")
            input_channel = InputChannel(chat.id, chat.access_hash)
            result = await self.user_client(GetForumTopicsRequest(
                channel=input_channel,
                q='',
                offset_date=None,
                offset_id=0,
                offset_topic=topic_id,
                limit=1
            ))
            if result.topics and len(result.topics) > 0:
                title = result.topics[0].title
                print(f"Found topic title: {title}")
                return title
        except Exception as e:
            print(f"Error getting forum topic title: {str(e)}")
            logger.error(f"Failed to retrieve forum topic name: {str(e)}", exc_info=True)

        return f"Unnamed Topic ({topic_id})"

    async def get_topic_name(self, chat, topic_id):
        """Fallback method for getting topic names."""
        try:
            print(f"Getting topic name for topic_id: {topic_id}")
            async for message in self.user_client.iter_messages(chat.id, reply_to=topic_id, limit=1):
                name = message.text or f"Unnamed Topic ({topic_id})"
                print(f"Found topic name: {name}")
                return name
        except Exception as e:
            print(f"Error getting topic name: {str(e)}")
            logger.error(f"Error retrieving topic name for thread ID {topic_id}: {str(e)}", exc_info=True)
        return f"Unnamed Topic ({topic_id})"

    async def format_message(self, event, sender, chat):
        """Format the message to include thread/topic details."""
        try:
            print("Formatting message...")
            message_text = event.message.text if event.message.text else '[No text content]'

            # Check if chat is a forum
            if getattr(chat, 'forum', False):
                print("Chat is a forum")
                thread_id = getattr(event.message, 'forum_topic_id', None)
                if thread_id:
                    print(f"Getting topic title for thread_id: {thread_id}")
                    topic_name = await self.get_forum_topic_title(chat, thread_id)
                else:
                    topic_name = "No Topic"
            else:
                print("Chat is not a forum")
                thread_id = None
                topic_name = "No Topic"

            # Check if the message is from a channel or group
            is_channel = hasattr(event.message, 'post') and event.message.post
            source_type = "Channel" if is_channel else "Group"
            print(f"Message source type: {source_type}")
            
            formatted_message = (
                f"👤 **From**: @{getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Unknown')}\n"
                f"⏰ **Time**: {self.format_timestamp(event.date)}\n\n"
                f"📄 **Message**:\n"
                f"{message_text}\n"
                f"━━━━━━━━━━━━━━━━"
            )
            print("Message formatted successfully")
            return formatted_message
            
        except Exception as e:
            print(f"Error formatting message: {str(e)}")
            logger.error(f"Error formatting message: {str(e)}", exc_info=True)
            return f"New message from @{getattr(sender, 'username', 'Unknown')}: {event.message.text or '[No text]'}"

    async def handle_new_message(self, event):
        """Handle new messages from the monitored group."""
        try:
            print("Handling new message...")
            sender = await event.get_sender()
            logger.info(f"New message received from user ID: {sender.id if sender else 'Unknown'}")
            logger.info(f"Target user IDs: {Config.TARGET_USER_IDS}")
            
            if not sender:
                print("No sender found for message")
                logger.warning("No sender found for message")
                return
                
            if sender.id not in Config.TARGET_USER_IDS:
                print(f"Message from {sender.id} ignored - not in target users")
                logger.info(f"Message from {sender.id} ignored - not in target users")
                return

            chat = await event.get_chat()
            print(f"Message is in chat/group: {chat.id}")
            logger.info(f"Message is in chat/group: {chat.id}")
            message_hash = f"{sender.id}:{event.message.id}"
            
            # Prevent duplicate processing of messages
            if message_hash in self.message_cache:
                print(f"Duplicate message detected: {message_hash}")
                logger.info(f"Duplicate message detected: {message_hash}")
                return
                
            self.message_cache[message_hash] = datetime.now()
            print("Formatting message...")
            formatted_message = await self.format_message(event, sender, chat)

            # Forward the message to the notification target
            print(f"Sending message to notification target: {Config.NOTIFICATION_TARGET}")
            logger.info(f"Sending message to notification target: {Config.NOTIFICATION_TARGET}")
            await self.bot_client.send_message(
                Config.NOTIFICATION_TARGET,
                formatted_message,
                parse_mode="markdown"
            )
            print(f"Message successfully forwarded from {getattr(sender, 'username', 'Unknown')}")
            logger.info(f"Message successfully forwarded from {getattr(sender, 'username', 'Unknown')}")

        except Exception as e:
            print(f"Error handling message: {str(e)}")
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            traceback.print_exc()

    async def start(self):
        """Start the Telegram monitor."""
        print("Starting Telegram monitor...")
        try:
            print("Starting user client...")
            await self.user_client.start(phone=Config.PHONE_NUMBER)
            print("User client started")
            
            print("Starting bot client...")
            await self.bot_client.start(bot_token=Config.BOT_TOKEN)
            print("Bot client started")
            
            logger.info("Clients started successfully")
            logger.info(f"Monitoring group ID: {Config.USER_GROUP_ID}")
            logger.info(f"Target user IDs: {Config.TARGET_USER_IDS}")
            logger.info(f"Notification target: {Config.NOTIFICATION_TARGET}")

            @self.user_client.on(events.NewMessage(chats=Config.USER_GROUP_ID))
            async def message_handler(event):
                await self.handle_new_message(event)

            logger.info("Monitor started successfully")
            print("Monitor started successfully")
            
            try:
                print("Sending test message...")
                await self.bot_client.send_message(
                    Config.NOTIFICATION_TARGET,
                    "🟢 Bot started and monitoring messages",
                    parse_mode="markdown"
                )
                print("Test message sent successfully")
            except Exception as e:
                print(f"Error sending test message: {str(e)}")
                logger.error(f"Error sending test message: {str(e)}", exc_info=True)
            
            print("Waiting for messages...")
            await self.user_client.run_until_disconnected()

        except Exception as e:
            print(f"Error in start method: {str(e)}")
            logger.error(f"Error in start method: {str(e)}", exc_info=True)
            raise
        finally:
            print("Disconnecting clients...")
            await self.user_client.disconnect()
            await self.bot_client.disconnect()
            print("Clients disconnected")

if __name__ == "__main__":
    print("Main block started")
    try:
        monitor = TelegramMonitor()
        print("Running monitor...")
        asyncio.run(monitor.start())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        traceback.print_exc()
        sys.exit(1)