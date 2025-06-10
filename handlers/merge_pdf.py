import os
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from PyPDF2 import PdfMerger

# Directory to store temporary files
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# Store user-uploaded PDFs by chat ID
user_files = {}

# Starts the PDF merge process
async def handle_merge_pdf(query: CallbackQuery, chat_id: int):
    user_files[chat_id] = []
    await query.edit_message_text(
        "📎 Please upload the PDF files you want to merge.\n"
        "When you're done, type /done to receive the merged file."
    )

# Handles receiving individual PDF files
async def receive_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id

    if len(user_files.get(chat_id, [])) >= 10:
        await update.message.reply_text("⚠️ You can upload a maximum of 10 PDFs for merging.")
        return

    document = update.message.document

    if document.mime_type != "application/pdf":
        await update.message.reply_text("⚠️ Only PDF files are accepted.")
        return

    file = await document.get_file()
    file_path = os.path.join(TEMP_DIR, f"{chat_id}_{document.file_unique_id}.pdf")
    await file.download_to_drive(file_path)

    user_files.setdefault(chat_id, []).append(file_path)
    await update.message.reply_text(f"✅ File received for merging: {document.file_name}")

# Completes the merging process and sends back the final PDF
async def complete_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    files = user_files.get(chat_id, [])

    if len(files) < 2:
        await update.message.reply_text("❗Please upload at least two PDFs before using /done.")
        return

    update.message.reply_text("🔁 Please wait while we merge your PDFs...")
    merged_path = os.path.join(TEMP_DIR, f"merged_{chat_id}.pdf")
    merger = PdfMerger()
    

    try:
        for pdf in files:
            merger.append(pdf)
        merger.write(merged_path)
        merger.close()
        update.message.reply_text("✅ Merging complete. Here is your file!")
    except Exception as e:
        error_message = str(e).lower()
        if "could not read malformed pdf file" in error_message or "startxref not found" in error_message:
            await update.message.reply_text("⚠️ One or more of the uploaded PDFs seem to be corrupted or invalid. Please check and try again.")
        else:
            await update.message.reply_text("❌ Failed to merge PDFs due to an internal error.")
            print(f"[ERROR] Failed to merge PDFs for {chat_id}: {e}")
        await update.message.reply_text("🔁 You can type /start to return to the main menu.")
        return

    await update.message.reply_document(document=open(merged_path, "rb"), filename="merged.pdf")
    await update.message.reply_text("✅ Merging complete. Here is your file!")
    await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")

    # Cleanup
    for f in files:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(merged_path):
        os.remove(merged_path)

    user_files[chat_id] = []