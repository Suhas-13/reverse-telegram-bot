import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import math
from serpapi import GoogleSearch
from queue import Queue
import numpy as np
import re
import telegram
from bs4 import BeautifulSoup
from bs4.element import Comment
from urllib.parse import urlparse
import validators
import requests
SERP_API_KEY = open("api_key.txt", "r").read().strip()
TELEGRAM_API_KEY = open("telegram_key.txt", "r").read().strip()
MAX_CHAR_COUNT = 128
MAX_WORD_COUNT = 90
MIN_CHARS_PER_WEBSITE_TEXT = 30
MIN_WORDS_PER_WEBSITE_TEXT = 10
MAX_WORDS_PER_QUERY = 32
MAX_TEXTS_PER_WEBSITE = 3
OVER_CHAR_COUNT_MESSAGE = "One or more words in the text you submitted is over {} characters. Unfortunately, the maximum word length at this time is {} characters."
OVER_WORD_COUNT_MESSAGE = "The text you have submitted is over the limit of {} words per text. Please re-submit with fewer words."
TEXT_USAGE_FORMAT = "Incorrect usage of this command. Command Usage: /text Sample text to be checked goes here"
TEXT_ERROR_MESSAGE = "An error occured while checking the text you submitted. Please try again shortly. If the error continues to occur please contact the developer."
NO_MATCHES_MESSAGE = "No matches found."
WEBSITE_USAGE_FORMAT = "Incorrect usage of this command. Command Usage: /website https://example.com"
INVALID_URL_MESSAGE = "The wesbite you entered was not in the correct format. Websites should be in the format: http://example.com"
NO_TEXT_FOUND = "Not enough text content found on the website meeting conditions for check (minimum 10 words and 30 characters per piece of text)."
JAVASCRIPT_REQUIRED_MESSAGE = "Unfortunately websites that require JavaScript are not supported at this time.\n\nIf you believe this website does not require JavaScript, please contact the developer."
async def generate_sub_lists(word_list, max_words_per_list):
    return np.array_split(word_list, math.ceil(len(word_list)/max_words_per_list))


async def run_text_match(word_list, exact_match, exclude_url=None):
    options = {"nfpr": 0, "filter": 0, "num": 40, "engine": "google",
               "q": "", "api_key": SERP_API_KEY, "async": True}
    search = GoogleSearch(options)
    list_of_word_lists = await generate_sub_lists(word_list, MAX_WORDS_PER_QUERY)
    search_queue = Queue()
    list_of_matches = []
    for new_list in list_of_word_lists:
        if exact_match:
            search.params_dict["q"] = '"' + " ".join(new_list) + '"'
        else:
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
                    new_domain = str(url.replace("www.", "")) 
                    if exclude_url is not None:
                        exclude_domain = str(urlparse(exclude_url).netloc.replace("www.", ""))
                    if exclude_url and new_domain == exclude_domain:
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
    options = {"engine": "yandex_images",
               "url": image_url, "api_key": SERP_API_KEY}
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
                thumbnail = result.get("thumbnail", None)
                if thumbnail:
                    thumbnail = thumbnail.get("link", None)
                original_image = result.get("original_image", None)
                if original_image:
                    original_image = original_image.get("link")
                local_matches.append((result['title'], result['link'], thumbnail, original_image))
    return local_matches


async def text_process(update, context, exact_match = False) -> None:
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
    text_matches = await run_text_match(word_list, exact_match)
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
                elif result[3] is None or result[2] is None:
                    message += (result[0] + "     |    <a href='" +
                                result[1] + "'>Live Page</a>\n\n")
                else:
                    message += (result[0] + "     |     <a href='" + result[1] +
                                "'>Live Page</a>     |    <a href='" + result[3] + "'>Image</a>    |    <a href='" + result[2] + "'>Thumbnail</a>\n\n")
                if result[2] is not None and result[2].startswith("http"):
                    images.append((result[0], result[2]))
            message += "\n\nTotal of " + \
                str(len(image_matches)) + " matching results found. Any available thumbnails will be sent shortly."
            await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
            if len(images) != 0:
                telegram_images = []
                for i in images:
                    try:
                        telegram_images.append(telegram.InputMediaPhoto(i[1], caption=i[0]))
                    except Exception as e:
                        print(e)
                try:
                    await update.message.reply_media_group(telegram_images)
                except Exception as e:
                    print(e)

def tag_visible(element):
    if element.parent.name in [
            'style', 'script', 'head', 'title', 'meta', '[document]'
    ]:
        return False
    if isinstance(element, Comment):
        print(element.text)
        return False
    return True
def comments_finder(element):
    if isinstance(element, Comment):
        return True

    if element.parent.name in [
            'style', 'script', 'head', 'title', 'meta', '[document]'
    ]:
        return False
    
    return False

async def javascript_required(page_html):
    if "need to enable JavaScript" in page_html:
        return True
    return False

async def process_website_text(text, exclude_url, exact_match = False):
    text_matches = await run_text_match(text.split(" ")[0: MAX_WORD_COUNT], exact_match, exclude_url)
    if text_matches == False:
        return None
    if len(text_matches) == 0:
        return 'Text from website: "' + str(text) + '"\n\n\nNo matching results.'
    else:
        t_count = sum([len(i) for i in text_matches])
        if len(text_matches) == 1:
            displayed_results = text_matches[0][0:5]
        elif len(text_matches) == 2:
            displayed_results = text_matches[0][0:3] + text_matches[1][0:3]
        else:
            displayed_results = text_matches[0][0:3] + \
                text_matches[1][0:3] + text_matches[2][0:3]
        message = 'Text from website: "' + str(text) + '"\n\n\nMatching Results (please note that results may be from a cache and some sites may no longer contain matching text):\n\n'
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
        return message
async def process_site(update, context, exact_match = False):
    if len(context.args) < 1:
        await update.message.reply_text(WEBSITE_USAGE_FORMAT)
        return
    website_url = context.args[0]
    if not validators.url(website_url):
        await update.message.reply_text(INVALID_URL_MESSAGE)
        return
    response = requests.get(website_url)
    if not response:
        await update.message.reply_text("Received Error Code: " + str(response.status_code) + " while trying to reach website. Please try again shortly.")
        return
    else:
        page_html = response.content.decode("utf-8")
        if await javascript_required(page_html):
            await update.message.reply_text(JAVASCRIPT_REQUIRED_MESSAGE)
            return
        soup = BeautifulSoup(page_html, "html.parser")
        text_elements = soup.findAll(text=True)
        visible_texts = filter(tag_visible, text_elements)
        visible_texts = [t.strip() for t in visible_texts]
        visible_texts = [i for i in visible_texts if i.strip() != '']
        visible_texts = [i.replace('"', '') for i in visible_texts if len(i) >= MIN_CHARS_PER_WEBSITE_TEXT and len(i.split(" ")) >= MIN_WORDS_PER_WEBSITE_TEXT]
        visible_texts = list(set(visible_texts))
        visible_texts.sort(key=lambda s: len(s))
        for i in range(len(visible_texts)):
            for word in visible_texts[i].split(" ")[0:90]:
                if len(word) >= MAX_CHAR_COUNT:
                    visible_texts.pop(i)
                    i-=1
        visible_texts.reverse()
        if len(visible_texts) == 0:
            await update.message.reply_text(NO_TEXT_FOUND)
        visible_texts = visible_texts[0: MAX_TEXTS_PER_WEBSITE]
        for visible_text in visible_texts:
            message = await process_website_text(visible_text, website_url, exact_match)
            if message:
                await update.message.reply_text(message, parse_mode="html", disable_web_page_preview=True)
        
        comments = filter(comments_finder, text_elements)
        
async def process_site_exact(update, context):
    await process_site(update, context, exact_match = True)

async def text_process_exact(update, context):
    await text_process(update, context, exact_match = True)
def main():
    application = Application.builder().token(TELEGRAM_API_KEY).build()
    application.add_handler(CommandHandler("text", text_process))
    application.add_handler(CommandHandler("text_exact", text_process_exact))
    application.add_handler(CommandHandler("website", process_site))
    application.add_handler(CommandHandler("website_exact", process_site_exact))
    application.add_handler(MessageHandler(
        filters.CAPTION & ~filters.COMMAND, logo_process))
    application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
