import logging
import os
import io
import zipfile

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import PDF manipulation libraries
import fitz  # PyMuPDF
from pypdf import PdfReader


# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I am your PDF Utility Bot. Send me a PDF file to see what I can do.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text("Send me a PDF and I will show you what I can do!")

# --- Message and Callback Handlers ---

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming PDF files and presents action buttons."""
    document = update.message.document
    if document.mime_type != "application/pdf":
        await update.message.reply_text("Please send me a PDF file.")
        return

    file_id = document.file_id
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Convert to Images", callback_data=f"to_images:{file_id}"),
            InlineKeyboardButton("📄 Extract Text", callback_data=f"extract_text:{file_id}"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("What would you like to do with this PDF?", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and runs the chosen PDF action."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press

    action, file_id = query.data.split(":", 1)

    await query.edit_message_text(text=f"Processing your request... Please wait.")

    try:
        file = await context.bot.get_file(file_id)
        pdf_bytes = await file.download_as_bytearray()

        if action == "to_images":
            await convert_pdf_to_images(query, pdf_bytes)
        elif action == "extract_text":
            await extract_text_from_pdf(query, pdf_bytes)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await query.edit_message_text(text="Sorry, an error occurred while processing your file.")

async def convert_pdf_to_images(query, pdf_bytes):
    """Converts a PDF into a zip file of images."""
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(dpi=200) # Higher DPI for better quality
            img_bytes = pix.tobytes("png")
            zip_file.writestr(f"page_{page_num + 1}.png", img_bytes)

    zip_buffer.seek(0)
    await query.message.reply_document(
        document=zip_buffer,
        filename="converted_images.zip",
        caption="Here are the converted images from your PDF."
    )
    await query.edit_message_text(text="✅ Conversion to images complete!")

async def extract_text_from_pdf(query, pdf_bytes):
    """Extracts text from a PDF and sends it as a .txt file."""
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n\n"

    if not text.strip():
        await query.edit_message_text(text="Could not extract any text from this PDF. It might be an image-based PDF.")
        return

    text_buffer = io.BytesIO(text.encode('utf-8'))
    await query.message.reply_document(
        document=text_buffer,
        filename="extracted_text.txt",
        caption="Here is the extracted text from your PDF."
    )
    await query.edit_message_text(text="✅ Text extraction complete!")

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles any message that isn't a command or a PDF."""
    await update.message.reply_text(
        "Sorry, I didn't understand that. Please send me a PDF file to get started."
    )


# --- Main Bot Logic ---

def main() -> None:
    """Start the bot."""
    # Get the token from environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not found in environment variables. Please create a .env file.")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Handler for PDF documents
    application.add_handler(MessageHandler(filters.Document.MimeType("application/pdf"), handle_document))
    
    # Handler for button callbacks
    application.add_handler(CallbackQueryHandler(button_callback))

    # Handler for any other message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    application.run_polling()

if __name__ == "__main__":
    main()
