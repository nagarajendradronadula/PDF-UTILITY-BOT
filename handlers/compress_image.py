import os
from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes

TEMP_DIR = "temp_files"

async def handle_compress_image(message, context: ContextTypes.DEFAULT_TYPE):
    await message.reply_text(
        "📉 Please upload an image you'd like to compress.\n"
        "Once uploaded, the bot will compress it and send it back to you."
    )

async def receive_compress_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[INFO] receive_compress_image handler triggered")
    chat_id = update.message.chat.id

    # Determine whether the input is a photo or document
    if update.message.photo:
        image_file = update.message.photo[-1]
        file_id = image_file.file_unique_id
        file_ext = "jpg"
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        image_file = update.message.document
        file_id = image_file.file_unique_id
        file_ext = image_file.mime_type.split("/")[-1]
    else:
        await update.message.reply_text("⚠️ Please upload a valid image file (photo or image document).")
        return

    file = await image_file.get_file()

    await update.message.reply_text("📥 Image received for compression. Processing now...")

    original_path = os.path.join(TEMP_DIR, f"{chat_id}_{file_id}_original.{file_ext}")
    compressed_path = os.path.join(TEMP_DIR, f"{chat_id}_compressed.jpg")

    try:
        await file.download_to_drive(original_path)
        await update.message.reply_text("📥 Image downloaded successfully.")
    except Exception as e:
        await update.message.reply_text("❌ Failed to download the image. Please try again.")
        print(f"[ERROR] Failed to download image: {e}")
        return

    try:
        image = Image.open(original_path)
        print(f"[INFO] Compressing image: {original_path}")
        image.save(compressed_path, "JPEG", optimize=True, quality=40)
        print(f"[INFO] Compressed image saved: {compressed_path}")

        with open(compressed_path, "rb") as doc:
            await update.message.reply_document(document=doc, filename="compressed.jpg")
        await update.message.reply_text("✅ Your image has been compressed!")
        print("[INFO] Compressed image sent successfully.")
    except Exception as e:
        error_message = str(e).lower()
        if "cannot identify image file" in error_message:
            await update.message.reply_text("⚠️ The uploaded file isn't a valid image. Please try again with a proper image file.")
        else:
            await update.message.reply_text("❌ Failed to compress the image.")
            print(f"[ERROR] Image compression failed: {e}")
    finally:
        await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")
        if os.path.exists(original_path):
            os.remove(original_path)
        if os.path.exists(compressed_path):
            os.remove(compressed_path)