import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Bot sozlamalari
BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKEN")  # Bot tokeningizni bu yerga yozing
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))      # O'zingizning Telegram ID'ingizni (son) bu yerga yozing

# Statistikani saqlash uchun sodda usul (ma'lumotlar bot o'chirilganda yo'qoladi)
# Real loyihalarda ma'lumotlar bazasidan (PostgreSQL/SQLite) foydalanish kerak
user_ids = set()

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher obyektlari
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- 1. Bot ishga tushganda yoki xabar kelganda foydalanuvchi ID ni saqlash ---
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    # Foydalanuvchi ID ni saqlash
    user_ids.add(message.from_user.id)
    
    # Asosiy tugmalar (ReplyKeyboardMarkup)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Reklama xizmati")
    
    await message.reply(
        "Assalomu alaykum! Men ID'ni aniqlovchi botman. Siz yuborgan har qanday xabar, rasm yoki faylning ID'sini aniqlay olaman.\n\n"
        "**Bu mutlaqo bepul xizmat!**", 
        reply_markup=keyboard
    )

# --- 2. Foydalanuvchi va Fayl ID aniqlash ---
@dp.message_handler(content_types=types.ContentType.ANY)
async def get_ids(message: types.Message):
    # Foydalanuvchi ID ni saqlash (agar /start bosmagan bo'lsa ham)
    user_ids.add(message.from_user.id)
    
    response_text = f"👤 **Sizning (foydalanuvchi) ID'ingiz:** `{message.from_user.id}`\n\n"
    
    file_id = None
    
    # Matn
    if message.text:
        response_text += "💬 **Yuborgan matn xabaringiz ID'si bo'lmaydi.**"
    
    # Rasm
    elif message.photo:
        file_id = message.photo[-1].file_id # Eng katta rasm versiyasini olish
        response_text += f"🖼️ **Rasm (photo) ID:** `{file_id}`"
    
    # Hujjat (fayl)
    elif message.document:
        file_id = message.document.file_id
        response_text += f"📄 **Hujjat (document) ID:** `{file_id}`"
        
    # Stiker
    elif message.sticker:
        file_id = message.sticker.file_id
        response_text += f"🎭 **Stiker (sticker) ID:** `{file_id}`"

    # Video
    elif message.video:
        file_id = message.video.file_id
        response_text += f"🎥 **Video ID:** `{file_id}`"
        
    # Boshqa turlar (Audio, ovozli xabar, va h.k.)
    elif file_id is None:
         # Agar yuqoridagilarga tushmagan bo'lsa, ContentType.ANY qoladi
         if message.content_type in ('audio', 'voice', 'video_note', 'animation'):
            # audio, voice, video_note, animation kabi turlar uchun mos obyektni topish
            obj = getattr(message, message.content_type)
            if obj:
                file_id = obj.file_id
                response_text += f"💾 **{message.content_type.capitalize()} ID:** `{file_id}`"
         else:
             response_text += "🤷 **Uzr, bu turdagi kontent uchun fayl ID topilmadi.**"
        
    # ID ni nima qilish mumkinligi haqida ma'lumot
    if file_id or message.text:
        response_text += (
            "\n\n**ID'ni nima qilish mumkin?**\n"
            "* **Foydalanuvchi ID** orqali siz shaxsiy chat ochish, ommaviy xabarlar yuborish (admin uchun) yoki xabarlarni bloklash kabi operatsiyalarni amalga oshirishingiz mumkin.\n"
            "* **Fayl ID** orqali ushbu rasm/hujjatni qayta yuklamasdan bot orqali boshqa chatlarga tezkor yuborishingiz mumkin. Bu Telegram serverida saqlangan kontentga havoladir."
        )

    await message.reply(response_text, parse_mode=types.ParseMode.MARKDOWN)

# --- 3. Reklama xizmati tugmasi ---
@dp.message_handler(text='Reklama xizmati')
async def show_advertising(message: types.Message):
    # Inline tugma yaratish
    # url='tg://user?id=YOUR_ADMIN_ID' orqali admin profiliga bog'lanish
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
        parse_mode=types.ParseMode.MARKDOWN
    )

# --- 4. Admin Paneli tugmalari (faqat admin uchun) ---
@dp.message_handler(commands=['admin'], user_id=ADMIN_ID)
async def admin_panel(message: types.Message):
    admin_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    admin_kb.add("📊 Statistika", "📤 Xabar yuborish")
    admin_kb.add("👤 Foydalanuvchi paneliga qaytish")
    
    await message.reply("👨‍💻 **Admin paneli:** Kerakli tugmani tanlang.", reply_markup=admin_kb, parse_mode=types.ParseMode.MARKDOWN)

@dp.message_handler(text='👤 Foydalanuvchi paneliga qaytish', user_id=ADMIN_ID)
async def return_to_user_panel(message: types.Message):
    user_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    user_kb.add("Reklama xizmati")
    await message.reply("👤 **Foydalanuvchi paneliga qaytdingiz.**", reply_markup=user_kb, parse_mode=types.ParseMode.MARKDOWN)


# --- 5. Statistika (faqat admin uchun) ---
@dp.message_handler(text='📊 Statistika', user_id=ADMIN_ID)
async def show_stats(message: types.Message):
    user_count = len(user_ids)
    
    await message.reply(
        f"📈 **Bot Statistikasi**\n\n"
        f"**👥 Umumiy faol foydalanuvchilar soni:** `{user_count}` ta",
        parse_mode=types.ParseMode.MARKDOWN
    )

# --- 6. Ommaviy Xabar Yuborish (faqat admin uchun) ---
# Eslatma: Bu sodda namuna. Katta auditoriyaga xabar yuborishda 
# Telegramning API limitlariga tushmaslik uchun kechikish (sleep) ishlatish kerak.

@dp.message_handler(text='📤 Xabar yuborish', user_id=ADMIN_ID)
async def start_broadcast(message: types.Message):
    await message.reply("📤 **Ommaviy xabar yuborish rejimi.**\n\n"
                        "Endi yubormoqchi bo'lgan xabaringizni (matn, rasm, fayl, video va h.k.) yuboring. Barcha foydalanuvchilarga tarqatiladi.",
                        reply_markup=types.ReplyKeyboardRemove())
    
    # Keyingi xabarni kutish uchun holatni o'rnatish kerak
    # aiogram Finite State Machine (FSM) ishlatiladi, ammo soddalik uchun bu bosqich tushirib qoldirildi.
    # To'liq kodda FSM dan foydalaning.

# --- Botni ishga tushirish ---
if __name__ == '__main__':
    # Eslatma: Real loyihalarda environment variable dan foydalanish tavsiya etiladi.
    executor.start_polling(dp, skip_updates=True)
