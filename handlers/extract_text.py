import os
import fitz  # PyMuPDF
from telegram import Update
from telegram.ext import ContextTypes

TEMP_DIR = "temp_files"

async def handle_extract_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.reply_text("📄 Please upload a PDF from which you'd like to extract the text.")

async def receive_pdf_for_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    document = update.message.document

    if not document.file_name.endswith(".pdf"):
        await update.message.reply_text("⚠️ Please upload a valid PDF file.")
        return

    file_path = os.path.join(TEMP_DIR, f"{chat_id}_{document.file_unique_id}_extract.pdf")
    file = await document.get_file()
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"📥 PDF received: {document.file_name} — starting text extraction.")

    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()

        if not text.strip():
            await update.message.reply_text("ℹ️ No readable text found (might be scanned image).")
            await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")
        elif len(text) > 4000:
            await update.message.reply_text("📋 Extracted text is too long, sending first part only:")
            await update.message.reply_text(text[:4000])
            await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")
        else:
            await update.message.reply_text("📋 Extracted text:\n" + text)
            await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")

    except Exception as e:
        error_message = str(e).lower()
        if "cannot open broken document" in error_message or "syntax error" in error_message:
            await update.message.reply_text("⚠️ The PDF appears to be corrupted or unreadable. Please try a different file.")
        else:
            await update.message.reply_text("❌ An internal error occurred while extracting text from the PDF.")
            print(f"[ERROR] Text extraction failed: {e}")
        await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")

    finally:
        os.remove(file_path)