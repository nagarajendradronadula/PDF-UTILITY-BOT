import os
from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes

TEMP_DIR = "temp_files"
A4_SIZE = (595, 842)  # in points (width, height)
image_files = {}

# Step 1: Ask user to upload images
async def handle_image_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat.id
    image_files[chat_id] = []
    await update.reply_text(
        "🖼️ Please send all the images you want to include in your PDF.\n"
        "When you're done, type /image_done."
    )

# Step 2: Receive each uploaded image
async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    photo = update.message.photo[-1]  # Get highest resolution version
    file = await photo.get_file()

    file_path = os.path.join(TEMP_DIR, f"{chat_id}_{photo.file_unique_id}.jpg")
    await file.download_to_drive(file_path)

    image_files.setdefault(chat_id, []).append(file_path)
    await update.message.reply_text("✅ Image received for PDF conversion.")

# Step 3: Combine images into a PDF
async def complete_image_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    files = image_files.get(chat_id, [])

    if not files:
        await update.message.reply_text("❗Please upload at least one image before using /image_done.")
        return

    pdf_path = os.path.join(TEMP_DIR, f"image_pdf_{chat_id}.pdf")

    try:
        image_list = []
        for path in sorted(files):
            img = Image.open(path).convert("RGB")
            img = img.resize(A4_SIZE)
            image_list.append(img)

        image_list[0].save(pdf_path, save_all=True, append_images=image_list[1:])
        await update.message.reply_document(document=open(pdf_path, "rb"), filename="images.pdf")
        await update.message.reply_text("✅ PDF created from your images!")
        await update.message.reply_text(
            "🔁 If you'd like to try another tool, type /start to return to the main menu."
        )
    except Exception as e:
        error_message = str(e).lower()
        if "cannot identify image file" in error_message or "image file is truncated" in error_message:
            await update.message.reply_text("⚠️ One or more of the uploaded images appears to be invalid or corrupted. Please re-upload valid image files.")
        else:
            await update.message.reply_text("❌ Failed to convert images to PDF due to an internal error.")
            print(f"[ERROR] Image to PDF failed: {e}")
        await update.message.reply_text(
            "🔁 You can type /start to return to the main menu."
        )
    finally:
        # Cleanup
        for f in files:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        image_files[chat_id] = []