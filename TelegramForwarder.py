import asyncio
import json
import os
from telethon import TelegramClient, events
from telethon.sync import TelegramClient as SyncTelegramClient
from telethon import errors

# BOT Settings
BOT_TOKEN = ""  # Replace with your bot token
OWNER_ID =   # Replace with your Telegram user ID (without quotes)

# User Client Setup
user_client = None
phone_number = None

# Bot Client Setup
bot = TelegramClient('bot_session', api_id="", api_hash="").start(bot_token=BOT_TOKEN)

# Settings storage
settings_file = "settings.json"
settings = {
    "source_chat_id": None,
    "destination_chat_id": None,
    "keywords": [],
    "delay": 5,
    "forwarding": False
}

# Load settings if exists
if os.path.exists(settings_file):
    with open(settings_file, "r") as f:
        settings.update(json.load(f))

async def save_settings():
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=4)

# /start command
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != OWNER_ID:
        return
    await event.reply("Welcome to your Forwarder Bot!\nUse /help to see commands.")

# /help command
@bot.on(events.NewMessage(pattern='/help'))
async def help_cmd(event):
    if event.sender_id != OWNER_ID:
        return
    help_text = """
/login - Login your Telegram account
/list_chats - List all your chats
/set_source <chat_id> - Set source chat
/set_destination <chat_id> - Set destination chat
/set_keywords keyword1,keyword2 - Set keywords (optional)
/set_delay <seconds> - Set forward delay
/start_forwarding - Start forwarding
/stop_forwarding - Stop forwarding
/status - Show current settings
"""
    await event.reply(help_text)

# /login command
@bot.on(events.NewMessage(pattern='/login'))
async def login(event):
    global user_client, phone_number
    if event.sender_id != OWNER_ID:
        return
    if phone_number is None:
        try:
            phone_number = event.text.split(' ', 1)[1]  # Get phone number after '/login'
            await event.reply(f"Sending login code to {phone_number}...")
            async with SyncTelegramClient('user_session', api_id=27866551, api_hash="76057a79a74262e29d6de1e9f41aab0d") as temp_client:
                await temp_client.send_code_request(phone_number)
            await event.reply(f"Code sent to {phone_number}. Please enter the code you received.")
        except IndexError:
            await event.reply("Please send your phone number after the /login command.")
    else:
        await event.reply("You are already in the login process. Please wait for the code to be entered.")

# Listen for /code input to handle code entry
@bot.on(events.NewMessage(pattern='/code'))
async def code_input(event):
    global user_client, phone_number
    if event.sender_id != OWNER_ID:
        return
    if phone_number is None:
        await event.reply("Please use the /login command first.")
        return
    try:
        code = event.text.split(' ', 1)[1]  # Extract the code from the message
        async with SyncTelegramClient('user_session', api_id=27866551, api_hash="76057a79a74262e29d6de1e9f41aab0d") as temp_client:
            await temp_client.sign_in(phone_number, code)
            user_client = temp_client
            await event.reply(f"Login successful for {phone_number}!")
            phone_number = None  # Reset phone number for next login
    except errors.SessionPasswordNeededError:
        await event.reply("Two-step password is enabled. Please provide the password.")
    except Exception as e:
        await event.reply(f"Login failed: {e}")

# /list_chats command
@bot.on(events.NewMessage(pattern='/list_chats'))
async def list_chats(event):
    if event.sender_id != OWNER_ID:
        return
    if not user_client:
        await event.reply("Please /login first.")
        return
    dialogs = await user_client.get_dialogs()
    with open(f'chats.txt', 'w', encoding='utf-8') as f:
        for d in dialogs:
            f.write(f"{d.id} - {d.title}\n")
    await event.reply(file='chats.txt')

# /set_source command
@bot.on(events.NewMessage(pattern='/set_source'))
async def set_source(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        chat_id = int(event.raw_text.split(" ", 1)[1])
        settings["source_chat_id"] = chat_id
        await save_settings()
        await event.reply(f"Source chat set to {chat_id}")
    except:
        await event.reply("Usage: /set_source <chat_id>")

# /set_destination command
@bot.on(events.NewMessage(pattern='/set_destination'))
async def set_destination(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        chat_id = int(event.raw_text.split(" ", 1)[1])
        settings["destination_chat_id"] = chat_id
        await save_settings()
        await event.reply(f"Destination chat set to {chat_id}")
    except:
        await event.reply("Usage: /set_destination <chat_id>")

# /set_keywords command
@bot.on(events.NewMessage(pattern='/set_keywords'))
async def set_keywords(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        keywords = event.raw_text.split(" ", 1)[1]
        settings["keywords"] = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        await save_settings()
        await event.reply(f"Keywords set to: {', '.join(settings['keywords'])}")
    except:
        await event.reply("Usage: /set_keywords keyword1,keyword2")

# /set_delay command
@bot.on(events.NewMessage(pattern='/set_delay'))
async def set_delay(event):
    if event.sender_id != OWNER_ID:
        return
    try:
        delay = int(event.raw_text.split(" ", 1)[1])
        settings["delay"] = delay
        await save_settings()
        await event.reply(f"Delay set to {delay} seconds")
    except:
        await event.reply("Usage: /set_delay <seconds>")

# /start_forwarding command
@bot.on(events.NewMessage(pattern='/start_forwarding'))
async def start_forwarding(event):
    if event.sender_id != OWNER_ID:
        return
    if not user_client:
        await event.reply("Please /login first.")
        return
    if not settings["source_chat_id"] or not settings["destination_chat_id"]:
        await event.reply("Please set source and destination chats first.")
        return
    if settings["forwarding"]:
        await event.reply("Already forwarding.")
        return

    settings["forwarding"] = True
    await save_settings()
    await event.reply("Started forwarding.")

    asyncio.create_task(forward_messages())

# /stop_forwarding command
@bot.on(events.NewMessage(pattern='/stop_forwarding'))
async def stop_forwarding(event):
    if event.sender_id != OWNER_ID:
        return
    settings["forwarding"] = False
    await save_settings()
    await event.reply("Stopped forwarding.")

# /status command
@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != OWNER_ID:
        return
    msg = f"""
**Forwarding:** {settings['forwarding']}
**Source Chat:** {settings['source_chat_id']}
**Destination Chat:** {settings['destination_chat_id']}
**Keywords:** {', '.join(settings['keywords'])}
**Delay:** {settings['delay']} seconds
"""
    await event.reply(msg)

async def forward_messages():
    last_message_id = 0

    while settings["forwarding"]:
        try:
            messages = await user_client.get_messages(settings["source_chat_id"], min_id=last_message_id)
            messages = list(reversed(messages))

            for msg in messages:
                if not settings["forwarding"]:
                    break

                if settings["keywords"]:
                    if msg.text and any(keyword in msg.text.lower() for keyword in settings["keywords"]):
                        await user_client.send_message(settings["destination_chat_id"], msg.text)
                        await asyncio.sleep(settings["delay"])
                else:
                    if msg.text:
                        await user_client.send_message(settings["destination_chat_id"], msg.text)
                        await asyncio.sleep(settings["delay"])

                last_message_id = max(last_message_id, msg.id)

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(5)

def main():
    print("Bot Started!")
    bot.run_until_disconnected()

if __name__ == "__main__":
    main()
