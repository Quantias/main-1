from telethon import TelegramClient, events
import asyncio
import os
import random

from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction
from telethon.tl.functions.contacts import BlockRequest
from collections import defaultdict


api_id = 20363060
api_hash = '97b41b4af4696c29091e31326bc2bd50'

client = TelegramClient('user', api_id, api_hash)

SENT_USERS_FILE = 'sent_users.txt'
FAILED_USERS_FILE = 'failed_users.txt'
SPAM_LOG_FILE = 'spam_log.txt'
BLOCKED_USERS_FILE = 'blocked_users.txt'

SPAM_COUNTS = defaultdict(int)
WARNED_USERS = set()

def load_sent_users():
    users = set()
    if os.path.exists(SENT_USERS_FILE):
        with open(SENT_USERS_FILE, 'r') as f:
            lines = f.read().splitlines()
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line.isdigit():
                users.add(int(line))
                cleaned_lines.append(line)
        with open(SENT_USERS_FILE, 'w') as f:
            f.write('\n'.join(cleaned_lines))
    return users

sent_users = load_sent_users()

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return

    sender = await event.get_sender()
    user_id = sender.id
    username = sender.username if sender.username else "None"

    SPAM_COUNTS[user_id] += 1

    if SPAM_COUNTS[user_id] == 15 and user_id not in WARNED_USERS:
        await event.respond("Пожалуйста, не спамь. Следующее сообщение — и я тебя заблокирую 🥺")
        WARNED_USERS.add(user_id)
        with open(SPAM_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'⚠️ Варн нахуй: {username} (ID: {user_id})\n')
        return

    if user_id in WARNED_USERS and SPAM_COUNTS[user_id] > 15:
        await event.respond("Ты продолжаешь спамить,отдохни в бане)")
        await client(BlockRequest(user_id))
        with open(BLOCKED_USERS_FILE, 'a', encoding='utf-8') as f:
            f.write(f'🚫 Вбананен: {username} (ID: {user_id})\n')
        return

    if user_id in sent_users:
        return

    try:
        sent_users.add(user_id)
        with open(SENT_USERS_FILE, 'a') as f:
            f.write(f'{user_id}\n')

        await client(SetTypingRequest(event.chat_id, SendMessageTypingAction()))
        await asyncio.sleep(random.uniform(2.5, 3.5))

        await client.send_message(
            event.chat_id,
            "Привет, если ты за подарком — щас скину кое-что! (быстро выполнишь — сразу дам подарок) ❤️"
        )

        await asyncio.sleep(random.uniform(1.5, 2.5))

        await client.send_message(
            event.chat_id,
            (
                "**Задание 1 😊**\n\n"
                "Зайди в бота, выполни одно задание и нажми на \"Проверить ✅\" → "
                "[жмяк](https://t.me/treasury_official_bot/app?startapp=5094540706)\n\n"
                "Отправь скрин подписки на каналы ❤️"
            ),
            parse_mode='md',
            link_preview=False
        )

        await asyncio.sleep(random.uniform(0.5, 1))

        await client.send_message(
            event.chat_id,
            (
                "**Задание 2 😊**\n\n"
                "Зайди по ссылке → [тык](https://www.tiktok.com/discover/%D1%82%D0%B3-%D0%BF%D0%BE%D0%B4%D0%B0%D1%80%D0%BA%D0%B8)\n"
                "и пиши под 15 видео текст 👇\n\n"
                "`@Crylinge кому звёздочек?)`\n"
                "*👆 Нажми чтобы скопировать*\n\n"
                "❗ ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:\n"
                "1. ЛАЙКАЙ СВОИ КОММЕНТАРИИ\n\n"
                "2. НАПИШИ 15 ТЕКСТОВ *(1 текст на 1 видео)* И ОТПРАВЬ СКРИНЫ КАЖДОГО ТЕКСТА\n\n"
                "3. ЛАЙКАЙ **ВСЕ** ТЕКСТА ОТ ДРУГИХ ЛЮДЕЙ С НИКОМ Crylinge\n"
                "*(если увижу на скрине где хотя бы один коммент не лайкнут - подарка не будет)*\n\n"
            ),
            parse_mode='md',
            link_preview=False
        )

    except Exception as e:
        with open(FAILED_USERS_FILE, 'a', encoding='utf-8') as f:
            f.write(f'Username: {username}, ID: {user_id}, Error: {e}\n')
        print(f"Чёт по хуйне пошло {user_id}: {e}")

client.start()
print("By @unmentionned")
client.run_until_disconnected()