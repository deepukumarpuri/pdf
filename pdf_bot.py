#!/usr/bin/env python3
# coding: utf-8

import dotenv
import langdetect
import logging
import os
import shlex
import smtplib

from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from subprocess import Popen, PIPE

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, RegexHandler, Filters
from telegram.ext.dispatcher import run_async

from cov_states import *

# Enable logging
logging.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt='%Y-%m-%d %I:%M:%S %p',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
dotenv.load(dotenv_path)
app_url = os.environ.get("APP_URL")
port = int(os.environ.get('PORT', '5000'))

telegram_token = os.environ.get("TELEGRAM_TOKEN_BETA") if os.environ.get("TELEGRAM_TOKEN_BETA") \
    else os.environ.get("TELEGRAM_TOKEN")
dev_tele_id = int(os.environ.get("DEV_TELE_ID"))
dev_email = os.environ.get("DEV_EMAIL") if os.environ.get("DEV_EMAIL") else "sample@email.com"
dev_email_pw = os.environ.get("DEV_EMAIL_PW")
is_email_feedback = os.environ.get("IS_EMAIL_FEEDBACK")
smtp_host = os.environ.get("SMTP_HOST")


# Sends start message
@run_async
def start(bot, update):
    tele_id = update.message.chat.id

    if update.message.chat.type != "group":
        message = "Welcome to PDF Bot. Type /help to see what I can do."
        bot.sendMessage(tele_id, message)


# Sends help message
@run_async
def help(bot, update):
    tele_id = update.message.from_user.id

    message = "The bot will guide you through each job. Below is a list of commands:\n" \
              "/decrypt - decrypt a PDF file with a password\n" \
              "/encrypt - encrypt a PDF file with a password\n" \
              "/merge - merge PDF files into a single PDF file\n" \
              "/rotate - rotate a PDF file\n" \
              "/split - split a PDF file with specified page range\n" \
              "/watermark - add a watermark (in PDF format) to a PDF file"

    bot.sendMessage(tele_id, message)


# Sends donate message
@run_async
def donate(bot, update):
    player_tele_id = update.message.from_user.id
    message = "Want to help keep me online? Please donate to %s through PayPal.\n\nDonations help " \
              "me to stay on my server and keep running." % dev_email
    bot.send_message(player_tele_id, message)


# Creates a decrypt conversation handler
def decrypt_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("decrypt", decrypt)],

        states={
            RECEIVE_DECRYPT_FILE: [MessageHandler(Filters.document, receive_decrypt_file, pass_user_data=True)],
            RECEIVE_DECRYPT_PW: [MessageHandler(Filters.text, receive_decrypt_pw, pass_user_data=True)]
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the decrypt conversation
@run_async
def decrypt(bot, update):
    update.message.reply_text("Please send me the PDF file that you will like to decrypt or type /cancel to "
                              "cancel this operation.")

    return RECEIVE_DECRYPT_FILE


# Receives and checks for the source PDF file
@run_async
def receive_decrypt_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to encrypt or type /cancel to cancel this operation.")

        return RECEIVE_DECRYPT_FILE
    elif not is_pdf_encrypted(bot, pdf_file.file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is already decrypted.")

        return ConversationHandler.END

    user_data["decrypt_file_id"] = pdf_file.file_id
    update.message.reply_text("Please send me the password to decrypt the PDF file.")

    return RECEIVE_DECRYPT_PW


# Receives pw and decrypts PDF file with pw
@run_async
def receive_decrypt_pw(bot, update, user_data):
    if not user_data["decrypt_file_id"]:
        return ConversationHandler.END

    tele_id = update.message.from_user.id
    pw = update.message.text
    update.message.reply_text("Decrypting your PDF file.")

    file_id = user_data["decrypt_file_id"]
    filename = "%d_decrypt_source.pdf" % tele_id
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    out_filename = "%d_decrypted.pdf" % tele_id

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    try:
        if pdf_reader.decrypt(pw) == 0:
            update.message.reply_text("The decryption password is incorrect. Please send the password again.")

            return RECEIVE_DECRYPT_PW
    except NotImplementedError:
        update.message.reply_text("The PDF file is encrypted with a method that I cannot decrypt. Sorry.")

        return ConversationHandler.END

    for page in pdf_reader.pages:
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your decrypted PDF file.")

    os.remove(filename)
    os.remove(out_filename)
    del user_data["decrypt_file_id"]

    return ConversationHandler.END


# Creates a encrypt conversation handler
def encrypt_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("encrypt", encrypt)],

        states={
            RECEIVE_ENCRYPT_FILE: [MessageHandler(Filters.document, receive_encrypt_file, pass_user_data=True)],
            RECEIVE_ENCRYPT_PW: [MessageHandler(Filters.text, receive_encrypt_pw, pass_user_data=True)]
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the encrypt conversation
@run_async
def encrypt(bot, update):
    update.message.reply_text("Please send me the PDF file that you will like to encrypt or type /cancel to "
                              "cancel this operation.")
    return RECEIVE_ENCRYPT_FILE


# Receives and checks for the source PDF file
@run_async
def receive_encrypt_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to encrypt or type /cancel to cancel this operation.")

        return RECEIVE_ENCRYPT_FILE
    elif is_pdf_encrypted(bot, pdf_file.file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        return ConversationHandler.END

    user_data["encrypt_file_id"] = pdf_file.file_id
    update.message.reply_text("Please send me the password that you will like to encrypt your PDF file with.")

    return RECEIVE_ENCRYPT_PW


# Receives pw and encrypts PDF file with pw
@run_async
def receive_encrypt_pw(bot, update, user_data):
    if not user_data["encrypt_file_id"]:
        return ConversationHandler.END

    tele_id = update.message.from_user.id
    pw = update.message.text
    update.message.reply_text("Encrypting your PDF file.")

    file_id = user_data["encrypt_file_id"]
    filename = "%d_encrypt_source.pdf" % tele_id
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    out_filename = "%d_encrypted.pdf" % tele_id

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        pdf_writer.addPage(page)

    pdf_writer.encrypt(pw)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your encrypted PDF file.")

    os.remove(filename)
    os.remove(out_filename)
    del user_data["encrypt_file_id"]

    return ConversationHandler.END


# Creates a merge conversation handler
def merge_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("merge", merge, pass_user_data=True)],

        states={
            RECEIVE_MERGE_FILE: [MessageHandler(Filters.document, receive_merge_file, pass_user_data=True),
                                 RegexHandler("^Done$", merge_file, pass_user_data=True)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the merge conversation
@run_async
def merge(bot, update, user_data):
    if "merge_file_ids" in user_data:
        del user_data["merge_file_ids"]
    if "merge_filenames" in user_data:
        del user_data["merge_filenames"]

    update.message.reply_text("Please send me the first PDF file that you will like to merge or type /cancel to "
                              "cancel this operation. The files will be merged in the order that you send me the "
                              "files.")

    return RECEIVE_MERGE_FILE


# Receives and checks for the source PDF file
@run_async
def receive_merge_file(bot, update, user_data):
    pdf_file = update.message.document
    file_id = pdf_file.file_id
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to merge or type /cancel to cancel this operation.")

        return RECEIVE_MERGE_FILE
    elif is_pdf_encrypted(bot, file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        if "merge_filenames" in user_data and user_data["merge_filenames"]:
            send_received_filenames(update, user_data["merge_filenames"])

            return RECEIVE_MERGE_FILE
        else:
            return ConversationHandler.END

    if "merge_file_ids" in user_data and user_data["merge_file_ids"]:
        user_data["merge_file_ids"].append(file_id)
        user_data["merge_filenames"].append(filename)
    else:
        user_data["merge_file_ids"] = [file_id]
        user_data["merge_filenames"] = [filename]

    keyboard = [["Done"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text("Please send me the next PDF file that you will like to merge or say Done if you have "
                              "sent me all the files that you want to merge.", reply_markup=reply_markup)

    send_received_filenames(update, user_data["merge_filenames"])

    return RECEIVE_MERGE_FILE


# Sends a list of received filenames
def send_received_filenames(update, filenames):
    text = "You have sent me the following PDF files:\n"

    for i, filename in enumerate(filenames):
        i += 1
        text += "%d: %s\n" % (i, filename)

    update.message.reply_text(text)


# Merges PDF file
@run_async
def merge_file(bot, update, user_data):
    if not user_data["merge_file_ids"]:
        return ConversationHandler.END

    tele_id = update.message.from_user.id
    update.message.reply_text("Merging your files.", reply_markup=ReplyKeyboardRemove())

    merger = PdfFileMerger()
    out_filename = "%d_merged.pdf" % tele_id

    for file_id in user_data["merge_file_ids"]:
        filename = "%d_merge_source.pdf" % tele_id
        pdf_file = bot.get_file(file_id)
        pdf_file.download(custom_path=filename)
        merger.append(open(filename, "rb"))
        os.remove(filename)

    with open(out_filename, "wb") as f:
        merger.write(f)

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your merged PDF file.")

    os.remove(out_filename)
    del user_data["merge_file_ids"]
    del user_data["merge_filenames"]

    return ConversationHandler.END


# Creates a rotate conversation handler
def rotate_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("rotate", rotate)],

        states={
            RECEIVE_ROTATE_FILE: [MessageHandler(Filters.document, receive_rotate_file, pass_user_data=True)],
            ROTATE_FILE: [RegexHandler("^(90|180|270)$", rotate_file, pass_user_data=True)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the rotate conversation
@run_async
def rotate(bot, update):
    update.message.reply_text("Please send me the PDF file that you will like to rotate or type /cancel to cancel this "
                              "operation.")
    return RECEIVE_ROTATE_FILE


# Receives and checks for the PDF file
@run_async
def receive_rotate_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to rotate or type /cancel to cancel this operation.")

        return RECEIVE_ROTATE_FILE
    elif is_pdf_encrypted(bot, pdf_file.file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        return ConversationHandler.END

    user_data["rotate_file_id"] = pdf_file.file_id

    keyboard = [["90"], ["180"], ["270"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text("Please select the degrees that you will like to rotate your PDF file in clockwise.",
                              reply_markup=reply_markup)

    return ROTATE_FILE


# Rotates the PDF file
@run_async
def rotate_file(bot, update, user_data):
    if not user_data["rotate_file_id"]:
        return ConversationHandler.END

    tele_id = update.message.from_user.id
    rotate_degree = int(update.message.text)
    update.message.reply_text("Rotating your PDF file clockwise by %d degrees." % rotate_degree,
                              reply_markup=ReplyKeyboardRemove())

    file_id = user_data["rotate_file_id"]
    filename = "%d_rotate_source.pdf" % tele_id
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    out_filename = "%d_rotated.pdf" % tele_id

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        pdf_writer.addPage(page.rotateClockwise(rotate_degree))

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your rotated PDF file.")

    os.remove(filename)
    os.remove(out_filename)
    del user_data["rotate_file_id"]

    return ConversationHandler.END


# Creates a scale by conversation handler
def scale_by_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("scaleby", scale)],

        states={
            RECEIVE_SCALE_FILE: [MessageHandler(Filters.document, receive_scale_by_file, pass_user_data=True)],
            RECEIVE_SCALE_X: [MessageHandler(Filters.text, receive_scale_by_x, pass_user_data=True)],
            RECEIVE_SCALE_Y: [MessageHandler(Filters.text, receive_scale_by_y, pass_user_data=True)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the scale by conversation
@run_async
def scale(bot, update):
    update.message.reply_text("Please send me the PDF file that you will like to scale or type /cancel to cancel this "
                              "operation.")

    return RECEIVE_SCALE_FILE


# Receives and checks for the PDF file
@run_async
def receive_scale_by_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to split or type /cancel to cancel this operation.")

        return RECEIVE_SPLIT_FILE
    elif is_pdf_encrypted(bot, pdf_file.file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        return ConversationHandler.END

    user_data["scale_by_file_id"] = pdf_file.file_id

    update.message.reply_text("Please send me the scaling factor for the horizontal axis. For example, 2 will double "
                              "the horizontal axis and 0.5 will half the horizontal axis.")

    return RECEIVE_SCALE_X


# Receives and checks for the x scaling factor
@run_async
def receive_scale_by_x(bot, update, user_data):
    scale_x = update.message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        update.message.reply_text("The scaling factor that you sent me is invalid. Please try again.")

        return RECEIVE_SCALE_X

    user_data["scale_by_x"] = scale_x

    update.message.reply_text("Please send me the scaling factor for the vertical axis. For example, 2 will double "
                              "the vertical axis and 0.5 will half the vertical axis.")

    return RECEIVE_SCALE_Y


# Receives and checks for the y scaling factor
@run_async
def receive_scale_by_y(bot, update, user_data):
    if not user_data["scale_by_file_id"] or not user_data["scale_by_x"]:
        return ConversationHandler.END

    scale_y = update.message.text

    try:
        scale_y = float(scale_y)
    except ValueError:
        update.message.reply_text("The scaling factor that you sent me is invalid. Please try again.")

        return RECEIVE_SCALE_Y

    scale_x = user_data["scale_by_x"]
    tele_id = update.message.from_user.id
    update.message.reply_text("Scaling your PDF file, horizontally by {0:g} and vertically by {0:g}.".
                              format(scale_x, scale_y))

    file_id = user_data["scale_by_file_id"]
    filename = "%d_scale_by_source.pdf" % tele_id
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    out_filename = "%d_scaled_by.pdf" % tele_id

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        page.scale(scale_x, scale_y)
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your scaled PDF file.")

    os.remove(filename)
    os.remove(out_filename)
    del user_data["scale_by_file_id"]
    del user_data["scale_by_x"]

    return ConversationHandler.END


# Creates a scale to conversation handler
def scale_to_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("scaleto", scale)],

        states={
            RECEIVE_SCALE_FILE: [MessageHandler(Filters.document, receive_scale_to_file, pass_user_data=True)],
            RECEIVE_SCALE_X: [MessageHandler(Filters.text, receive_scale_to_x, pass_user_data=True)],
            RECEIVE_SCALE_Y: [MessageHandler(Filters.text, receive_scale_to_y, pass_user_data=True)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Receives and checks for the PDF file
@run_async
def receive_scale_to_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to split or type /cancel to cancel this operation.")

        return RECEIVE_SPLIT_FILE
    elif is_pdf_encrypted(bot, pdf_file.file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        return ConversationHandler.END

    user_data["scale_to_file_id"] = pdf_file.file_id

    update.message.reply_text("Please send me the new width.")

    return RECEIVE_SCALE_X


# Receives and checks for the width
@run_async
def receive_scale_to_x(bot, update, user_data):
    scale_x = update.message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        update.message.reply_text("The width that you sent me is invalid. Please try again.")

        return RECEIVE_SCALE_X

    user_data["scale_to_x"] = scale_x

    update.message.reply_text("Please send me the new height.")

    return RECEIVE_SCALE_Y


# Receives and checks for the height
@run_async
def receive_scale_to_y(bot, update, user_data):
    if not user_data["scale_to_file_id"] or not user_data["scale_to_x"]:
        return ConversationHandler.END

    scale_y = update.message.text

    try:
        scale_y = float(scale_y)
    except ValueError:
        update.message.reply_text("The height that you sent me is invalid. Please try again.")

        return RECEIVE_SCALE_Y

    scale_x = user_data["scale_to_x"]
    tele_id = update.message.from_user.id
    update.message.reply_text("Scaling your PDF file with width of {0:g} and height of {0:g}.".
                              format(scale_x, scale_y))

    file_id = user_data["scale_to_file_id"]
    filename = "%d_scale_to_source.pdf" % tele_id
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    out_filename = "%d_scaled_to.pdf" % tele_id

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(filename, "rb"))

    for page in pdf_reader.pages:
        page.scaleTo(scale_x, scale_y)
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your scaled PDF file.")

    os.remove(filename)
    os.remove(out_filename)
    del user_data["scale_to_file_id"]
    del user_data["scale_to_x"]

    return ConversationHandler.END


# Creates a split conversation handler
def split_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("split", split)],

        states={
            RECEIVE_SPLIT_FILE: [MessageHandler(Filters.document, receive_split_file, pass_user_data=True)],
            SPLIT_FILE: [MessageHandler(Filters.text, split_file, pass_user_data=True)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the rotate conversation
@run_async
def split(bot, update):
    update.message.reply_text("Please send me the PDF file that you will like to split or type /cancel to cancel this "
                              "operation.")

    return RECEIVE_SPLIT_FILE


# Receives and checks for the PDF file
@run_async
def receive_split_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to split or type /cancel to cancel this operation.")

        return RECEIVE_SPLIT_FILE
    elif is_pdf_encrypted(bot, pdf_file.file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        return ConversationHandler.END

    user_data["split_file_id"] = pdf_file.file_id

    update.message.reply_text("Please send me the range that you will like to keep. You can refer to "
                              "http://telegra.ph/Telegram-PDF-Bot-07-16 for range examples.")

    return SPLIT_FILE


# Splits the PDF file
@run_async
def split_file(bot, update, user_data):
    if not user_data["split_file_id"]:
        return ConversationHandler.END

    tele_id = update.message.from_user.id
    split_range = update.message.text
    update.message.reply_text("Splitting your PDF file.")

    file_id = user_data["split_file_id"]
    filename = "%d_split_source.pdf" % tele_id
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    out_filename = "%d_split.pdf" % tele_id

    command = "python3 pdfcat.py -o {out_filename} {in_filename} {split_range}". \
        format(out_filename=out_filename, in_filename=filename, split_range=split_range)

    process = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    process_out, process_err = process.communicate()

    if process.returncode != 0 or not os.path.exists(out_filename) or "[Errno" in process_err.decode("utf8").strip():
        update.message.reply_text("The range is invalid. Please send me the range again.")

        return SPLIT_FILE

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your split PDF file.")

    os.remove(filename)
    os.remove(out_filename)
    del user_data["split_file_id"]

    return ConversationHandler.END


# Creates a watermark conversation handler
def watermark_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("watermark", watermark)],

        states={
            RECEIVE_WATERMARK_SOURCE_FILE: [MessageHandler(Filters.document, receive_watermark_source_file,
                                                           pass_user_data=True)],
            RECEIVE_WATERMARK_FILE: [MessageHandler(Filters.document, receive_watermark_file, pass_user_data=True)]
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Starts the watermark conversation
@run_async
def watermark(bot, update):
    update.message.reply_text("Please send me the PDF file that you will like to add a watermark or type /cancel to "
                              "cancel this operation.")
    return RECEIVE_WATERMARK_SOURCE_FILE


# Receives and checks for the source PDF file
@run_async
def receive_watermark_source_file(bot, update, user_data):
    pdf_file = update.message.document
    filename = pdf_file.file_name

    if not filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the PDF file that you will "
                                  "like to add a watermark or type /cancel to cancel this operation.")

        return RECEIVE_WATERMARK_SOURCE_FILE
    elif is_pdf_encrypted(bot, pdf_file.file_id, update.message.from_user.id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        return ConversationHandler.END

    user_data["watermark_file_id"] = pdf_file.file_id
    update.message.reply_text("Please send me the watermark in PDF format.")

    return RECEIVE_WATERMARK_FILE


# Receives and checks for the watermark PDF file and watermark the PDF file
@run_async
def receive_watermark_file(bot, update, user_data):
    if not user_data["watermark_file_id"]:
        return ConversationHandler.END

    tele_id = update.message.from_user.id
    watermark_pdf_file = update.message.document
    watermark_file_id = watermark_pdf_file.file_id
    watermark_filename = watermark_pdf_file.file_name

    if not watermark_filename.endswith("pdf"):
        update.message.reply_text("The file you sent is not a PDF file. Please send me the watermark PDF file.")

        return RECEIVE_WATERMARK_FILE
    elif is_pdf_encrypted(bot, watermark_file_id, tele_id):
        update.message.reply_text("The PDF file you sent is encrypted. Please decrypt it yourself or use /decrypt to "
                                  "decrypt it first.")

        return ConversationHandler.END

    update.message.reply_text("Adding watermark to your PDF file.")

    source_file_id = user_data["watermark_file_id"]
    source_filename = "%d_watermark_source.pdf" % tele_id
    source_pdf_file = bot.get_file(source_file_id)
    source_pdf_file.download(custom_path=source_filename)
    out_filename = "%d_watermarked.pdf" % tele_id

    watermark_pdf_file = bot.get_file(watermark_file_id)
    watermark_filename = "%d_watermark.pdf" % tele_id
    watermark_pdf_file.download(custom_path=watermark_filename)

    pdf_writer = PdfFileWriter()
    pdf_reader = PdfFileReader(open(source_filename, "rb"))
    watermark_reader = PdfFileReader(open(watermark_filename, "rb"))

    for page in pdf_reader.pages:
        page.mergePage(watermark_reader.getPage(0))
        pdf_writer.addPage(page)

    with open(out_filename, "wb") as f:
        pdf_writer.write(f)

    update.message.reply_document(document=open(out_filename, "rb"),
                                  caption="Here is your watermarked PDF file.")

    os.remove(source_filename)
    os.remove(watermark_filename)
    os.remove(out_filename)
    del user_data["watermark_file_id"]

    return ConversationHandler.END


# Checks if PDF file is encrypted
def is_pdf_encrypted(bot, file_id, tele_id):
    filename = "%d_check.pdf" % tele_id
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)

    pdf_reader = PdfFileReader(open(filename, "rb"))
    encrypted = pdf_reader.isEncrypted
    os.remove(filename)

    return encrypted


# Creates a feedback conversation handler
def feedback_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],

        states={
            0: [MessageHandler(Filters.text, receive_feedback)],
        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True
    )

    return conv_handler


# Sends a feedback message
@run_async
def feedback(bot, update):
    update.message.reply_text("Please send me your feedback or type /cancel to cancel this operation. My developer "
                              "can understand English and Chinese.")

    return 0


# Saves a feedback
@run_async
def receive_feedback(bot, update):
    feedback_msg = update.message.text
    valid_lang = False
    langdetect.DetectorFactory.seed = 0
    langs = langdetect.detect_langs(feedback_msg)

    for lang in langs:
        if lang.lang in ("en", "zh-tw", "zh-cn"):
            valid_lang = True
            break

    if not valid_lang:
        update.message.reply_text("The feedback you sent is not in English or Chinese. Please try again.")
        return 0

    update.message.reply_text("Thank you for your feedback, I will let my developer know.")

    if is_email_feedback:
        server = smtplib.SMTP(smtp_host)
        server.ehlo()
        server.starttls()
        server.login(dev_email, dev_email_pw)

        text = "Feedback received from %d\n\n%s" % (update.message.from_user.id, update.message.text)
        message = "Subject: %s\n\n%s" % ("Telegram PDF Bot Feedback", text)
        server.sendmail(dev_email, dev_email, message)
    else:
        logger.info("Feedback received from %d: %s" % (update.message.from_user.id, update.message.text))

    return ConversationHandler.END


# Cancels feedback opteration
@run_async
def cancel(bot, update):
    update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Sends a message to a specified user
def send(bot, update, args):
    if update.message.from_user.id == dev_tele_id:
        tele_id = int(args[0])
        message = " ".join(args[1:])

        try:
            bot.send_message(tele_id, message)
        except Exception as e:
            logger.exception(e)
            bot.send_message(dev_tele_id, "Failed to send message")


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(telegram_token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("donate", donate))
    dp.add_handler(decrypt_cov_handler())
    dp.add_handler(encrypt_cov_handler())
    dp.add_handler(merge_cov_handler())
    dp.add_handler(rotate_cov_handler())
    dp.add_handler(scale_by_cov_handler())
    dp.add_handler(scale_to_cov_handler())
    dp.add_handler(split_cov_handler())
    dp.add_handler(watermark_cov_handler())
    dp.add_handler(feedback_cov_handler())
    dp.add_handler(CommandHandler("send", send, pass_args=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if app_url:
        updater.start_webhook(listen="0.0.0.0",
                              port=port,
                              url_path=telegram_token)
        updater.bot.set_webhook(app_url + telegram_token)
    else:
        updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
