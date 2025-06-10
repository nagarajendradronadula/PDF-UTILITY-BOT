import os
import io
import subprocess
from pptx import Presentation
from pptx.util import Inches
from fpdf import FPDF
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image, ImageDraw
from pathlib import Path
import cloudconvert
from dotenv import load_dotenv
import requests

TEMP_DIR = "temp_files"

async def handle_ppt_to_pdf(message, context: ContextTypes.DEFAULT_TYPE):
    await message.reply_text("📑 Please upload a PPT (.pptx) file to convert it into a PDF.")

async def receive_ppt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    document = update.message.document

    if not document.file_name.endswith(".pptx"):
        await update.message.reply_text("⚠️ Please upload a valid `.pptx` file.")
        return

    ppt_path = os.path.join(TEMP_DIR, f"{chat_id}_{document.file_unique_id}.pptx")
    pdf_path = os.path.join(TEMP_DIR, f"{chat_id}_converted.pdf")

    file = await document.get_file()
    await file.download_to_drive(ppt_path)
    await update.message.reply_text("📥 PPT file received. Converting to PDF now...")

    try:
        load_dotenv()
        api_key = os.getenv("CLOUDCONVERT_API_KEY")
        print("CLOUDCONVERT_API_KEY:", api_key)
        cloudconvert.configure(api_key=api_key)

        job = cloudconvert.Job.create(payload={
            "tasks": {
                "import-ppt": {
                    "operation": "import/upload"
                },
                "convert-ppt": {
                    "operation": "convert",
                    "input": "import-ppt",
                    "input_format": "pptx",
                    "output_format": "pdf",
                    "engine": "office"
                },
                "export-pdf": {
                    "operation": "export/url",
                    "input": "convert-ppt"
                }
            }
        })

        upload_task = next(task for task in job["tasks"] if task["name"] == "import-ppt")
        upload_url = upload_task["result"]["form"]["url"]
        upload_params = upload_task["result"]["form"]["parameters"]

        with open(ppt_path, "rb") as f:
            response = requests.post(upload_url, data=upload_params, files={"file": f})
            response.raise_for_status()

        job = cloudconvert.Job.wait(id=job["id"])
        export_task = next(task for task in job["tasks"] if task["name"] == "export-pdf")
        file_url = export_task["result"]["files"][0]["url"]

        response = requests.get(file_url)
        with open(pdf_path, "wb") as f:
            f.write(response.content)

        await update.message.reply_document(document=open(pdf_path, "rb"), filename="converted_ppt.pdf")
        await update.message.reply_text("✅ Your PPT has been converted to PDF using CloudConvert.")
    except Exception as e:
        error_message = str(e).lower()
        if "unsupported file type" in error_message or "corrupt" in error_message:
            await update.message.reply_text("⚠️ The PPT file appears to be invalid or corrupted. Please upload a valid `.pptx` file.")
        else:
            await update.message.reply_text("❌ An error occurred while converting your PPT to PDF.")
            print(f"[ERROR] PPT to PDF conversion failed: {e}")
    finally:
        await update.message.reply_text("🔁 If you'd like to try another tool, type /start to return to the main menu.")
        try:
            os.remove(ppt_path)
        except Exception:
            pass
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass