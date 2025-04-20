from telethon import TelegramClient, events
import asyncio
import os
import random
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction
from telethon.tl.functions.contacts import BlockRequest
from telethon.errors import FloodWaitError
from collections import defaultdict

api_id = 20363060
api_hash = '97b41b4af4696c29091e31326bc2bd50'
client = TelegramClient('user', api_id, api_hash)

SENT_USERS_FILE = 'sent_users.txt'
FAILED_USERS_FILE = 'failed_users.txt'
SPAM_LOG_FILE = 'spam_log.txt'
BLOCKED_USERS_FILE = 'blocked_users.txt'
RETRY_LOG_FILE = 'retry_log.txt'

SPAM_COUNTS = defaultdict(int)
WARNED_USERS = set()

MAX_RETRIES = 1
RETRY_DELAY = 60  # сек
DELAY_BETWEEN_USERS = 20  # ⏱ пауза между пользователями
MAX_SENDER_RETRIES = 3


def load_sent_users():
    users = set()
    if os.path.exists(SENT_USERS_FILE):
        with open(SENT_USERS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.split('. ', 1)[-1].isdigit():
                    users.add(int(line.split('. ', 1)[-1]))
    return users


def get_next_user_number():
    if not os.path.exists(SENT_USERS_FILE):
        return 1
    with open(SENT_USERS_FILE, 'r') as f:
        lines = f.readlines()
    return len(lines) + 1


sent_users = load_sent_users()
processing_queue = asyncio.Queue()


async def safe_send_message(chat_id, message, parse_mode=None, link_preview=False):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            await client.send_message(
                chat_id,
                message,
                parse_mode=parse_mode,
                link_preview=link_preview
            )
            return True
        except FloodWaitError as e:
            print(f"FloodWait: ждём {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Ошибка отправки: {e}, попытка {retries + 1} из {MAX_RETRIES}")
            await asyncio.sleep(RETRY_DELAY)
            retries += 1
    return False


async def get_sender_with_retries(event):
    for attempt in range(1, MAX_SENDER_RETRIES + 1):
        sender = await event.get_sender()
        if sender is not None:
            return sender
        print(f"⚠️ sender is None, попытка {attempt}/{MAX_SENDER_RETRIES}")
        await asyncio.sleep(2)
    return None


async def process_user(event):
    try:
        sender = await get_sender_with_retries(event)
        if sender is None:
            log_retry("Unknown", "None", "sender is None after retries")
            print("❌ Пропущен: не удалось получить отправителя после нескольких попыток")
            return

        user_id = sender.id
        username = sender.username if sender.username else "None"

        SPAM_COUNTS[user_id] += 1

        if SPAM_COUNTS[user_id] == 150 and user_id not in WARNED_USERS:
            await event.respond("Пожалуйста, не спамь. Следующее сообщение — и я тебя заблокирую 🥺")
            WARNED_USERS.add(user_id)
            with open(SPAM_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f'⚠️ Варн нахуй: {username} (ID: {user_id})\n')
            return

        if user_id in WARNED_USERS and SPAM_COUNTS[user_id] > 160:
            await event.respond("Ты продолжаешь спамить, отдохни в бане)")
            await client(BlockRequest(user_id))
            with open(BLOCKED_USERS_FILE, 'a', encoding='utf-8') as f:
                f.write(f'🚫 Вбананен: {username} (ID: {user_id})\n')
            return

        if user_id in sent_users:
            return

        sent_users.add(user_id)
        number = get_next_user_number()
        with open(SENT_USERS_FILE, 'a') as f:
            f.write(f'{number}. {user_id}\n')

        await client(SetTypingRequest(event.chat_id, SendMessageTypingAction()))
        await asyncio.sleep(random.uniform(6, 8))

        await safe_send_message(
            event.chat_id,
            "Привет, если ты за подарком — щас скину кое-что (быстро выполнишь — сразу дам подарок) ❤️"
        )

        await asyncio.sleep(random.uniform(5, 7))

        await safe_send_message(
            event.chat_id,
            (
                "**Задание 1 😊**\n\n"
                "Зайди в бота, выполни одно задание и нажми на \"Проверить ✅\" → "
                "[жмяк](https://t.me/StarsovEarnBot?start=xVh5ZASi3)\n\n"
                "Отправь скрин подписки на каналы ❤️"
            ),
            parse_mode='md',
            link_preview=False
        )

        await asyncio.sleep(random.uniform(5, 7))

        await safe_send_message(
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
                "3. ЛАЙКАЙ **ВСЕ** ТЕКСТЫ ОТ ДРУГИХ ЛЮДЕЙ С НИКОМ Crylinge\n"
                "*(если увижу на скрине где хотя бы один коммент не лайкнут - подарка не будет)*\n\n"
            ),
            parse_mode='md',
            link_preview=False
        )

        await asyncio.sleep(DELAY_BETWEEN_USERS)

    except Exception as e:
        sender = await event.get_sender()
        user_id = sender.id if sender else "None"
        username = sender.username if sender and sender.username else "None"
        log_retry(username, user_id, str(e))
        print(f"❌ Ошибка в обработке пользователя: {e}")


def log_retry(username, user_id, reason):
    with open(RETRY_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"⏳ Повторная попытка — Username: {username}, ID: {user_id}, Причина: {reason}\n")


@client.on(events.NewMessage(incoming=True))
async def handler(event):
    await processing_queue.put(event)


async def queue_worker():
    while True:
        event = await processing_queue.get()
        await process_user(event)
        processing_queue.task_done()


client.start()
print("By @unmentionned")
client.loop.create_task(queue_worker())
client.run_until_disconnected()
