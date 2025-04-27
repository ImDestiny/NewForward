import asyncio
import json
import os
from telethon import TelegramClient, events
from telethon.sync import TelegramClient as SyncTelegramClient
from telethon.sessions import StringSession
from telethon import errors

# BOT Settings
BOT_TOKEN = "7775154408:AAGfT04KJXR5jtOyTEMtrdNWstQy3rF3SzE"
OWNER_ID = 5437233066   # <- Only your Telegram ID can control the bot

# Bot Client
bot = TelegramClient('bot_session', api_id=27866551, api_hash="76057a79a74262e29d6de1e9f41aab0d").start(bot_token=BOT_TOKEN)

# User Client (for forwarding)
user_client = None
login_waiting_for_code = False

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


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != OWNER_ID:
        return
    await event.reply("Welcome to your Forwarder Bot!\nUse /help to see commands.")


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


@bot.on(events.NewMessage(pattern='/login'))
async def login(event):
    global user_client, login_waiting_for_code
    if event.sender_id != OWNER_ID:
        return
    if login_waiting_for_code:
        await event.reply("You are already in the login process. Please enter the code.")
        return
    login_waiting_for_code = True
    await event.reply("Starting login... Please send your phone number.")

    @bot.on(events.NewMessage(func=lambda e: e.sender_id == OWNER_ID and login_waiting_for_code))
    async def phone_handler(event):
        global user_client, login_waiting_for_code
        phone = event.text.strip()
        await event.reply(f"Sending login code to {phone}...")

        async with SyncTelegramClient('user_session', api_id=YOUR_API_ID, api_hash="YOUR_API_HASH") as temp_client:
            await temp_client.send_code_request(phone)
            await event.reply(f"Please enter the code you received.")

            # Wait for the code
            @bot.on(events.NewMessage(func=lambda e: e.sender_id == OWNER_ID and login_waiting_for_code))
            async def code_handler(event):
                code = event.text.strip()
                try:
                    await temp_client.sign_in(phone, code)
                    await event.reply("Login successful!")
                    login_waiting_for_code = False
                    user_client = TelegramClient('user_session', api_id=YOUR_API_ID, api_hash="YOUR_API_HASH")
                    await user_client.start()
                except errors.SessionPasswordNeededError:
                    pw = input("Two-step password enabled. Enter your password: ")
                    await temp_client.sign_in(password=pw)
                    await event.reply("Logged in successfully!")
                except Exception as e:
                    await event.reply(f"Login failed: {e}")
                    login_waiting_for_code = False


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


@bot.on(events.NewMessage(pattern='/stop_forwarding'))
async def stop_forwarding(event):
    if event.sender_id != OWNER_ID:
        return
    settings["forwarding"] = False
    await save_settings()
    await event.reply("Stopped forwarding.")


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
