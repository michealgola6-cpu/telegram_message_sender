#!/usr/bin/env python3
"""
Telegram Message Sender
Uses Telethon to send messages from your account to specified usernames.
Features:
- Secure authentication
- Rate limiting with delays
- Progress tracking
- Error handling
"""

import asyncio
import os
import time
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, 
    UserNotMutualContactError,
    UserPrivacyRestrictedError,
    UsernameNotOccupiedError,
    RPCError
)
from telethon.tl.types import User

# Configuration - Get these from https://my.telegram.org/apps
API_ID = input("Enter your API ID: ").strip()
API_HASH = input("Enter your API HASH: ").strip()
SESSION_NAME = "message_sender_session"

# Settings
DELAY_SECONDS = 30  # Delay between messages
DAILY_LIMIT = 50    # Maximum messages per day

class TelegramMessageSender:
    def __init__(self):
        self.client = None
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'start_time': None
        }

    async def connect(self):
        """Initialize and connect the client"""
        self.client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
        await self.client.start()

        if await self.client.is_user_authorized():
            me = await self.client.get_me()
            print(f"\n✅ Logged in as: {me.first_name} (@{me.username})")
            return True
        else:
            print("❌ Authorization failed!")
            return False

    async def disconnect(self):
        """Disconnect the client"""
        if self.client:
            await self.client.disconnect()

    def get_usernames_input(self):
        """Get usernames from user input"""
        print("\n" + "="*50)
        print("ENTER USERNAME(s)")
        print("="*50)
        print("Options:")
        print("1. Enter single username")
        print("2. Enter multiple usernames (comma-separated)")
        print("3. Load from file (usernames.txt)")
        print("="*50)

        choice = input("\nSelect option (1-3): ").strip()
        usernames = []

        if choice == "1":
            username = input("Enter username (without @): ").strip()
            if username:
                usernames.append(username)

        elif choice == "2":
            username_input = input("Enter usernames separated by commas: ").strip()
            usernames = [u.strip().replace("@", "") for u in username_input.split(",") if u.strip()]

        elif choice == "3":
            try:
                with open("usernames.txt", "r") as f:
                    usernames = [line.strip().replace("@", "") for line in f if line.strip()]
                print(f"✅ Loaded {len(usernames)} usernames from file")
            except FileNotFoundError:
                print("❌ usernames.txt not found!")
                return []
        else:
            print("❌ Invalid choice!")
            return []

        # Validate and clean usernames
        cleaned = []
        for username in usernames:
            username = username.strip().replace("@", "")
            if username and username not in cleaned:
                cleaned.append(username)

        return cleaned[:DAILY_LIMIT]  # Enforce daily limit

    async def resolve_username(self, username):
        """Resolve username to user entity"""
        try:
            entity = await self.client.get_entity(username)
            if isinstance(entity, User) and not entity.bot:
                return entity
            return None
        except UsernameNotOccupiedError:
            return None
        except Exception as e:
            return None

    async def send_message_with_delay(self, username, message, index, total):
        """Send message to a single user with delay"""
        print(f"\n[{index}/{total}] Processing @{username}...")

        # Resolve username
        user = await self.resolve_username(username)
        if not user:
            print(f"   ❌ Failed: User @{username} not found or invalid")
            self.stats['failed'] += 1
            return False

        # Check if user is in contacts (optional safety check)
        try:
            # Send the message
            await self.client.send_message(user.id, message)

            # Get current time
            current_time = datetime.now().strftime("%H:%M:%S")

            print(f"   ✅ Success! Message sent to {user.first_name} (@{username}) at {current_time}")
            self.stats['success'] += 1

            # Add delay if not the last message
            if index < total:
                print(f"   ⏳ Waiting {DELAY_SECONDS} seconds before next message...")
                await asyncio.sleep(DELAY_SECONDS)

            return True

        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"   ⚠️  Rate limit hit! Need to wait {wait_time} seconds")
            print(f"   ⏳ Waiting...")
            await asyncio.sleep(wait_time)
            # Retry once after waiting
            try:
                await self.client.send_message(user.id, message)
                print(f"   ✅ Success after waiting!")
                self.stats['success'] += 1
                return True
            except Exception as e2:
                print(f"   ❌ Failed after waiting: {str(e2)}")
                self.stats['failed'] += 1
                return False

        except UserPrivacyRestrictedError:
            print(f"   ❌ Failed: User @{username} has privacy restrictions")
            self.stats['failed'] += 1
            return False

        except UserNotMutualContactError:
            print(f"   ❌ Failed: User @{username} is not a mutual contact")
            self.stats['failed'] += 1
            return False

        except RPCError as e:
            print(f"   ❌ Failed: Telegram error - {str(e)}")
            self.stats['failed'] += 1
            return False

        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            self.stats['failed'] += 1
            return False

    def print_progress_bar(self, current, total, bar_length=40):
        """Print a progress bar"""
        filled = int(bar_length * current // total)
        bar = "█" * filled + "░" * (bar_length - filled)
        percentage = (current / total) * 100
        print(f"\nProgress: [{bar}] {percentage:.1f}% ({current}/{total})")

    def print_final_stats(self):
        """Print final statistics"""
        duration = time.time() - self.stats['start_time']
        print("\n" + "="*50)
        print("FINAL STATISTICS")
        print("="*50)
        print(f"Total Messages:    {self.stats['total']}")
        print(f"Successful:        {self.stats['success']} ✅")
        print(f"Failed:            {self.stats['failed']} ❌")
        print(f"Success Rate:      {(self.stats['success']/self.stats['total']*100):.1f}%")
        print(f"Duration:          {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"Average per msg:   {duration/self.stats['total']:.1f} seconds")
        print("="*50)

    async def run(self):
        """Main execution flow"""
        print("\n" + "="*50)
        print("TELEGRAM MESSAGE SENDER")
        print("="*50)
        print("⚠️  WARNING: Use responsibly to avoid account restrictions!")
        print(f"⚙️  Settings: {DAILY_LIMIT} max/day, {DELAY_SECONDS}s delay between messages")
        print("="*50)

        # Connect to Telegram
        if not await self.connect():
            return

        try:
            # Get message from user
            print("\n" + "="*50)
            print("MESSAGE CONTENT")
            print("="*50)
            message = input("\nEnter the message to send:\n> ").strip()

            if not message:
                print("❌ Message cannot be empty!")
                return

            # Confirm message
            print("\n" + "-"*50)
            print("Message preview:")
            print(f'"{message}"')
            print("-"*50)
            confirm = input("\nProceed with this message? (yes/no): ").strip().lower()

            if confirm not in ['yes', 'y']:
                print("❌ Cancelled by user")
                return

            # Get usernames
            usernames = self.get_usernames_input()

            if not usernames:
                print("❌ No valid usernames provided!")
                return

            if len(usernames) > DAILY_LIMIT:
                print(f"⚠️  Limiting to {DAILY_LIMIT} usernames (daily limit)")
                usernames = usernames[:DAILY_LIMIT]

            # Confirm recipients
            print(f"\n📋 Ready to send to {len(usernames)} user(s):")
            for i, username in enumerate(usernames, 1):
                print(f"   {i}. @{username}")

            confirm = input(f"\nSend message to these {len(usernames)} users? (yes/no): ").strip().lower()

            if confirm not in ['yes', 'y']:
                print("❌ Cancelled by user")
                return

            # Start sending
            self.stats['total'] = len(usernames)
            self.stats['start_time'] = time.time()

            print("\n" + "="*50)
            print("SENDING MESSAGES")
            print("="*50)

            # Process each username
            for i, username in enumerate(usernames, 1):
                await self.send_message_with_delay(username, message, i, len(usernames))
                self.print_progress_bar(i, len(usernames))

            # Print final stats
            self.print_final_stats()

            print("\n✅ Process completed!")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            if self.stats['total'] > 0:
                self.print_final_stats()
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
        finally:
            await self.disconnect()
            print("\n👋 Disconnected from Telegram")


def create_requirements_file():
    """Create requirements.txt"""
    with open("requirements.txt", "w") as f:
        f.write("telethon>=1.28.5\n")
    print("✅ Created requirements.txt")


def create_usernames_template():
    """Create template file for usernames"""
    if not os.path.exists("usernames.txt"):
        with open("usernames.txt", "w") as f:
            f.write("# Add one username per line (without @)\n")
            f.write("# Example:\n")
            f.write("username1\n")
            f.write("username2\n")
            f.write("username3\n")
        print("✅ Created usernames.txt template")


if __name__ == "__main__":
    # Create helper files
    create_requirements_file()
    create_usernames_template()

    # Run the sender
    sender = TelegramMessageSender()
    asyncio.run(sender.run())
