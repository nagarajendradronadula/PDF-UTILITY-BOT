import os
import zipfile
from telegram import Update
from telegram.ext import ContextTypes
from pdf2image import convert_from_path

TEMP_DIR = "temp_files"

async def handle_pdf_to_images(message, context: ContextTypes.DEFAULT_TYPE):
    await message.reply_text("🖼️ Please upload the PDF file you want to convert into images.")

async def receive_pdf_for_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    document = update.message.document

    if not document.file_name.endswith(".pdf"):
        await update.message.reply_text("⚠️ Only PDF files are supported.")
        return

    pdf_path = os.path.join(TEMP_DIR, f"{chat_id}_{document.file_unique_id}.pdf")
    file = await document.get_file()
    await file.download_to_drive(pdf_path)
    await update.message.reply_text("📥 PDF received for conversion to images. Processing now...")

    try:
        images = convert_from_path(pdf_path)
        if not images:
            await update.message.reply_text("⚠️ No pages found in the PDF.")
            return

        await update.message.reply_text(f"📄 Converting {len(images)} pages to images...")

        # If more than 5 pages, send as zip, else send as individual images
        if len(images) > 5:
            zip_path = os.path.join(TEMP_DIR, f"{chat_id}_pages.zip")
            image_paths = []
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for i, image in enumerate(images):
                    image_path = os.path.join(TEMP_DIR, f"{chat_id}_page_{i + 1}.jpg")
                    image.save(image_path, "JPEG")
                    zipf.write(image_path, os.path.basename(image_path))
                    image_paths.append(image_path)
            await update.message.reply_document(document=open(zip_path, "rb"), filename="pdf_pages.zip")
            await update.message.reply_text("✅ Conversion complete.")
            await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")
            # Cleanup zip file
            if os.path.exists(zip_path):
                os.remove(zip_path)
        else:
            image_paths = []
            for i, image in enumerate(images):
                image_path = os.path.join(TEMP_DIR, f"{chat_id}_page_{i + 1}.jpg")
                image.save(image_path, "JPEG")
                await update.message.reply_photo(photo=open(image_path, "rb"))
                image_paths.append(image_path)
            await update.message.reply_text("✅ All pages sent as images!")
            await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")

        # Cleanup all images
        for img_path in image_paths:
            if os.path.exists(img_path):
                os.remove(img_path)

    except Exception as e:
        error_message = str(e).lower()
        if "unable to get page count" in error_message or "syntax error" in error_message:
            await update.message.reply_text("⚠️ The PDF appears to be corrupted or not readable. Please try a different file.")
        else:
            await update.message.reply_text("❌ An internal error occurred while converting the PDF to images.")
            print(f"[ERROR] PDF to image conversion failed: {e}")
        await update.message.reply_text("🔁 You can type /start to return to the main menu.")

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)