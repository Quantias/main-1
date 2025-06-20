from telethon import TelegramClient, events
import asyncio
import os
import random
from datetime import datetime, timedelta
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction
from telethon.tl.functions.contacts import BlockRequest
from telethon.errors import FloodWaitError, ChannelPrivateError
from collections import defaultdict

api_id = 20363060
api_hash = '97b41b4af4696c29091e31326bc2bd50'
client = TelegramClient('user', api_id, api_hash)

SENT_USERS_FILE = 'sent_users.txt'
FAILED_USERS_FILE = 'failed_users.txt'
SPAM_LOG_FILE = 'spam_log.txt'
BLOCKED_USERS_FILE = 'blocked_users.txt'
RETRY_LOG_FILE = 'retry_log.txt'
INITIAL_SENT_FILE = 'initial_sent_chats.txt'
SECONDARY_CHECKED_FILE = 'secondary_checked_chats.txt'

SPAM_COUNTS = defaultdict(int)
WARNED_USERS = set()
ready_to_respond = False
MAX_RETRIES = 1
RETRY_DELAY = 60
DELAY_BETWEEN_USERS = 20
MAX_SENDER_RETRIES = 3
SECONDARY_DELAY_BETWEEN_USERS = 2
INITIAL_DELAY_BETWEEN_CHATS = 0
REPLY_INTERVAL = timedelta(days=200)

processing_queue = asyncio.Queue()
last_replied = {}

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

def load_initial_sent_chats():
    if not os.path.exists(INITIAL_SENT_FILE):
        return set()
    with open(INITIAL_SENT_FILE, 'r') as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

def save_initial_sent_chat(chat_id):
    with open(INITIAL_SENT_FILE, 'a') as f:
        f.write(f"{chat_id}\n")

def load_secondary_checked_chats():
    if not os.path.exists(SECONDARY_CHECKED_FILE):
        return set()
    with open(SECONDARY_CHECKED_FILE, 'r') as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

def save_secondary_checked_chat(chat_id):
    with open(SECONDARY_CHECKED_FILE, 'a') as f:
        f.write(f"{chat_id}\n")

sent_users = load_sent_users()

async def safe_send_message(chat_id, message, parse_mode=None, link_preview=False):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            await client.send_message(chat_id, message, parse_mode=parse_mode, link_preview=link_preview)
            return True
        except FloodWaitError as e:
            print(f"[⏳] FloodWait: ждём {e.seconds} сек (chat_id={chat_id})")
            await asyncio.sleep(e.seconds)
        except Exception as ex:
            print(f"[❌] Ошибка при отправке сообщения в чат {chat_id}: {ex}")
            await asyncio.sleep(RETRY_DELAY)
            retries += 1
    return False

async def get_event_sender(obj):
    for _ in range(1, MAX_SENDER_RETRIES + 1):
        try:
            if hasattr(obj, "get_sender"):
                sender = await obj.get_sender()
            else:
                sender = await client.get_entity(obj.sender_id)
            if sender is not None:
                return sender
        except Exception:
            pass
        await asyncio.sleep(2)
    return None

async def process_user(obj):
    try:
        sender = await get_event_sender(obj)
        if sender is None:
            print(f"[❌] sender is None — попытки исчерпаны для чата ID {getattr(obj, 'chat_id', getattr(obj, 'peer_id', 'N/A'))}")
            return

        user_id = sender.id
        username = sender.username if sender.username else "None"

        if user_id == 777000:
            return

        now = datetime.now()
        if user_id in last_replied and now - last_replied[user_id] < REPLY_INTERVAL:
            return
        last_replied[user_id] = now

        SPAM_COUNTS[user_id] += 1

        if SPAM_COUNTS[user_id] == 150 and user_id not in WARNED_USERS:
            await obj.respond("Пожалуйста, не спамь. Следующиее сообщение и я тебя заблокирую 🥺")
            WARNED_USERS.add(user_id)
            with open(SPAM_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f'⚠️ Варн нахуй: {username} (ID: {user_id})\n')
            return

        if user_id in WARNED_USERS and SPAM_COUNTS[user_id] > 151:
            await obj.respond("Ты продолжаешь спамить, отдохни в бане)")
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

        await client(SetTypingRequest(obj.chat_id, SendMessageTypingAction()))
        await asyncio.sleep(random.uniform(5, 7))

        await safe_send_message(obj.chat_id, "Привет, если ты за подарком — щас скину кое-что (быстро выполнишь — сразу дам подарок) ❤️")
        await asyncio.sleep(random.uniform(5, 7))

        await safe_send_message(
            obj.chat_id,
            "**Задание 1 😊**\n\n"
            "Зайди в бота, выполни одно задание и нажми на \"Проверить ✅\" → "
            "[жмяк](https://t.me/StarsovEarnBot?start=xVh5ZASi3)\n\n"
            "Отправь скрин подписки на каналы ❤️",
            parse_mode='md',
            link_preview=False
        )

        await asyncio.sleep(random.uniform(5, 7))

        await safe_send_message(
            obj.chat_id,
            "**Задание 2 😊**\n\n"
            "Зайди по ссылке → [тык](https://www.tiktok.com/discover/%D1%82%D0%B3-%D0%BF%D0%BE%D0%B4%D0%B0%D1%80%D0%BA%D0%B8)\n"
            "и пиши под 20 видео текст 👇\n\n"
            "`@Crylinge кому звёздочек?)`\n"
            "*👆 Нажми чтобы скопировать*\n\n"
            "❗ ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:\n"
            "1. ЛАЙКАЙ СВОИ КОММЕНТАРИИ\n\n"
            "2. НАПИШИ 20 ТЕКСТОВ *(1 текст на 1 видео)* И ОТПРАВЬ СКРИНЫ КАЖДОГО ТЕКСТА\n\n"
            "3. ЛАЙКАЙ **ВСЕ** ТЕКСТЫ ОТ ДРУГИХ ЛЮДЕЙ С НИКОМ Crylinge\n"
            "*(Соблюдай правила,если увижу на скрине где хотя бы один коммент не лайкнут - подарка не будет)*",
            parse_mode='md',
            link_preview=False
        )

        await asyncio.sleep(random.uniform(5, 7))

        await safe_send_message(
            obj.chat_id,
            "Обязательно пришли скрины ВСЕХ выполненных условий выше 🙏\n"
            "Без подтверждения не смогу выдать подарок 😔",
            parse_mode='md',
            link_preview=False
        )

        await asyncio.sleep(DELAY_BETWEEN_USERS)

    except Exception as e:
        user_id = sender.id if sender else "None"
        username = sender.username if sender and sender.username else "None"
        with open(RETRY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"⏳ Повторная попытка — Username: {username}, ID: {user_id}, Причина: {str(e)}\n")

async def handler(event):
    await processing_queue.put(event)

async def queue_worker():
    global ready_to_respond
    while True:
        obj = await processing_queue.get()
        while not ready_to_respond:
            await asyncio.sleep(0.5)
        await process_user(obj)
        processing_queue.task_done()

async def iter_messages_safe(chat_id, limit=50, min_id=None):
    try:
        return [m async for m in client.iter_messages(chat_id, limit=limit, min_id=min_id)]
    except Exception:
        return []

async def initial_greeting_check():
    me = await client.get_me()
    already_sent = load_initial_sent_chats()
    checked_chat_ids = set()
    count = 0

    print("🔄 Запускаю проверку на первичные приветствия...")

    async for dialog in client.iter_dialogs():
        chat_id = dialog.id

        if chat_id == 777000 or chat_id in checked_chat_ids or chat_id in already_sent or chat_id in sent_users:
            continue

        checked_chat_ids.add(chat_id)
        count += 1

        print(f"Проверяю чат №{count} (ID {chat_id})")

        try:
            msgs = await asyncio.wait_for(iter_messages_safe(chat_id, limit=150), timeout=10)
            if any(m.sender_id == me.id for m in msgs):
                save_initial_sent_chat(chat_id)
                continue
            try:
                await asyncio.sleep(random.uniform(7, 15))
                await client.send_message(chat_id, "Приветствую, это сообщение от автоответчика. Если вы за звёздами отправьте 1 в чат.")
                save_initial_sent_chat(chat_id)
            except Exception:
                pass
        except asyncio.TimeoutError:
            print(f"⏭️ Чат {chat_id} пропущен из-за таймаута")

        await asyncio.sleep(INITIAL_DELAY_BETWEEN_CHATS)

    print("✅ Проверка первичных приветствий завершена!")

async def run_secondary_autoresponder():
    me = await client.get_me()
    checked_secondary = load_secondary_checked_chats()
    print("🔄 Второстепенный автоответчик запущен...")
    count = 0
    try:
        async for dialog in client.iter_dialogs():
            chat_id = dialog.id
            if chat_id == 777000 or chat_id in checked_secondary:
                continue

            try:
                last_initial = None
                try:
                    msgs = await asyncio.wait_for(iter_messages_safe(chat_id, limit=150), timeout=10)
                except asyncio.TimeoutError:
                    print(f"⏭️ Чат {chat_id} пропущен из-за таймаута")
                    continue

                for m in msgs:
                    if m.sender_id == me.id and m.text and "Приветствую" in m.text and "автоответчика" in m.text:
                        last_initial = m.id
                        break

                if last_initial:
                    try:
                        msgs2 = await asyncio.wait_for(iter_messages_safe(chat_id, min_id=last_initial), timeout=10)
                    except asyncio.TimeoutError:
                        print(f"⏭️ Чат {chat_id} пропущен из-за таймаута (вторичный проход)")
                        continue

                    for m in msgs2:
                        if m.sender_id != me.id:
                            sender_id = m.sender_id
                            if sender_id in sent_users:
                                print(f"⏭️ Пользователь ID {sender_id} уже получил основное сообщение — пропускаем")
                                break
                            print(f"✅ Сообщение от пользователя ID {sender_id} после автоответа — ставим в очередь")
                            await asyncio.sleep(random.uniform(5, 10))
                            await processing_queue.put(m)
                            count += 1
                            await asyncio.sleep(SECONDARY_DELAY_BETWEEN_USERS)
                            break

                save_secondary_checked_chat(chat_id)

            except ChannelPrivateError:
                continue

    except Exception as e:
        print(f"Ошибка в secondary_autoresponder: {e}")

    print(f"✅ Второстепенный автоответчик закончил работу. Обработано {count} чатов.")
    global ready_to_respond
    ready_to_respond = True

async def main():
    await client.start()
    print("By @iwill_mc")
    client.add_event_handler(handler, events.NewMessage(incoming=True))
    client.loop.create_task(queue_worker())
    await initial_greeting_check()
    await run_secondary_autoresponder()
    await client.run_until_disconnected()

client.loop.run_until_complete(main())
