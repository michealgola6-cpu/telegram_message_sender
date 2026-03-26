#!/usr/bin/env python3
"""
Telegram User Bot - Send Messages to Any Username
Deployment-ready version for Render
"""

import asyncio
import os
import json
import sqlite3
import logging
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UserPrivacyRestrictedError,
    UsernameNotOccupiedError,
    RPCError
)
from telethon.tl.types import User
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# Get credentials from environment variables (safer for deployment)
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Settings
DELAY_SECONDS = int(os.environ.get('DELAY_SECONDS', 30))
DAILY_LIMIT = int(os.environ.get('DAILY_LIMIT', 50))
USER_SESSION_FILE = "user_session"

# Conversation states
(WAITING_MESSAGE, WAITING_USERNAMES, CONFIRM_SEND) = range(3)

# ==================== DATABASE SETUP ====================
def init_database():
    """Initialize SQLite database for tracking"""
    conn = sqlite3.connect('message_tracker.db')
    c = conn.cursor()
    
    # Track sent messages
    c.execute('''CREATE TABLE IF NOT EXISTS sent_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  recipient_username TEXT,
                  recipient_id INTEGER,
                  message TEXT,
                  status TEXT,
                  sent_time TIMESTAMP,
                  error TEXT)''')
    
    # Track daily stats
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stats
                 (date TEXT PRIMARY KEY,
                  count INTEGER DEFAULT 0)''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def log_sent_message(username, user_id, message, status, error=None):
    """Log a sent message to database"""
    conn = sqlite3.connect('message_tracker.db')
    c = conn.cursor()
    c.execute('''INSERT INTO sent_messages 
                 (recipient_username, recipient_id, message, status, sent_time, error)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (username, user_id, message, status, datetime.now(), error))
    conn.commit()
    conn.close()

def get_today_count():
    """Get number of messages sent today"""
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('message_tracker.db')
    c = conn.cursor()
    c.execute('SELECT count FROM daily_stats WHERE date = ?', (today,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def increment_today_count():
    """Increment today's message count"""
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect('message_tracker.db')
    c = conn.cursor()
    c.execute('''INSERT INTO daily_stats (date, count) 
                 VALUES (?, 1) 
                 ON CONFLICT(date) DO UPDATE SET count = count + 1''', (today,))
    conn.commit()
    conn.close()

# ==================== TELEGRAM USER CLIENT ====================
class UserMessageSender:
    """Handles sending messages using the user account"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.user_info = None
        
    async def connect(self):
        """Connect the user client"""
        try:
            if not API_ID or not API_HASH:
                return False, "❌ API_ID or API_HASH not configured in environment variables"
                
            self.client = TelegramClient(USER_SESSION_FILE, API_ID, API_HASH)
            await self.client.start()
            
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                self.is_connected = True
                self.user_info = me
                return True, f"✅ Connected as: {me.first_name} (@{me.username})"
            else:
                return False, "❌ Not authorized. Please check your API credentials."
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False, f"❌ Connection failed: {str(e)}"
    
    async def disconnect(self):
        """Disconnect the user client"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
    
    async def send_to_username(self, username, message):
        """Send a message to a username"""
        try:
            # Remove @ if present
            username = username.strip().replace('@', '')
            
            # Get user entity
            entity = await self.client.get_entity(username)
            
            if not isinstance(entity, User):
                return False, "Not a user (might be a channel/group)"
            
            # Send message
            await self.client.send_message(entity, message)
            
            return True, f"✅ Sent to {entity.first_name or 'User'} (@{username})"
            
        except UsernameNotOccupiedError:
            return False, f"❌ Username @{username} does not exist"
        except UserPrivacyRestrictedError:
            return False, f"❌ @{username} has privacy restrictions"
        except FloodWaitError as e:
            return False, f"⚠️ Rate limited. Wait {e.seconds} seconds"
        except RPCError as e:
            return False, f"❌ Telegram error: {str(e)}"
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False, f"❌ Error: {str(e)}"
    
    async def send_batch(self, usernames, message, progress_callback=None):
        """Send messages to multiple users"""
        results = []
        today_count = get_today_count()
        
        for i, username in enumerate(usernames, 1):
            # Check daily limit
            if today_count + i > DAILY_LIMIT:
                results.append({
                    'username': username,
                    'success': False,
                    'response': f'Daily limit reached ({DAILY_LIMIT} messages/day)'
                })
                continue
            
            # Send message
            success, response = await self.send_to_username(username, message)
            
            result = {
                'username': username,
                'success': success,
                'response': response
            }
            results.append(result)
            
            # Log the attempt
            log_sent_message(username, None, message, 
                            'success' if success else 'failed', 
                            response if not success else None)
            
            if success:
                increment_today_count()
            
            # Call progress callback if provided
            if progress_callback:
                await progress_callback(i, len(usernames), result)
            
            # Add delay between messages (except last)
            if i < len(usernames):
                await asyncio.sleep(DELAY_SECONDS)
        
        return results

# ==================== BOT HANDLERS ====================
class MessageBot:
    """Telegram bot handler"""
    
    def __init__(self):
        self.user_sender = UserMessageSender()
        self.pending_messages = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = """
🤖 **Telegram Message Sender Bot**

This bot uses YOUR Telegram account to send messages to any public username!

**Features:**
✅ Send to ANY public username (not just contacts)
✅ Batch sending support
✅ Daily limit protection
✅ Rate limiting with delays
✅ Message tracking

**Commands:**
/start - Show this message
/connect - Connect your Telegram account
/status - Check connection status
/send - Start sending messages
/stats - View today's statistics
/help - Show help message

**How to use:**
1. First, connect your Telegram account using `/connect`
2. Then use `/send` to send messages to usernames

⚠️ **Important**: Use responsibly to avoid account restrictions!
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
📚 **Help Guide**

**Step 1: Connect Account**
Use `/connect` to connect your Telegram account.
The API credentials are already configured in the bot.

**Step 2: Send Messages**
Use `/send` and follow the prompts:
1. Enter your message
2. Enter usernames (one per line, or comma-separated)
3. Confirm and send

**Tips:**
- Usernames can be entered without @ symbol
- Maximum {DAILY_LIMIT} messages per day
- {DELAY_SECONDS} seconds delay between messages
- Use `/stats` to check your daily usage

**Example:**
Message: "Hello! This is a test message"
Usernames: user1, user2, user3

⚠️ **Important**: You can only message users who haven't blocked you or set privacy restrictions.
        """
        
        await update.message.reply_text(help_text)
    
    async def connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /connect command"""
        chat_id = update.effective_chat.id
        
        # Check if already connected
        if self.user_sender.is_connected:
            await update.message.reply_text("✅ You are already connected!")
            return
        
        await update.message.reply_text(
            "🔐 **Connecting to your Telegram account...**\n\n"
            "Please wait...",
            parse_mode='Markdown'
        )
        
        success, message = await self.user_sender.connect()
        
        if success:
            await update.message.reply_text(
                f"✅ {message}\n\n"
                "You can now use /send to send messages to usernames!"
            )
        else:
            await update.message.reply_text(
                f"❌ {message}\n\n"
                "Please check your API credentials in the environment variables."
            )
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if self.user_sender.is_connected:
            me = self.user_sender.user_info
            today_count = get_today_count()
            
            status_text = f"""
📊 **Account Status**

✅ **Connected**
👤 Account: {me.first_name} (@{me.username})
📱 User ID: {me.id}

📈 **Today's Activity**
Messages sent: {today_count}/{DAILY_LIMIT}
Remaining: {DAILY_LIMIT - today_count}

⚙️ **Settings**
Delay between messages: {DELAY_SECONDS} seconds
Daily limit: {DAILY_LIMIT} messages

Use /send to send more messages!
            """
            await update.message.reply_text(status_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ **Not connected**\n\n"
                "Use /connect to connect your Telegram account first.",
                parse_mode='Markdown'
            )
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        today_count = get_today_count()
        
        # Get last 10 messages
        conn = sqlite3.connect('message_tracker.db')
        c = conn.cursor()
        c.execute('''SELECT recipient_username, status, sent_time 
                     FROM sent_messages 
                     ORDER BY sent_time DESC 
                     LIMIT 10''')
        recent = c.fetchall()
        conn.close()
        
        stats_text = f"""
📊 **Message Statistics**

**Today**
Messages: {today_count}/{DAILY_LIMIT}
Remaining: {DAILY_LIMIT - today_count}

**Recent Messages (Last 10)**
"""
        for username, status, sent_time in recent:
            emoji = "✅" if status == "success" else "❌"
            time_str = datetime.strptime(sent_time, '%Y-%m-%d %H:%M:%S.%f').strftime('%H:%M')
            stats_text += f"{emoji} @{username} - {time_str}\n"
        
        await update.message.reply_text(stats_text)
    
    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the send conversation"""
        if not self.user_sender.is_connected:
            await update.message.reply_text(
                "❌ **Not connected**\n\n"
                "Please use /connect first to connect your Telegram account.",
                parse_mode='Markdown'
            )
            return
        
        # Check daily limit
        today_count = get_today_count()
        if today_count >= DAILY_LIMIT:
            await update.message.reply_text(
                f"⚠️ **Daily limit reached**\n\n"
                f"You have sent {DAILY_LIMIT} messages today.\n"
                f"Please try again tomorrow.",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(
            f"📝 **Send Messages**\n\n"
            f"Please enter the message you want to send:\n\n"
            f"*Daily limit remaining: {DAILY_LIMIT - today_count} messages*\n"
            f"*Delay: {DELAY_SECONDS} seconds between messages*",
            parse_mode='Markdown'
        )
        
        return WAITING_MESSAGE
    
    async def receive_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive the message from user"""
        message_text = update.message.text
        
        # Store in context
        context.user_data['message'] = message_text
        
        await update.message.reply_text(
            f"✅ Message saved!\n\n"
            f"**Your message:**\n\"{message_text}\"\n\n"
            f"Now, enter the usernames you want to send this message to.\n\n"
            f"**Format:**\n"
            f"- One username per line\n"
            f"- Or comma-separated: user1, user2, user3\n"
            f"- Don't include @ symbol\n\n"
            f"Example:\n"
            f"john_doe\n"
            f"jane_smith\n"
            f"username123",
            parse_mode='Markdown'
        )
        
        return WAITING_USERNAMES
    
    async def receive_usernames(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and parse usernames"""
        usernames_input = update.message.text
        
        # Parse usernames
        usernames = []
        
        # Try comma separation first
        if ',' in usernames_input:
            usernames = [u.strip().replace('@', '') for u in usernames_input.split(',') if u.strip()]
        else:
            # Try line separation
            usernames = [line.strip().replace('@', '') for line in usernames_input.split('\n') if line.strip()]
        
        # Remove duplicates
        usernames = list(dict.fromkeys(usernames))
        
        # Check against daily limit
        today_count = get_today_count()
        remaining = DAILY_LIMIT - today_count
        
        if len(usernames) > remaining:
            await update.message.reply_text(
                f"⚠️ You have {len(usernames)} usernames but only {remaining} messages remaining today.\n"
                f"Please reduce the number of recipients."
            )
            return WAITING_USERNAMES
        
        # Store in context
        context.user_data['usernames'] = usernames
        
        # Show preview
        preview = f"**📋 Preview**\n\n"
        preview += f"**Message:**\n\"{context.user_data['message']}\"\n\n"
        preview += f"**Recipients ({len(usernames)}):**\n"
        
        for i, username in enumerate(usernames[:10], 1):
            preview += f"{i}. @{username}\n"
        
        if len(usernames) > 10:
            preview += f"... and {len(usernames) - 10} more\n"
        
        preview += f"\n**Estimated time:** ~{len(usernames) * DELAY_SECONDS / 60:.1f} minutes"
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            preview,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return CONFIRM_SEND
    
    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle confirmation callback"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Operation cancelled.")
            return ConversationHandler.END
        
        # Proceed with sending
        await query.edit_message_text(
            "📤 **Sending messages...**\n\n"
            "Please wait, this may take a few minutes.\n"
            "I'll notify you when complete.",
            parse_mode='Markdown'
        )
        
        usernames = context.user_data['usernames']
        message = context.user_data['message']
        
        # Send the messages
        results = []
        
        async def update_progress(current, total, result):
            # Update status message every few messages
            if current % 5 == 0 or current == total:
                status_msg = f"📤 **Sending...**\n\n"
                status_msg += f"Progress: {current}/{total}\n"
                status_msg += f"Success: {len([r for r in results if r['success']])}\n"
                status_msg += f"Failed: {len([r for r in results if not r['success']])}"
                await query.edit_message_text(status_msg, parse_mode='Markdown')
        
        results = await self.user_sender.send_batch(usernames, message, update_progress)
        
        # Prepare final report
        success_count = len([r for r in results if r['success']])
        failed_count = len([r for r in results if not r['success']])
        
        report = f"✅ **Sending Complete!**\n\n"
        report += f"**Results:**\n"
        report += f"✅ Success: {success_count}\n"
        report += f"❌ Failed: {failed_count}\n\n"
        
        if failed_count > 0:
            report += f"**Failed attempts:**\n"
            for r in results[:5]:  # Show first 5 failures
                if not r['success']:
                    report += f"• @{r['username']}: {r['response'][:50]}...\n"
        
        report += f"\nUse /stats to see full history."
        
        await query.edit_message_text(report, parse_mode='Markdown')
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        await update.message.reply_text("❌ Operation cancelled.")
        return ConversationHandler.END

# ==================== MAIN ====================
async def main():
    """Main function to run the bot"""
    # Check if credentials are set
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables!")
        return
    
    if not API_ID or not API_HASH:
        logger.error("API_ID or API_HASH not set in environment variables!")
        return
    
    # Initialize database
    init_database()
    
    # Create bot instance
    message_bot = MessageBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add conversation handler for send command
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('send', message_bot.send_command)],
        states={
            WAITING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_bot.receive_message)],
            WAITING_USERNAMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_bot.receive_usernames)],
            CONFIRM_SEND: [CallbackQueryHandler(message_bot.handle_confirmation)]
        },
        fallbacks=[CommandHandler('cancel', message_bot.cancel)]
    )
    
    # Add handlers
    application.add_handler(CommandHandler('start', message_bot.start))
    application.add_handler(CommandHandler('help', message_bot.help))
    application.add_handler(CommandHandler('connect', message_bot.connect))
    application.add_handler(CommandHandler('status', message_bot.status))
    application.add_handler(CommandHandler('stats', message_bot.stats))
    application.add_handler(conv_handler)
    
    # Start bot
    logger.info("🤖 Bot is starting...")
    
    # Use polling (works better for Render)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot is running! Press Ctrl+C to stop")
    
    # Keep the bot running
    stop_signal = asyncio.Event()
    await stop_signal.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
