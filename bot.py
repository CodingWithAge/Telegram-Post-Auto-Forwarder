
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from telethon import TelegramClient
import os
import sys
import re
import asyncio
from threading import Thread, Event
import json
import tempfile
from telegram.constants import ParseMode
from dotenv import load_dotenv
from config_store import generate_key, save_config, load_config, LOG_BOT_API_TOKEN, LOG_BOT_TARGET_CHAT_ID

from log_bot import TelegramLogBot
# Initialize log bot (global)
log_bot = None
if LOG_BOT_API_TOKEN != "<LOG_BOT_TOKEN_HERE>" and LOG_BOT_TARGET_CHAT_ID != "<LOG_BOT_CHAT_ID_HERE>":
    log_bot = TelegramLogBot(LOG_BOT_API_TOKEN, LOG_BOT_TARGET_CHAT_ID)

def send_log(message: str):
    if log_bot:
        log_bot.send_log(message)

# Simple ANSI color codes for terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_startup_banner():
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}{Colors.BOLD}{' '*20}Flash Strategist Bot{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.YELLOW}{' '*10}A secure Telegram message forwarder bot.{Colors.ENDC}")
    print(f"{Colors.YELLOW}{' '*10}Forward messages between channels and groups using multiple accounts.{Colors.ENDC}")
    print(f"{Colors.MAGENTA}{' '*10}script coded by @authorable / Adrian{Colors.ENDC}")
    print(f"\n{Colors.BOLD}To use:{Colors.ENDC} Start the bot, then open Telegram and type /start to see all setup and control commands. All configuration is done via Telegram chat—no file editing needed!\n")

    send_log("[Startup] Main bot started.")


# Replace with your actual Telegram user IDs
ALLOWED_USERS = {7065157618}

API_ID, API_HASH, SESSION_NAME, SRC, DST = range(5)

forwarder_thread = None
stop_event = Event()
pause_event = Event()
account_index = 0

def is_authorized(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_authorized(user.id):
        if update.message:
            await update.message.reply_text("Access denied. Contact the admin to be whitelisted.")
        return ConversationHandler.END
    if update.message:
        await update.message.reply_text(
            "👋 Welcome to the Telegram Forwarder Config Bot!\n\n"
            "This bot lets you securely configure and control a Telegram message forwarder. "
            "You can set up your API credentials, source and destination channels, and control forwarding directly from Telegram.\n\n"
            "<b>Setup Commands:</b>\n"
            "/start - Begin or update setup\n"
            "/add_account <code>api_id</code> <code>api_hash</code> <code>session_name</code> - Add a forwarder account\n"
            "/remove_account <code>session_name</code> - Remove a forwarder account\n"
            "/list_accounts - List all forwarder accounts\n"
            "/set_source <code>channel</code> - Change the source channel\n"
            "/add_destination <code>channel</code> - Add a destination channel\n"
            "/remove_destination <code>channel</code> - Remove a destination channel\n"
            "/list_destinations - List all destination channels\n"
            "\n<b>Forwarding Controls:</b>\n"
            "/start_forwarder - Start forwarding\n"
            "/stop_forwarder - Stop forwarding\n"
            "/pause_forwarder - Pause forwarding\n"
            "/resume_forwarder - Resume forwarding\n"
            "/status - Show current status\n"
            "\n<b>Advanced Settings:</b>\n"
            "/set_interval <code>minutes</code> - Set forwarding interval\n"
            "\n<b>Configuration:</b>\n"
            "/show_config - Show current config\n"
            "/reset_config - Reset all settings\n"
            "/export_config - Export your config file\n"
            "/import_config - Import a config file (send as document)\n"
            "/cancel - Cancel current operation\n",
            parse_mode="HTML"
        )
    if context.user_data is None:
        context.user_data = {}
    return API_ID

async def set_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is None:
        context.user_data = {}
    if not update.message or not update.message.text or not update.message.text.strip().isdigit():
        if update.message:
            await update.message.reply_text("Please send a valid numeric API ID.")
        return API_ID
    context.user_data['api_id'] = update.message.text.strip()
    if update.message:
        await update.message.reply_text("Send your API Hash:")
    return API_HASH

async def set_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is None:
        context.user_data = {}
    if not update.message or not update.message.text or not re.fullmatch(r"[0-9a-fA-F]{32}", update.message.text.strip()):
        if update.message:
            await update.message.reply_text("Please send a valid 32-character hexadecimal API Hash.")
        return API_HASH
    context.user_data['api_hash'] = update.message.text.strip()
    if update.message:
        await update.message.reply_text("Send a unique session name for this account:")
    return SESSION_NAME

async def set_session_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is None:
        context.user_data = {}
    text = update.message.text if update.message and hasattr(update.message, 'text') and update.message.text is not None else None
    if not text:
        if update.message:
            await update.message.reply_text("Please send a valid session name.")
        return SESSION_NAME
    stripped = text.strip()
    if not stripped:
        if update.message:
            await update.message.reply_text("Please send a valid session name.")
        return SESSION_NAME
    context.user_data['session_name'] = stripped

    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        if update.message:
            await update.message.reply_text("User ID not found. Please try again.")
        return ConversationHandler.END
    config = load_config(user_id)
    accounts = config.get('accounts', [])
    accounts.append({
        'api_id': context.user_data['api_id'],
        'api_hash': context.user_data['api_hash'],
        'session_name': context.user_data['session_name']
    })
    config['accounts'] = accounts
    config['_user_id'] = user_id
    save_config(config)
    if update.message:
        await update.message.reply_text(f"Account {context.user_data['session_name']} added!")
    return ConversationHandler.END


async def set_src(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is None:
        context.user_data = {}
    if not update.message or not update.message.text:
        if update.message:
            await update.message.reply_text("Please send a valid source channel.")
        return SRC
    context.user_data['source_channel'] = update.message.text.strip()
    if update.message:
        await update.message.reply_text("Send destination channel(s), comma separated:")
    return DST

async def set_dst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is None:
        context.user_data = {}
    if not update.message or not update.message.text:
        if update.message:
            await update.message.reply_text("Please send at least one destination channel.")
        return DST
    context.user_data['destination_groups'] = [x.strip() for x in update.message.text.split(',') if x.strip()]
    if not context.user_data['destination_groups']:
        if update.message:
            await update.message.reply_text("Please send at least one destination channel.")
        return DST
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        if update.message:
            await update.message.reply_text("User ID not found. Please try again.")
        return ConversationHandler.END
    context.user_data['_user_id'] = user_id
    save_config(context.user_data)
    if update.message:
        await update.message.reply_text("Configuration saved securely!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def run_forwarder(stop_event: Event, pause_event: Event, user_id: int):
    import asyncio
    import time
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    last_message_id = None
    account_idx = 0

    if not user_id:
        msg = "[ERROR] run_forwarder: user_id not provided. Forwarder will not run."
        print(msg)
        send_log(msg)
        return

    while not stop_event.is_set():
        try:
            config = load_config(user_id)
            accounts = config.get('accounts', [])
            if not accounts:
                msg = "No accounts configured."
                print(msg)
                send_log(msg)
                time.sleep(60)
                continue
            account = accounts[account_idx % len(accounts)]
            api_id = int(account['api_id'])
            api_hash = account['api_hash']
            session_name = account['session_name']
            source_channel = config['source_channel']
            destination_groups = config['destination_groups']
            interval = int(config.get('interval', 60))  # minutes
        except Exception as e:
            msg = f"Error loading configuration: {e}"
            print(msg)
            send_log(msg)
            time.sleep(10)
            continue

        msg = f"[Forwarder] Logging in to account: {session_name} (API ID: {api_id})"
        print(f"\n{msg}\n")
        send_log(msg)
        client = TelegramClient(session_name, api_id, api_hash)

        import random
        async def forward_posts():
            nonlocal last_message_id
            from telethon.tl.patched import MessageService
            # Only forward a single, user-specified message ID from config
            single_message_id = config.get('single_message_id')
            if not single_message_id:
                print("No single_message_id set in config. Nothing to forward.")
                return
            try:
                message = await client.get_messages(source_channel, ids=single_message_id)
            except Exception as e:
                msg = f"Error fetching message {single_message_id}: {e}"
                print(msg)
                send_log(msg)
                return
            # get_messages may return a list if ids is a list, or a single message if ids is a single int/str
            if isinstance(message, list):
                if not message:
                    print(f"Message with ID {single_message_id} not found in source channel.")
                    return
                message = message[0]
            if not message:
                print(f"Message with ID {single_message_id} not found in source channel.")
                return
            if isinstance(message, MessageService):
                print("Cannot forward service messages.")
                return
            if not getattr(message, 'to_id', None) and not getattr(message, 'message', None):
                print("Message is not forwardable.")
                return

            # Get username and API ID for logging
            username = None
            try:
                me = await client.get_me()
                # me can be a User or InputPeerUser; only User has username/first_name/id
                if hasattr(me, 'username') or hasattr(me, 'first_name') or hasattr(me, 'id'):
                    username = getattr(me, 'username', None) or getattr(me, 'first_name', None) or str(getattr(me, 'id', 'unknown'))
                else:
                    # fallback: try to get from dict
                    me_dict = me.to_dict() if hasattr(me, 'to_dict') else {}
                    username = me_dict.get('username') or me_dict.get('first_name') or str(me_dict.get('id', 'unknown'))
                api_id_for_log = getattr(client, 'api_id', 'unknown')
            except Exception:
                username = 'unknown'
                api_id_for_log = 'unknown'

            for group in destination_groups:
                # Uncensored group name
                msg = (
                    f"Forwarding to: {group}\n"
                    f"User: {username}\n"
                    f"API ID: ||{api_id_for_log}||"  # Telegram spoiler formatting
                )
                print(msg)
                send_log(msg)
                try:
                    await client.forward_messages(group, message)
                except Exception as e:
                    err_msg = f"Error forwarding to {group}: {e}"
                    print(err_msg)
                    send_log(err_msg)
                delay = random.uniform(0, 20)
                print(f"Waiting {delay:.2f} seconds before next forward...")
                await asyncio.sleep(delay)
            last_message_id = message.id


        async def scheduler():
            while not stop_event.is_set():
                if pause_event.is_set():
                    await asyncio.sleep(2)
                    continue
                try:
                    await forward_posts()
                    msg = f"[Account: {session_name}] Forwarded posts. Waiting for {interval} minute(s)..."
                    print(msg)
                    send_log(msg)
                except Exception as e:
                    err_msg = f"Error: {e}"
                    print(err_msg)
                    send_log(err_msg)
                for _ in range(interval * 60):
                    if stop_event.is_set() or pause_event.is_set():
                        break
                    await asyncio.sleep(1)

        with client:
            loop.run_until_complete(scheduler())

        account_idx = (account_idx + 1) % len(accounts)

async def start_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global forwarder_thread, stop_event, pause_event
    user = update.effective_user
    if not user or not is_authorized(user.id):
        if update.message:
            await update.message.reply_text("Access denied.")
        return
    if forwarder_thread and forwarder_thread.is_alive():
        if update.message:
            await update.message.reply_text("Forwarder is already running.")
        return
    stop_event.clear()
    pause_event.clear()
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        if update.message:
            await update.message.reply_text("User ID not found. Please try again.")
        return
    forwarder_thread = Thread(target=run_forwarder, args=(stop_event, pause_event, user_id), daemon=True)
    forwarder_thread.start()
    send_log(f"[User {user_id}] Forwarder started.")
    if update.message:
        await update.message.reply_text("Forwarder started.")

async def stop_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_event, forwarder_thread, pause_event
    user = update.effective_user
    if not user or not is_authorized(user.id):
        if update.message:
            await update.message.reply_text("Access denied.")
        return
    if not forwarder_thread or not forwarder_thread.is_alive():
        if update.message:
            await update.message.reply_text("Forwarder is not running.")
        return
    stop_event.set()
    pause_event.clear()
    user_id = update.effective_user.id if update.effective_user else None
    send_log(f"[User {user_id}] Forwarder stopping...")
    if update.message:
        await update.message.reply_text("Forwarder stopping...")

async def set_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_authorized(user.id):
        if update.message:
            await update.message.reply_text("Access denied.")
        return
    if not context.args or len(context.args) < 2:
        if update.message:
            example = '{\n  "accounts": [{"api_id": "123456", "api_hash": "your_api_hash", "session_name": "mysession"}],\n  "source_channel": "@sourcechannel",\n  "destination_groups": ["@dest1", "@dest2"]\n}'
            await update.message.reply_text(
                "<b>Usage:</b> /set_config <code>key</code> <code>value</code>\n"
                "Supported keys: accounts, destination_groups, source_channel.\n"
                "For accounts and destination_groups, provide a JSON list.\n"
                "<b>Example:</b> /set_config accounts '[{\"api_id\": \"123456\", \"api_hash\": \"your_api_hash\", \"session_name\": \"mysession\"}]'\n"
                "<b>Example config:</b>\n<pre>" + example + "</pre>",
                parse_mode="HTML"
            )
        return
    key = context.args[0]
    value = ' '.join(context.args[1:])
    import json
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        if update.message:
            await update.message.reply_text("User ID not found. Please try again.")
        return
    try:
        config = load_config(user_id)
    except FileNotFoundError:
        config = {}
    if key == 'accounts' or key == 'destination_groups':
        try:
            config[key] = json.loads(value)
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Invalid JSON for {key}: {e}")
            return
    else:
        config[key] = value
    config['_user_id'] = user_id
    save_config(config)
    if update.message:
        await update.message.reply_text(f"Config key '{key}' updated.")

async def export_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_authorized(user.id):
        if update.message:
            await update.message.reply_text("❌ Access denied.", parse_mode=ParseMode.MARKDOWN)
        return
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        if update.message:
            await update.message.reply_text("User ID not found. Please try again.")
        return
    try:
        config = load_config(user_id)
        with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.json') as f:
            json.dump(config, f, indent=2)
            f.flush()
            f.seek(0)
            if update.message:
                await update.message.reply_document(document=open(f.name, 'rb'), filename='config.json', caption="🗂️ *Exported config*", parse_mode=ParseMode.MARKDOWN)
        os.unlink(f.name)
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Error exporting config: {e}", parse_mode=ParseMode.MARKDOWN)

async def import_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_authorized(user.id):
        if update.message:
            await update.message.reply_text("❌ Access denied.", parse_mode=ParseMode.MARKDOWN)
        return
    if not update.message or not update.message.document:
        if update.message:
            example_config = '{\n  "accounts": [\n    {\n      "api_id": "123456",\n      "api_hash": "your_api_hash",\n      "session_name": "mysession"\n    }\n  ],\n  "source_channel": "@sourcechannel",\n  "destination_groups": ["@dest1", "@dest2"],\n  "single_message_id": 12345\n}'
            instructions = (
                "To import your configuration, please send a previously exported config file as a document. "
                "\n\n<b>Instructions:</b>\n"
                "1. Export your config from another account or backup using /export_config.\n"
                "2. Send the exported config.json file here as a document.\n"
                "3. Importing will overwrite your current settings.\n\n"
                "<b>Example config file:</b>\n"
                f"<pre>{example_config}</pre>"
            )
            await update.message.reply_text(instructions, parse_mode="HTML")
        return
    file = await update.message.document.get_file()
    content = await file.download_as_bytearray()
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        if update.message:
            await update.message.reply_text("User ID not found. Please try again.")
        return
    try:
        config = json.loads(content.decode())
        config['_user_id'] = user_id
        save_config(config)
        if update.message:
            await update.message.reply_text("✅ Config imported successfully!", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Error importing config: {e}", parse_mode=ParseMode.MARKDOWN)

def main():
    print_startup_banner()
    generate_key()
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set. Please create a .env file with TELEGRAM_BOT_TOKEN=your_token_here")
        sys.exit(1)
    app = Application.builder().token(bot_token).build()
    # Direct handler for /add_account <api_id> <api_hash> <session_name>
    async def add_account_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        args = context.args if context.args else []
        if len(args) == 0:
            if update.message:
                await update.message.reply_text(
                    "<b>Usage:</b> /add_account <code>api_id</code> <code>api_hash</code> <code>session_name</code>\n"
                    "Adds a new Telegram account for forwarding.\n"
                    "- <b>api_id</b>: Your Telegram API ID (numeric)\n"
                    "- <b>api_hash</b>: Your 32-character API hash\n"
                    "- <b>session_name</b>: A unique name for this account\n"
                    "<b>Example:</b> /add_account 123456 0123456789abcdef0123456789abcdef mysession",
                    parse_mode="HTML"
                )
            return
        if len(args) == 3:
            api_id, api_hash, session_name = args
            if not api_id.isdigit():
                if update.message:
                    await update.message.reply_text("API ID must be numeric.")
                return
            if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
                if update.message:
                    await update.message.reply_text("API Hash must be a 32-character hexadecimal string.")
                return
            if not session_name.strip():
                if update.message:
                    await update.message.reply_text("Session name cannot be empty.")
                return
            user_id = update.effective_user.id if update.effective_user else None
            if not user_id:
                if update.message:
                    await update.message.reply_text("User ID not found. Please try again.")
                return
            try:
                config = load_config(user_id)
            except FileNotFoundError:
                config = {}
            accounts = config.get('accounts', [])
            accounts.append({
                'api_id': api_id,
                'api_hash': api_hash,
                'session_name': session_name.strip()
            })
            config['accounts'] = accounts
            config['_user_id'] = user_id
            save_config(config)
            if update.message:
                await update.message.reply_text(f"Account {session_name.strip()} added!")
            return
        else:
            if update.message:
                await update.message.reply_text(
                    "<b>Usage:</b> /add_account <code>api_id</code> <code>api_hash</code> <code>session_name</code>\n"
                    "Adds a new Telegram account for forwarding.\n"
                    "- <b>api_id</b>: Your Telegram API ID (numeric)\n"
                    "- <b>api_hash</b>: Your 32-character API hash\n"
                    "- <b>session_name</b>: A unique name for this account\n"
                    "<b>Example:</b> /add_account 123456 0123456789abcdef0123456789abcdef mysession",
                    parse_mode="HTML"
                )
            return

    setup_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_api_id)],
            API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_api_hash)],
            SRC: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_src)],
            DST: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_dst)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(CommandHandler('add_account', add_account_cmd))
    app.add_handler(setup_conv)

    async def remove_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        if not context.args:
            if update.message:
                await update.message.reply_text(
                    "<b>Usage:</b> /remove_account <code>session_name</code>\n"
                    "Removes a Telegram account from the forwarder.\n"
                    "- <b>session_name</b>: The name of the account session to remove.\n"
                    "<b>Example:</b> /remove_account mysession",
                    parse_mode="HTML"
                )
            return
        session_name = context.args[0].strip() if context.args[0] else ""
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            accounts = config.get('accounts', [])
            new_accounts = [a for a in accounts if a['session_name'] != session_name]
            if len(new_accounts) == len(accounts):
                if update.message:
                    await update.message.reply_text(f"Account {session_name} not found.")
                return
            config['accounts'] = new_accounts
            config['_user_id'] = user_id
            save_config(config)
            if update.message:
                await update.message.reply_text(f"Account {session_name} removed.")
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")

    async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            accounts = config.get('accounts', [])
            if not accounts:
                if update.message:
                    await update.message.reply_text("No accounts configured.")
                return
            msg = (
                "<b>Configured accounts:</b>\n" +
                "\n".join(f"- <b>{a['session_name']}</b> (API ID: <code>{a['api_id']}</code>)" for a in accounts) +
                "\n\n<b>Usage:</b> /list_accounts\nLists all Telegram accounts added for forwarding."
            )
            if update.message:
                await update.message.reply_text(msg, parse_mode="HTML")
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")

    app.add_handler(CommandHandler('remove_account', remove_account))
    app.add_handler(CommandHandler('list_accounts', list_accounts))
    app.add_handler(CommandHandler('start_forwarder', start_forwarder))
    app.add_handler(CommandHandler('stop_forwarder', stop_forwarder))

    async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        if not context.args:
            if update.message:
                await update.message.reply_text(
                    "<b>Usage:</b> /add_destination <code>channel</code>\n"
                    "Adds a destination channel or group to forward messages to.\n"
                    "- <b>channel</b>: The @username or ID of the destination channel/group.\n"
                    "<b>Example:</b> /add_destination @mygroup",
                    parse_mode="HTML"
                )
            return
        channel = context.args[0].strip()
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            dests = config.get('destination_groups', [])
            if channel in dests:
                if update.message:
                    await update.message.reply_text(f"{channel} is already a destination.")
                return
            dests.append(channel)
            config['destination_groups'] = dests
            config['_user_id'] = user_id
            save_config(config)
            if update.message:
                await update.message.reply_text(f"Added {channel} to destination channels.")
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def remove_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        if not context.args:
            if update.message:
                await update.message.reply_text(
                    "<b>Usage:</b> /remove_destination <code>channel</code>\n"
                    "Removes a destination channel or group from the forwarder.\n"
                    "- <b>channel</b>: The @username or ID of the destination channel/group.\n"
                    "<b>Example:</b> /remove_destination @mygroup",
                    parse_mode="HTML"
                )
            return
        channel = context.args[0].strip()
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            dests = config.get('destination_groups', [])
            if channel not in dests:
                if update.message:
                    await update.message.reply_text(f"{channel} is not in destination channels.")
                return
            dests.remove(channel)
            config['destination_groups'] = dests
            config['_user_id'] = user_id
            save_config(config)
            if update.message:
                await update.message.reply_text(f"Removed {channel} from destination channels.")
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def list_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            dests = config.get('destination_groups', [])
            if update.message:
                if dests:
                    await update.message.reply_text(
                        "<b>Destination channels:</b>\n" + "\n".join(f"<code>{d}</code>" for d in dests) +
                        "\n\n<b>Usage:</b> /list_destinations\nLists all destination channels/groups currently set for forwarding.",
                        parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text(
                        "No destination channels set.\n\n<b>Usage:</b> /list_destinations\nLists all destination channels/groups currently set for forwarding.",
                        parse_mode="HTML"
                    )
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def set_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        if not context.args:
            if update.message:
                await update.message.reply_text(
                    "<b>Usage:</b> /set_source <code>channel</code>\n"
                    "Sets the source channel or group to forward messages from.\n"
                    "- <b>channel</b>: The @username or ID of the source channel/group.\n"
                    "<b>Example:</b> /set_source @sourcechannel",
                    parse_mode="HTML"
                )
            return
        channel = context.args[0].strip()
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            config['source_channel'] = channel
            config['_user_id'] = user_id
            save_config(config)
            if update.message:
                await update.message.reply_text(f"Source channel set to {channel}.")
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        if not context.args or not context.args[0].isdigit():
            if update.message:
                await update.message.reply_text(
                    "<b>Usage:</b> /set_interval <code>minutes</code>\n"
                    "Sets the interval (in minutes) between forwarding checks.\n"
                    "- <b>minutes</b>: How often to check for new messages.\n"
                    "<b>Example:</b> /set_interval 10",
                    parse_mode="HTML"
                )
            return
        minutes = int(context.args[0])
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            config['interval'] = minutes
            config['_user_id'] = user_id
            save_config(config)
            if update.message:
                await update.message.reply_text(f"Interval set to {minutes} minute(s).")
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        running = forwarder_thread.is_alive() if forwarder_thread else False
        paused = pause_event.is_set()
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            interval = config.get('interval', 60)
            src = config.get('source_channel', '-')
            dsts = config.get('destination_groups', [])
            msg = (
                f"Forwarder status: {'Running' if running else 'Stopped'}\n"
                f"Paused: {'Yes' if paused else 'No'}\n"
                f"Source: {src}\n"
                f"Destinations: {', '.join(dsts) if dsts else '-'}\n"
                f"Interval: {interval} min"
            )
            if update.message:
                await update.message.reply_text(msg)
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def pause_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        if not forwarder_thread or not forwarder_thread.is_alive():
            if update.message:
                await update.message.reply_text("Forwarder is not running.")
            return
        pause_event.set()
        if update.message:
            await update.message.reply_text("Forwarder paused.")

    async def resume_forwarder(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        if not forwarder_thread or not forwarder_thread.is_alive():
            if update.message:
                await update.message.reply_text("Forwarder is not running.")
            return
        pause_event.clear()
        if update.message:
            await update.message.reply_text("Forwarder resumed.")

    async def show_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            config = load_config(user_id)
            safe_config = {k: v for k, v in config.items() if k not in ('api_id', 'api_hash', '_user_id')}
            msg = '\n'.join(f"{k}: {v}" for k, v in safe_config.items())
            if update.message:
                await update.message.reply_text(
                    f"<b>Current config:</b>\n<pre>{msg}</pre>\n\n<b>Usage:</b> /show_config\nShows your current configuration (excluding sensitive info).",
                    parse_mode="HTML"
                )
        except FileNotFoundError:
            if update.message:
                await update.message.reply_text("No configuration found. Please run /start to set up your bot.")
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def reset_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            if update.message:
                await update.message.reply_text("Access denied.")
            return
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            if update.message:
                await update.message.reply_text("User ID not found. Please try again.")
            return
        try:
            save_config({'_user_id': user_id})
            if update.message:
                await update.message.reply_text(
                    "<b>Config reset.</b>\nAll your settings have been cleared. Please use /start to reconfigure.\n\n<b>Usage:</b> /reset_config\nResets your configuration to default.",
                    parse_mode="HTML"
                )
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"Error: {e}")

    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(
                "<b>Setup Commands:</b>\n"
                "/start - Begin or update setup\n"
                "/add_account <code>api_id</code> <code>api_hash</code> <code>session_name</code> - Add a forwarder account\n"
                "/remove_account <code>session_name</code> - Remove a forwarder account\n"
                "/list_accounts - List all forwarder accounts\n"
                "/set_source <code>channel</code> - Change the source channel\n"
                "/add_destination <code>channel</code> - Add a destination channel\n"
                "/remove_destination <code>channel</code> - Remove a destination channel\n"
                "/list_destinations - List all destination channels\n"
                "\n<b>Forwarding Controls:</b>\n"
                "/start_forwarder - Start forwarding\n"
                "/stop_forwarder - Stop forwarding\n"
                "/pause_forwarder - Pause forwarding\n"
                "/resume_forwarder - Resume forwarding\n"
                "/status - Show current status\n"
                "\n<b>Advanced Settings:</b>\n"
                "/set_interval <code>minutes</code> - Set forwarding interval\n"
                "\n<b>Configuration:</b>\n"
                "/show_config - Show current config\n"
                "/reset_config - Reset all settings\n"
                "/export_config - Export your config file\n"
                "/import_config - Import a config file (send as document)\n"
                "/cancel - Cancel current operation\n",
                parse_mode="HTML"
            )

    app.add_handler(CommandHandler('add_destination', add_destination))
    app.add_handler(CommandHandler('remove_destination', remove_destination))
    app.add_handler(CommandHandler('list_destinations', list_destinations))
    app.add_handler(CommandHandler('set_source', set_source))
    app.add_handler(CommandHandler('set_interval', set_interval))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('pause_forwarder', pause_forwarder))
    app.add_handler(CommandHandler('resume_forwarder', resume_forwarder))
    app.add_handler(CommandHandler('show_config', show_config))
    app.add_handler(CommandHandler('reset_config', reset_config))
    app.add_handler(CommandHandler('help', help_cmd))


    # Register export_config and import_config handlers
    app.add_handler(CommandHandler('export_config', export_config))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, import_config))
    app.add_handler(CommandHandler('import_config', import_config))

    app.run_polling()

if __name__ == '__main__':
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()