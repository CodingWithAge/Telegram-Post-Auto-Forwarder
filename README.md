# 🚀 Telegram Auto Forwarder Bot

A powerful, secure, and user-friendly Telegram bot that enables you to configure and control a multi-account Telethon message forwarder directly from Telegram. Perfect for automating message forwarding between channels, groups, and chats with advanced features like account rotation, scheduling, and comprehensive logging.

## ✨ Features

- 🔐 **Secure Configuration**: All sensitive data stored securely with encryption
- 👥 **Multi-Account Support**: Add multiple Telethon accounts to rotate and avoid rate limits
- 📱 **Telegram-Controlled**: Manage everything via Telegram commands - no manual file editing needed
- 📊 **Real-time Logging**: Separate log bot for activity and error reporting
- ⏰ **Scheduled Forwarding**: Set custom intervals for automatic message forwarding
- 🔄 **Live Management**: Start, stop, pause, and resume forwarding on the fly
- 📤 **Bulk Operations**: Add/remove multiple destination channels easily
- 💾 **Config Import/Export**: Backup and restore your configurations
- 🛡️ **Access Control**: Restrict bot usage to authorized Telegram users only

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Tokens (get from [@BotFather](https://t.me/botfather))

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram-auto-forwarder.git
   cd telegram-auto-forwarder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your tokens:
   ```
   TELEGRAM_BOT_TOKEN=your_main_bot_token_here
   LOG_BOT_API_TOKEN=your_log_bot_token_here
   LOG_BOT_TARGET_CHAT_ID=your_log_bot_chat_id_here
   ```

4. **Set your Telegram User ID**
   - Get your ID from [@userinfobot](https://t.me/userinfobot)
   - Edit `bot.py` and update `ALLOWED_USERS` with your ID

5. **Start the bot**
   ```bash
   python bot.py
   ```

## 📖 Usage

1. Start a chat with your bot on Telegram
2. Send `/start` to initialize and see available commands
3. Add Telethon accounts using `/add_account`
4. Configure source and destination channels
5. Start forwarding with `/start_forwarder`

## 🎮 Commands

### Account Management
- `/add_account <api_id> <api_hash> <session_name>` - Add a Telethon account
- `/remove_account <session_name>` - Remove an account
- `/list_accounts` - Show all configured accounts

### Channel Configuration
- `/set_source <channel>` - Set source channel (username or ID)
- `/add_destination <channel>` - Add destination channel
- `/remove_destination <channel>` - Remove destination channel
- `/list_destinations` - Show all destinations

### Forwarding Control
- `/start_forwarder` - Begin message forwarding
- `/stop_forwarder` - Stop forwarding completely
- `/pause_forwarder` - Pause forwarding (resume later)
- `/resume_forwarder` - Resume paused forwarding
- `/status` - Check current forwarding status

### Advanced Settings
- `/set_interval <minutes>` - Set forwarding interval
- `/show_config` - Display current configuration
- `/reset_config` - Reset all settings
- `/export_config` - Export config file
- `/import_config` - Import config file
- `/set_config <key> <value>` - Advanced config editing

### Utilities
- `/cancel` - Cancel current operation
- `/help` - Show help menu

## 🔧 Configuration

The bot uses encrypted configuration storage. All settings are managed through Telegram commands. Sensitive information like API keys and tokens are stored securely and never exposed in logs or exports.

## 📋 Logging

- Integrated log bot sends real-time activity reports to a separate Telegram chat
- Includes detailed error messages and operation status
- Uses Telegram spoiler formatting for sensitive information
- Configurable log destination chat

## ⚠️ Disclaimer

This bot is for educational and personal use only. Please respect Telegram's Terms of Service and API usage guidelines. The developers are not responsible for any misuse of this software.

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram API wrapper
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [cryptography](https://cryptography.io/) - Encryption library

Made with ❤️ for the Telegram community
