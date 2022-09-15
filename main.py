import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import html
import telegram
from bs4 import BeautifulSoup
import validators
import requests
from constants import *
from matches import *


'''
called when the user uses the /text or /text_exact command. 
attempts up to 3 reverse search queries (based on text size) and returns results to user
'''


async def text_process(update, context, exact_match=False) -> None:
    word_list = context.args
    if len(word_list) == 0:
        await update.message.reply_text(TEXT_USAGE_FORMAT)
        return
    if len(word_list) >= MAX_WORD_COUNT:
        await update.message.reply_text(OVER_WORD_COUNT_MESSAGE.format(MAX_WORD_COUNT))
        return
    for word in word_list:
        if len(word) >= MAX_CHAR_COUNT:
            await update.message.reply_text(OVER_CHAR_COUNT_MESSAGE.format(MAX_CHAR_COUNT, MAX_CHAR_COUNT))
            return
    # generate text matches from word list
    text_matches = await run_text_match(word_list, exact_match)
    # processes text matches
    await send_text_match_response(text_matches, update.message)


'''
called when the user uses the /logo command
reverse searches the attached image and provides the user with the results
'''


async def logo_process(update, context) -> None:
    file_path = None
    # obtains image URL from message attachment
    if update.message.document:
        if 'image' in update.message.document.mime_type and "/logo" in update.message.caption:
            file_path = (await update.message.document.get_file())['file_path']
        else:
            return
    elif update.message.photo:
        if "/logo" in update.message.caption:
            max_size = 0
            max_photo = None
            for photo in update.message.photo:
                if photo.file_size > max_size:
                    max_photo = photo
                    max_size = photo.file_size
            file_path = (await max_photo.get_file())['file_path']
        else:
            return
    if file_path:
        # attempts to find matching images
        image_matches = await run_image_match(file_path)
        # if an error occured while processing image matches
        await send_image_match_response(image_matches, update.message)


'''
called when the user uses /website or /website_exact
downloads website source and then reverse searches largest images and text blobs before returning it to the user
'''


async def process_site(update, context, exact_match=False):
    if len(context.args) < 1:
        await update.message.reply_text(WEBSITE_USAGE_FORMAT)
        return
    website_url = context.args[0]
    if not validators.url(website_url):
        await update.message.reply_text(INVALID_URL_MESSAGE)
        return
    response = requests.get(website_url)
    if not response:
        await update.message.reply_text("Received Error Code: " + str(response.status_code) + " while trying to reach website. Please try again shortly. This could be because the website is behind a WAF like Cloudflare.")
        return
    else:
        # processes website source
        page_html = response.content.decode("utf-8")
        if await check_javascript_required(page_html):
            await update.message.reply_text(JAVASCRIPT_REQUIRED_MESSAGE)
            return
        soup = BeautifulSoup(page_html, "html.parser")

        text_elements = soup.findAll(text=True)
        visible_texts = await get_visible_texts_sorted(text_elements)

        for i in range(len(visible_texts)):
            for word in visible_texts[i].split(" ")[0:90]:
                if len(word) >= MAX_CHAR_COUNT:
                    visible_texts.pop(i)
                    i -= 1

        if len(visible_texts) == 0:
            await update.message.reply_text(NO_TEXT_FOUND)

        visible_texts = visible_texts[0: MAX_TEXTS_PER_WEBSITE]
        await send_website_text_match_response(visible_texts, website_url, update.message, exact_match)
        images = await get_images(soup)
        valid_images = await get_valid_images(images, website_url)
        await send_website_image_match_response(valid_images, update.message, website_url)


async def process_site_exact(update, context):
    await process_site(update, context, exact_match=True)


async def text_process_exact(update, context):
    await text_process(update, context, exact_match=True)


def main():
    application = Application.builder().token(TELEGRAM_API_KEY).build()
    application.add_handler(CommandHandler("text", text_process))
    application.add_handler(CommandHandler("text_exact", text_process_exact))
    application.add_handler(CommandHandler("website", process_site))
    application.add_handler(CommandHandler(
        "website_exact", process_site_exact))
    application.add_handler(MessageHandler(
        filters.CAPTION & ~filters.COMMAND, logo_process))
    application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
