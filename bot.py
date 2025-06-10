from handlers.image_to_pdf import handle_image_to_pdf, receive_image, complete_image_pdf
from handlers.compress_image import handle_compress_image, receive_compress_image
from handlers.ppt_to_pdf import handle_ppt_to_pdf, receive_ppt
from handlers.extract_text import handle_extract_text, receive_pdf_for_text
from handlers.pdf_to_images import handle_pdf_to_images, receive_pdf_for_images
from handlers.merge_pdf import handle_merge_pdf, receive_pdf, complete_merge
import os
from telegram import Update, CallbackQuery
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.ext import ContextTypes
from PyPDF2 import PdfMerger
from dotenv import load_dotenv
load_dotenv()

TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)
user_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("🧩 Merge PDFs", callback_data="merge")],
        [InlineKeyboardButton("🖼️ Image to PDF", callback_data="image_to_pdf")],
        [InlineKeyboardButton("📉 Compress Image", callback_data="compress_image")],
        [InlineKeyboardButton("📑 PPT to PDF", callback_data="ppt_to_pdf")],
        [InlineKeyboardButton("🔍 Extract Text from PDF", callback_data="extract_text")],
        [InlineKeyboardButton("🖼️ PDF to Images", callback_data="pdf_to_images")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to the PDF Utility Bot!\n\n"
        "📎 You can use the following commands:\n"
        "• /merge – Merge multiple PDFs\n"
        "• /image_to_pdf – Convert images to a single PDF\n"
        "• /compress_image – Compress an image\n"
        "• /ppt_to_pdf – Convert PPTX to PDF\n"
        "• /extract_text – Extract text from PDF\n"
        "• /pdf_to_images – Convert PDF pages to images\n"
        "• /done – Finish the current merge process\n"
        "• /image_done – Finish the current image to PDF process\n\n"
        "👇 Or click a button below to get started:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id

    context.user_data["active_feature"] = data

    # Confirm feature selection
    try:
        await query.edit_message_text(f"✅ You selected: *{data.replace('_', ' ').title()}*", parse_mode="Markdown")
    except Exception:
        await query.message.reply_text(f"✅ You selected: *{data.replace('_', ' ').title()}*", parse_mode="Markdown")

    if data == "merge":
        await handle_merge_pdf(query, chat_id)
    elif data == "image_to_pdf":
        await handle_image_to_pdf(query.message, context)
    elif data == "compress_image":
        await handle_compress_image(query.message, context)
    elif data == "ppt_to_pdf":
        await handle_ppt_to_pdf(query.message, context)
    elif data == "extract_text":
        await handle_extract_text(query.message, context)
    elif data == "pdf_to_images":
        await handle_pdf_to_images(query.message, context)
    else:
        await query.message.reply_text("❗Unknown option selected.")

async def route_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feature = context.user_data.get("active_feature")
    if feature == "image_to_pdf":
        await receive_image(update, context)
    elif feature == "compress_image":
        await receive_compress_image(update, context)
    else:
        await update.message.reply_text("⚠️ Please choose a feature from /start before sending an image.")

async def route_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feature = context.user_data.get("active_feature")
    if feature == "merge":
        await receive_pdf(update, context)
    elif feature == "extract_text":
        await receive_pdf_for_text(update, context)
    elif feature == "pdf_to_images":
        await receive_pdf_for_images(update, context)
    else:
        await update.message.reply_text("⚠️ Please choose a PDF-related feature from /start before uploading a PDF.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", complete_merge))
    app.add_handler(MessageHandler(filters.Document.PDF, route_pdf))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("image_done", complete_image_pdf))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/vnd.openxmlformats-officedocument.presentationml.presentation"), receive_ppt))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/pdf") & filters.Caption("extract"), receive_pdf_for_text))
    app.add_handler(MessageHandler(filters.Document.MimeType("application/pdf") & filters.Caption("images"), receive_pdf_for_images))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, route_image))

    app.add_handler(CommandHandler("merge", handle_merge_pdf))
    app.add_handler(CommandHandler("image_to_pdf", handle_image_to_pdf))
    app.add_handler(CommandHandler("compress_image", handle_compress_image))
    app.add_handler(CommandHandler("ppt_to_pdf", handle_ppt_to_pdf))
    app.add_handler(CommandHandler("extract_text", handle_extract_text))
    app.add_handler(CommandHandler("pdf_to_images", handle_pdf_to_images))

    print("🚀 Bot is running...")
    app.run_polling()