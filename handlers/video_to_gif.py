import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from moviepy.editor import VideoFileClip
from PIL import Image, ImageDraw

TEMP_DIR = "temp_files"

def apply_mask(gif_path, shape):
    """Apply shape mask to GIF frames"""
    gif = Image.open(gif_path)
    frames = []
    
    try:
        while True:
            frame = gif.copy().convert("RGBA")
            mask = Image.new("L", frame.size, 0)
            draw = ImageDraw.Draw(mask)
            width, height = frame.size

            if shape == "circle":
                draw.ellipse((0, 0, width, height), fill=255)
            elif shape == "square":
                draw.rectangle((0, 0, width, height), fill=255)
            elif shape == "rectangle":
                draw.rectangle((0, 0, width, height // 2), fill=255)
            elif shape == "triangle":
                draw.polygon([(width // 2, 0), (0, height), (width, height)], fill=255)

            masked_frame = Image.new("RGBA", frame.size)
            masked_frame.paste(frame, (0, 0), mask)
            frames.append(masked_frame)
            
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass

    if frames:
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], 
                      duration=gif.info.get('duration', 100), loop=0)

async def handle_video_to_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video to GIF conversion request"""
    keyboard = [
        [InlineKeyboardButton("🔵 Circle", callback_data="gif_circle")],
        [InlineKeyboardButton("⬜ Square", callback_data="gif_square")],
        [InlineKeyboardButton("📱 Rectangle", callback_data="gif_rectangle")],
        [InlineKeyboardButton("🔺 Triangle", callback_data="gif_triangle")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.reply_text(
        "🎬 **Video to GIF Converter**\n\n"
        "📤 Please upload a video file and choose the shape for your GIF:\n\n"
        "• Circle - Creates a circular GIF\n"
        "• Square - Creates a square GIF\n"
        "• Rectangle - Creates a rectangular GIF\n"
        "• Triangle - Creates a triangular GIF\n\n"
        "⚠️ Note: Videos will be trimmed to 5 seconds for optimization",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive video file for GIF conversion"""
    if not update.message.video and not update.message.document:
        await update.message.reply_text("❌ Please send a valid video file.")
        return

    # Store video file info
    if update.message.video:
        file_info = update.message.video
    else:
        file_info = update.message.document
        if not file_info.mime_type.startswith('video/'):
            await update.message.reply_text("❌ Please send a valid video file.")
            return

    context.user_data["video_file"] = file_info
    
    keyboard = [
        [InlineKeyboardButton("🔵 Circle", callback_data="gif_circle")],
        [InlineKeyboardButton("⬜ Square", callback_data="gif_square")],
        [InlineKeyboardButton("📱 Rectangle", callback_data="gif_rectangle")],
        [InlineKeyboardButton("🔺 Triangle", callback_data="gif_triangle")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Video received! Now choose the shape for your GIF:",
        reply_markup=reply_markup
    )

async def process_video_to_gif(update: Update, context: ContextTypes.DEFAULT_TYPE, shape: str):
    """Process video to GIF with selected shape"""
    query = update.callback_query
    await query.answer()
    
    video_file = context.user_data.get("video_file")
    if not video_file:
        await query.edit_message_text("❌ No video file found. Please upload a video first.")
        return

    await query.edit_message_text("🔄 Processing your video... This may take a moment.")

    try:
        # Download video file
        unique_id = str(uuid.uuid4())
        video_path = os.path.join(TEMP_DIR, f"video_{unique_id}.mp4")
        gif_path = os.path.join(TEMP_DIR, f"gif_{unique_id}.gif")

        file = await context.bot.get_file(video_file.file_id)
        await file.download_to_drive(video_path)

        # Convert video to GIF
        clip = VideoFileClip(video_path)
        clip = clip.subclip(0, min(5, clip.duration))  # Trim to max 5 seconds
        clip = clip.resize(height=300)  # Resize for optimization
        clip.write_gif(gif_path, fps=10)
        clip.close()

        # Apply shape mask
        if shape != "original":
            apply_mask(gif_path, shape)

        # Send the GIF
        with open(gif_path, 'rb') as gif_file:
            await context.bot.send_animation(
                chat_id=query.message.chat.id,
                animation=gif_file,
                caption=f"🎉 Your {shape} GIF is ready!"
            )

        # Cleanup
        os.remove(video_path)
        os.remove(gif_path)
        
        # Clear user data
        context.user_data.pop("video_file", None)

    except Exception as e:
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f"❌ Error processing video: {str(e)}"
        )
        # Cleanup on error
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(gif_path):
            os.remove(gif_path)