import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import math
from serpapi import GoogleSearch
from queue import Queue
import numpy as np
import re
import telegram
from urllib.parse import urlparse

SERP_API_KEY = open("api_key.txt", "r").read().strip()
TELEGRAM_API_KEY = open("telegram_key.txt", "r").read().strip()
MAX_CHAR_COUNT = 128
MAX_WORD_COUNT = 90
MAX_WORDS_PER_QUERY = 32
OVER_CHAR_COUNT_MESSAGE = "One or more words in the text you submitted is over {} characters. Unfortunately, the maximum word length at this time is {} characters."
OVER_WORD_COUNT_MESSAGE = "The text you have submitted is over the limit of {} words per text. Please re-submit with fewer words."
TEXT_USAGE_FORMAT = "Incorrect usage of this command. Command Usage: /text Sample text to be checked goes here"
TEXT_ERROR_MESSAGE = "An error occured while checking the text you submitted. Please try again shortly. If the error continues to occur please contact the developer."
NO_MATCHES_MESSAGE = "No matches found."


async def generate_sub_lists(word_list, max_words_per_list):
    return np.array_split(word_list, math.ceil(len(word_list)/max_words_per_list))


async def run_text_match(word_list, exclude_url=None):
    options = {"nfpr": 0, "filter": 0, "num": 40, "engine": "google",
               "q": "", "api_key": SERP_API_KEY, "async": True}
    search = GoogleSearch(options)
    list_of_word_lists = await generate_sub_lists(word_list, MAX_WORDS_PER_QUERY)
    search_queue = Queue()
    list_of_matches = []
    for new_list in list_of_word_lists:
        search.params_dict["q"] = " ".join(new_list)
        result = search.get_dict()
        if "error" in result and result['error'] == "Google hasn't returned any results for this query.":
            continue
        elif "error" in result:
            print("oops error: ", result["error"])
            continue
        search_queue.put(result)
    while not search_queue.empty():
        result = search_queue.get()
        search_id = result['search_metadata']['id']
        search_archived = search.get_search_archive(search_id)
        local_matches = []
        if re.search('Cached|Success',
                     search_archived['search_metadata']['status']):
            if "organic_results" in search_archived:
                for result in search_archived['organic_results']:
                    url = urlparse(result['link']).netloc
                    if url.replace("wwww.", "") == exclude_url:
                        continue
                    cached_page = result.get("cached_page_link", None)
                    if cached_page is not None and not cached_page.startswith("http"):
                        cached_page = None
                    local_matches.append((result['title'], result.get(
                        "link", None), cached_page))
            if len(local_matches) != 0:
                list_of_matches.append(local_matches)
        else:
            search_queue.put(result)
            await asyncio.sleep(1.3)
    return list_of_matches


async def run_image_match(image_url, exclude_url=None):
    options = {"engine": "google_reverse_image",
               "image_url": image_url, "api_key": SERP_API_KEY}
    search = GoogleSearch(options)
    results = search.get_dict()

    local_matches = []
    if 'error' in results:
        print(results['error'])
        return False
    if re.search('Cached|Success', results['search_metadata']['status']):
        if "image_results" in results:
            for result in results['image_results']:
                url = urlparse(result['link']).netloc
                if url.replace("wwww.", "") == exclude_url:
                    continue
                cached_page = result.get("cached_page_link", None)
                if cached_page is not None and not cached_page.startswith("http"):
                    cached_page = None
                local_matches.append((result['title'], result['link'], cached_page, result.get("thumbnail", None)))
    return local_matches


async def text_process(update, context) -> None:
    word_list = context.args
    if len(word_list) == 0:
        await update.message.reply_text(TEXT_USAGE_FORMAT)
    if len(word_list) >= MAX_WORD_COUNT:
        await update.message.reply_text(OVER_WORD_COUNT_MESSAGE.format(MAX_WORD_COUNT))
        return
    for word in word_list:
        if len(word) >= MAX_CHAR_COUNT:
            await update.message.reply_text(OVER_CHAR_COUNT_MESSAGE.format(MAX_CHAR_COUNT, MAX_CHAR_COUNT))
            return
    text_matches = await run_text_match(word_list)
    if text_matches == False:
        await update.message.reply_text(TEXT_ERROR_MESSAGE)
    if len(text_matches) == 0:
        await update.message.reply_text(NO_MATCHES_MESSAGE)
    else:
        t_count = sum([len(i) for i in text_matches])
        if len(text_matches) == 1:
            displayed_results = text_matches[0][0:5]
        elif len(text_matches) == 2:
            displayed_results = text_matches[0][0:3] + text_matches[1][0:3]
        else:
            displayed_results = text_matches[0][0:3] + \
                text_matches[1][0:3] + text_matches[2][0:3]
        message = "Matching Results (please note that results may be from a cache and some sites may no longer contain matching text):\n\n"
        for result in displayed_results:
            if result[1] is None:
                continue
            elif result[2] is None:
                message += (result[0] + "     |    <a href='" +
                            result[1] + "'>Live Page</a>\n\n")
            else:
                message += (result[0] + "     |     <a href='" + result[1] +
                            "'>Live Page</a>     |    <a href='" + result[2] + "'>Cached Page</a>\n\n")
        message += "\n\nTotal of " + str(t_count) + " matching results found."
        await update.message.reply_text(message, parse_mode="html", disable_web_page_preview=True)


async def logo_process(update, context) -> None:
    file_path = None
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
        image_matches = await run_image_match(file_path)
        if image_matches == False:
            await update.message.reply_text(TEXT_ERROR_MESSAGE)
        if len(image_matches) == 0:
            await update.message.reply_text(NO_MATCHES_MESSAGE)
        else:

            message = "Matching Results:\n\n"
            images = []
            for result in image_matches[0:5]:
                if result[1] is None:
                    continue
                elif result[2] is None:
                    message += (result[0] + "     |    <a href='" +
                                result[1] + "'>Live Page</a>\n\n")
                else:
                    message += (result[0] + "     |     <a href='" + result[1] +
                                "'>Live Page</a>     |    <a href='" + result[2] + "'>Cached Page</a>\n\n")
                if result[3] is not None:
                    images.append((result[0], result[3]))
            message += "\n\nTotal of " + \
                str(len(image_matches)) + " matching results found. Any available thumbnails will be sent shortly."
            await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
            await update.message.reply_media_group([telegram.InputMediaPhoto(i[1], caption=i[0]) for i in images])


def main():
    application = Application.builder().token(TELEGRAM_API_KEY).build()
    application.add_handler(CommandHandler("text", text_process))
    application.add_handler(MessageHandler(
        filters.CAPTION & ~filters.COMMAND, logo_process))
    application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
