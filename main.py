import logging
import os
import aiosqlite
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from asyncio import sleep

# --- 1. Xavfsizlik: Atrof-muhit o'zgaruvchilaridan o'qish ---
try:
    API_TOKEN = os.environ['BOT_TOKEN']
    # ADMIN_ID ni int turiga o'tkazish
    ADMIN_ID = int(os.environ['ADMIN_ID']) 
except KeyError:
    print("XATO: BOT_TOKEN yoki ADMIN_ID atrof-muhit o'zgaruvchisi topilmadi!")
    exit(1)

# --- Konfiguratsiya ---
DATABASE_NAME = 'bot_users.db'

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher obyektlari
storage = MemoryStorage() # FSM uchun
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# --- FSM Holatlari: Ommaviy Xabar Yuborish uchun ---
class BroadcastState(StatesGroup):
    waiting_for_message = State()

# --- 2. Ma'lumotlar Bazasini Boshqarish ---

async def init_db():
    """Ma'lumotlar bazasini yaratish yoki ulash."""
    db = await aiosqlite.connect(DATABASE_NAME)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()
    return db

async def add_user(user_id, username):
    """Yangi foydalanuvchini bazaga qo'shish."""
    db = await aiosqlite.connect(DATABASE_NAME)
    try:
        await db.execute("INSERT INTO users (user_id, username) VALUES (?, ?) ON CONFLICT(user_id) DO NOTHING", 
                         (user_id, username))
        await db.commit()
    except Exception as e:
        logging.error(f"Foydalanuvchini qo'shishda xato: {e}")
    finally:
        await db.close()

async def get_all_users():
    """Barcha foydalanuvchilar ID'sini olish."""
    db = await aiosqlite.connect(DATABASE_NAME)
    cursor = await db.execute("SELECT user_id FROM users")
    users = [row[0] for row in await cursor.fetchall()]
    await db.close()
    return users

# --- 3. Asosiy Handlerlar ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    # Foydalanuvchi ID ni saqlash (DB ga qo'shish)
    await add_user(message.from_user.id, message.from_user.username)
    
    # Asosiy tugmalar (ReplyKeyboardMarkup)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📢 Reklama xizmati")
    
    # Agar admin bo'lsa, admin tugmasini ham qo'shamiz
    if message.from_user.id == ADMIN_ID:
        keyboard.add("/admin")
        
    await message.reply(
        "👋 Assalomu alaykum! Men ID'ni aniqlovchi botman. Siz yuborgan har qanday xabar, rasm yoki faylning ID'sini aniqlay olaman.\n\n"
        "**Bu mutlaqo bepul xizmat!**", 
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(commands=['admin'], user_id=ADMIN_ID)
async def admin_panel(message: types.Message):
    """Admin panelini ochish."""
    admin_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    admin_kb.add("📊 Statistika", "📤 Xabar yuborish")
    admin_kb.add("👤 Foydalanuvchi paneliga qaytish")
    
    await message.reply("👨‍💻 **Admin paneli:** Kerakli tugmani tanlang.", reply_markup=admin_kb, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(text='👤 Foydalanuvchi paneliga qaytish', user_id=ADMIN_ID)
async def return_to_user_panel(message: types.Message):
    """Adminni oddiy panelga qaytarish."""
    user_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    user_kb.add("📢 Reklama xizmati")
    await message.reply("👤 **Foydalanuvchi paneliga qaytdingiz.**", reply_markup=user_kb, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(text='📢 Reklama xizmati')
async def show_advertising(message: types.Message):
    """Reklama taklifini ko'rsatish."""
    # Inline tugma yaratish
    # url='tg://user?id=ADMIN_ID' orqali admin profiliga bog'lanish
    admin_link_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text="👨‍💻 Admin bilan bog'lanish", 
            url=f'tg://user?id={ADMIN_ID}'
        )
    )

    await message.reply(
        "📢 **REKLAMA XIZMATI**\n\n"
        "Ushbu bot orqali minglab faol foydalanuvchilarga o'z reklamangizni tarqatishingiz mumkin. Bot statistikasi doimiy oshib bormoqda!\n\n"
        "**Batafsil ma'lumot va narxlar uchun admin bilan bog'laning.**",
        reply_markup=admin_link_kb,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(text='📊 Statistika', user_id=ADMIN_ID)
async def show_stats(message: types.Message):
    """Foydalanuvchilar sonini ko'rsatish."""
    all_users = await get_all_users()
    user_count = len(all_users)
    
    await message.reply(
        f"📈 **Bot Statistikasi**\n\n"
        f"**👥 Umumiy faol foydalanuvchilar soni:** `{user_count}` ta",
        parse_mode=ParseMode.MARKDOWN
    )

# --- 4. Ommaviy Xabar Yuborish Mantiqi (FSM yordamida) ---

@dp.message_handler(text='📤 Xabar yuborish', user_id=ADMIN_ID)
async def start_broadcast(message: types.Message):
    """Ommaviy xabar yuborish rejimini ishga tushirish."""
    await message.reply("📤 **Ommaviy xabar yuborish rejimi.**\n\n"
                        "Endi yubormoqchi bo'lgan xabaringizni (matn, rasm, fayl, video va h.k.) yuboring. Tarqatishni bekor qilish uchun /cancel buyrug'ini yuboring.",
                        reply_markup=types.ReplyKeyboardRemove())
    
    await BroadcastState.waiting_for_message.set()

@dp.message_handler(state=BroadcastState.waiting_for_message, commands='cancel')
async def cancel_broadcast(message: types.Message, state: FSMContext):
    """Ommaviy xabar yuborishni bekor qilish."""
    await state.finish()
    await admin_panel(message) # Admin paneliga qaytarish
    await message.reply("Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=BroadcastState.waiting_for_message, content_types=types.ContentType.ANY)
async def process_broadcast(message: types.Message, state: FSMContext):
    """Barcha foydalanuvchilarga xabarni tarqatish."""
    await state.finish() # FSM rejimini tugatish
    
    await message.reply("Tarqatish boshlandi. Natija haqida xabar beraman...", reply_markup=types.ReplyKeyboardRemove())
    
    all_users = await get_all_users()
    success_count = 0
    
    for user_id in all_users:
        try:
            # Xabarni barcha foydalanuvchilarga nusxalash (copy_message orqali)
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success_count += 1
            # Telegram API limitlariga tushmaslik uchun kechikish
            await sleep(0.05) 
        except Exception as e:
            # Foydalanuvchi botni bloklagan bo'lishi mumkin
            logging.error(f"Xabar yuborishda xato, ID {user_id}: {e}")
            pass
            
    await admin_panel(message) # Admin paneliga qaytarish

    await bot.send_message(
        ADMIN_ID,
        f"✅ **Tarqatish yakunlandi!**\n"
        f"**👥 Umumiy foydalanuvchilar:** {len(all_users)}\n"
        f"**📤 Muvaffaqiyatli yuborildi:** {success_count}\n"
        f"**❌ Muvaffaqiyatsiz (bloklangan):** {len(all_users) - success_count}",
        parse_mode=ParseMode.MARKDOWN
    )

# --- 5. Fayl/Xabar ID ni Aniqlash (Oxirgi Handler) ---

@dp.message_handler(content_types=types.ContentType.ANY)
async def get_ids(message: types.Message):
    """Foydalanuvchi va fayl ID'larini aniqlash."""
    # Foydalanuvchi ID ni saqlash (agar /start bosmagan bo'lsa ham)
    await add_user(message.from_user.id, message.from_user.username)
    
    response_text = f"👤 **Sizning (foydalanuvchi) ID'ingiz:** `{message.from_user.id}`\n\n"
    
    file_id = None
    
    # Matn
    if message.text:
        response_text += "💬 **Matn xabarlarining o'ziga xos ID'si bo'lmaydi.**"
    
    # Rasmlar, hujjatlar va boshqalar uchun ID ni topish
    elif message.photo:
        # Eng yuqori sifatli rasmni olish
        file_id = message.photo[-1].file_id 
        response_text += f"🖼️ **Rasm (photo) ID:** `{file_id}`"
    
    elif message.document:
        file_id = message.document.file_id
        response_text += f"📄 **Hujjat (document) ID:** `{file_id}`"
        
    elif message.sticker:
        file_id = message.sticker.file_id
        response_text += f"🎭 **Stiker (sticker) ID:** `{file_id}`"

    elif message.video:
        file_id = message.video.file_id
        response_text += f"🎥 **Video ID:** `{file_id}`"
    
    elif message.audio:
        file_id = message.audio.file_id
        response_text += f"🎶 **Audio ID:** `{file_id}`"
    
    else:
        # Boshqa noma'lum turlar uchun umumiy tekshiruv
        try:
             # Agar biror obyektda file_id bo'lsa
             obj = getattr(message, message.content_type)
             if obj and hasattr(obj, 'file_id'):
                 file_id = obj.file_id
                 response_text += f"💾 **{message.content_type.capitalize()} ID:** `{file_id}`"
             else:
                 response_text += "🤷 **Uzr, bu turdagi kontent uchun fayl ID topilmadi.**"
        except Exception:
             response_text += "🤷 **Uzr, bu turdagi kontent uchun fayl ID topilmadi.**"


    # ID ni nima qilish mumkinligi haqida ma'lumot
    if file_id or message.text:
        response_text += (
            "\n\n**ID'ni nima qilish mumkin?**\n"
            "* **Foydalanuvchi ID** orqali siz shaxsiy chat ochish, admin sifatida ommaviy xabarlar yuborish kabi operatsiyalarni amalga oshirishingiz mumkin.\n"
            "* **Fayl ID** orqali ushbu rasm/hujjatni qayta yuklamasdan bot orqali boshqa chatlarga tezkor yuborishingiz mumkin. Bu Telegram serverida saqlangan kontentga havoladir."
        )

    await message.reply(response_text, parse_mode=ParseMode.MARKDOWN)


# --- Botni ishga tushirish ---
if __name__ == '__main__':
    # Ma'lumotlar bazasini ishga tushirish
    dp.loop.run_until_complete(init_db())
    # Botni ishga tushirish
    executor.start_polling(dp, skip_updates=True)
