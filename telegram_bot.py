"""
ربات تلگرام برای جمع‌آوری و دسته‌بندی فایل‌ها
نصب: pip install python-telegram-bot httpx[socks]
"""

import os
import shutil
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import httpx

# ──────────────────────────────────────────────
# تنظیمات
# ──────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

CATEGORIES = {
    "مدارک": "مدارک",
    "دانشگاه": "دانشگاه",
    "بانکی": "بانکی",
    "سایر": "سایر",
}

BASE_DIR = "/tmp/فایل‌های_من"

EXTENSION_MAP = {
    "pdf": "مدارک",
    "jpg": "مدارک",
    "jpeg": "مدارک",
    "png": "مدارک",
    "docx": "دانشگاه",
    "doc": "دانشگاه",
    "xlsx": "بانکی",
    "xls": "بانکی",
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def ensure_dirs():
    for cat in CATEGORIES.values():
        os.makedirs(os.path.join(BASE_DIR, cat), exist_ok=True)


def get_suggested_category(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return EXTENSION_MAP.get(ext, "سایر")


def save_file(file_path: str, filename: str, category: str) -> str:
    dest_dir = os.path.join(BASE_DIR, category)
    os.makedirs(dest_dir, exist_ok=True)
    base, ext = os.path.splitext(filename)
    dest_path = os.path.join(dest_dir, filename)
    if os.path.exists(dest_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(dest_dir, f"{base}_{timestamp}{ext}")
    shutil.move(file_path, dest_path)
    return dest_path


def category_keyboard(suggested: str = None):
    buttons = []
    for cat in CATEGORIES.keys():
        label = f"✅ {cat}" if cat == suggested else cat
        buttons.append(InlineKeyboardButton(label, callback_data=f"cat:{cat}"))
    return InlineKeyboardMarkup([buttons[:2], buttons[2:]])


def list_files_text() -> str:
    ensure_dirs()
    lines = ["📁 *فایل‌های ذخیره‌شده:*\n"]
    total = 0
    for cat in CATEGORIES.values():
        folder = os.path.join(BASE_DIR, cat)
        files = os.listdir(folder) if os.path.exists(folder) else []
        files = [f for f in files if os.path.isfile(os.path.join(folder, f))]
        total += len(files)
        if files:
            lines.append(f"📂 *{cat}* ({len(files)} فایل)")
            for f in files[-5:]:
                lines.append(f"  • {f}")
            if len(files) > 5:
                lines.append(f"  _... و {len(files)-5} فایل دیگر_")
            lines.append("")
    if total == 0:
        return "هنوز هیچ فایلی ذخیره نشده."
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 👋\n\n"
        "من ربات مدیریت فایل شما هستم.\n"
        "کافیه هر فایلی (PDF، عکس، Word، Excel و ...) برام بفرستی "
        "تا دسته‌بندی و ذخیره کنم.\n\n"
        "دستورات:\n"
        "/list — نمایش فایل‌های ذخیره‌شده\n"
        "/help — راهنما"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *راهنما*\n\n"
        "1. هر فایلی بفرست → ربات دسته پیشنهاد می‌دهد\n"
        "2. دسته را تأیید یا عوض کن\n"
        "3. فایل ذخیره می‌شود!\n\n"
        "دسته‌بندی‌ها:\n"
        "📄 مدارک — شناسنامه، کارت ملی، گواهی‌ها\n"
        "🎓 دانشگاه — ریزنمره، فرم‌های دانشگاهی\n"
        "🏦 بانکی — صورت‌حساب، چک، فیش\n"
        "📦 سایر — بقیه فایل‌ها\n\n"
        "/list — مشاهده فایل‌ها",
        parse_mode="Markdown",
    )


async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(list_files_text(), parse_mode="Markdown")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_dirs()
    message = update.message

    if message.document:
        tg_file = await message.document.get_file()
        filename = message.document.file_name or f"file_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    elif message.photo:
        tg_file = await message.photo[-1].get_file()
        filename = f"photo_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    elif message.video:
        tg_file = await message.video.get_file()
        filename = message.video.file_name or f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
    elif message.audio:
        tg_file = await message.audio.get_file()
        filename = message.audio.file_name or f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
    else:
        await message.reply_text("این نوع پیام پشتیبانی نمی‌شود.")
        return

    tmp_path = os.path.join("/tmp", filename)
    await tg_file.download_to_drive(tmp_path)

    suggested = get_suggested_category(filename)
    context.user_data["pending_file"] = tmp_path
    context.user_data["pending_filename"] = filename

    await message.reply_text(
        f"✅ فایل دریافت شد: *{filename}*\n\n"
        f"دسته پیشنهادی: *{suggested}*\n"
        "کدام دسته‌بندی مناسب‌تر است؟",
        parse_mode="Markdown",
        reply_markup=category_keyboard(suggested),
    )


async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.replace("cat:", "")
    file_path = context.user_data.get("pending_file")
    filename = context.user_data.get("pending_filename")

    if not file_path or not os.path.exists(file_path):
        await query.edit_message_text("خطا: فایل پیدا نشد. دوباره ارسال کنید.")
        return

    save_file(file_path, filename, category)
    context.user_data.pop("pending_file", None)
    context.user_data.pop("pending_filename", None)

    await query.edit_message_text(
        f"✅ فایل *{filename}* در دسته *{category}* ذخیره شد!",
        parse_mode="Markdown",
    )


def main():
    ensure_dirs()
    
    # استفاده از proxy برای دور زدن محدودیت‌ها
    proxy_url = os.environ.get("PROXY_URL", "")
    
    builder = Application.builder().token(BOT_TOKEN)
    
    if proxy_url:
        builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)
    
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("list", list_files))
    app.add_handler(CallbackQueryHandler(handle_category_choice, pattern="^cat:"))
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO,
        handle_file,
    ))

    logger.info("ربات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
