# Telegram Message Sender

A Python script that allows you to send messages from your Telegram account to multiple contacts with automatic delays and progress tracking.

## ⚠️ Important Warnings

1. **Rate Limits**: Telegram has strict anti-spam measures. This script includes a 30-second delay between messages to avoid triggering limits.
2. **Daily Limit**: Maximum 50 messages per day is enforced to protect your account.
3. **Terms of Service**: Only use for legitimate personal purposes. Mass unsolicited messaging may result in account restrictions.
4. **Security**: Your API credentials are sensitive. Never share them or commit them to version control.

## 📋 Prerequisites

1. Python 3.7 or higher
2. A Telegram account
3. API credentials from Telegram

## 🔧 Setup Instructions

### Step 1: Get API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Click on "API development tools"
4. Create a new application:
   - **App title**: `MessageSender` (or any name)
   - **Short name**: `msgsender`
   - **URL**: (optional)
   - **Platform**: Desktop
   - **Description**: Personal messaging tool
5. Copy the `api_id` and `api_hash` values

### Step 2: Install Dependencies

```bash
pip install telethon
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

### Step 3: Run the Script

```bash
python telegram_message_sender.py
```

## 🚀 How to Use

### First Run - Authentication

1. The script will ask for your `API ID` and `API HASH`
2. Enter your phone number (with country code, e.g., +1234567890)
3. Telegram will send you a verification code
4. Enter the code to authenticate
5. A session file will be created for future runs

### Sending Messages

1. **Enter your message** when prompted
2. **Choose input method** for usernames:
   - Option 1: Single username
   - Option 2: Multiple usernames (comma-separated)
   - Option 3: Load from `usernames.txt` file
3. **Review and confirm** the recipients
4. **Watch progress** as messages are sent

### Username File Format (usernames.txt)

```
username1
username2
username3
friend_username
family_member
```

- One username per line
- Do not include the @ symbol
- Lines starting with # are ignored

## 📊 Features

### Progress Tracking
- Real-time progress bar
- Success/failure count
- Timestamp for each message
- Final statistics summary

### Error Handling
- User not found detection
- Privacy restriction handling
- Rate limit automatic recovery
- Connection error management

### Safety Features
- 30-second delay between messages
- Daily limit of 50 messages
- Confirmation prompts
- Session persistence (no re-login needed)

## 📈 Example Output

```
==================================================
TELEGRAM MESSAGE SENDER
==================================================
⚠️  WARNING: Use responsibly to avoid account restrictions!
⚙️  Settings: 50 max/day, 30s delay between messages
==================================================

Please enter your phone (or bot token): +1234567890
Please enter the code you received: 12345
Signed in successfully as John Doe

==================================================
MESSAGE CONTENT
==================================================

Enter the message to send:
> Hello! This is a test message.

--------------------------------------------------
Message preview:
"Hello! This is a test message."
--------------------------------------------------

Proceed with this message? (yes/no): yes

==================================================
ENTER USERNAME(s)
==================================================
Options:
1. Enter single username
2. Enter multiple usernames (comma-separated)
3. Load from file (usernames.txt)
==================================================

Select option (1-3): 2
Enter usernames separated by commas: friend1, friend2, friend3

📋 Ready to send to 3 user(s):
   1. @friend1
   2. @friend2
   3. @friend3

Send message to these 3 users? (yes/no): yes

==================================================
SENDING MESSAGES
==================================================

[1/3] Processing @friend1...
   ✅ Success! Message sent to Friend One (@friend1) at 14:30:15
   ⏳ Waiting 30 seconds before next message...

Progress: [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 33.3% (1/3)

[2/3] Processing @friend2...
   ✅ Success! Message sent to Friend Two (@friend2) at 14:30:45
   ⏳ Waiting 30 seconds before next message...

Progress: [████████████████░░░░░░░░░░░░░░░░░░░░░░░░] 66.7% (2/3)

[3/3] Processing @friend3...
   ✅ Success! Message sent to Friend Three (@friend3) at 14:31:15

Progress: [████████████████████████████████████████] 100.0% (3/3)

==================================================
FINAL STATISTICS
==================================================
Total Messages:    3
Successful:        3 ✅
Failed:            0 ❌
Success Rate:      100.0%
Duration:          60.5 seconds (1.0 minutes)
Average per msg:   20.2 seconds
==================================================

✅ Process completed!

👋 Disconnected from Telegram
```

## 🔒 Security Notes

1. **Session File**: The script creates `message_sender_session.session` - this contains your login session. Keep it secure and don't share it.
2. **API Credentials**: Never hardcode your API ID and HASH in the script. The current version asks for them at runtime.
3. **Two-Factor Authentication**: If you have 2FA enabled, you'll need to enter your password when prompted.

## ⚡ Customization

You can modify these settings in the script:

```python
DELAY_SECONDS = 30    # Change delay between messages
DAILY_LIMIT = 50      # Change daily message limit
```

**Warning**: Reducing delays or increasing limits increases the risk of account restrictions.

## 🐛 Troubleshooting

### "User not found" errors
- Ensure the username is correct (without @)
- The user must have a public username

### "Rate limit" errors
- The script will automatically wait and retry
- If persistent, wait a few hours before trying again

### "Authorization failed"
- Check your API ID and HASH are correct
- Ensure your phone number includes country code

### Session expired
- Delete the `message_sender_session.session` file
- Run the script again to re-authenticate

## 📝 Legal Notice

This tool is for educational and personal use only. You are responsible for complying with Telegram's Terms of Service and applicable laws. The author is not responsible for any misuse or account restrictions.

## 🔄 Updates

To update the script:
1. Backup your `message_sender_session.session` file
2. Download the new version
3. Replace the old script
4. Your session should still work

---

**Created**: March 2026
**Version**: 1.0
**Requires**: Python 3.7+, Telethon 1.28.5+
