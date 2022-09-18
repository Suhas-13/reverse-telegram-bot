from helper import *
from queue import Queue
from serpapi import GoogleSearch
from constants import *
import asyncio
from urllib.parse import urljoin
from urllib.parse import urlparse
import re
import html
import telegram


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
                        exclude_domain = str(
                            urlparse(exclude_url).netloc.replace("www.", ""))
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


async def send_text_match_response(text_matches, reply_message):
    if text_matches == False:
        await reply_message.reply_text(TEXT_ERROR_MESSAGE, parse_mode="HTML", disable_web_page_preview=True)
        return
    if len(text_matches) == 0:
        await reply_message.reply_text(NO_MATCHES_MESSAGE, parse_mode="HTML", disable_web_page_preview=True)
        return
    else:
        results_count = sum([len(i) for i in text_matches])
        # chooses how many results to show from each of max 3 queries.
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
        message += "\n\nTotal of " + \
            str(results_count) + " matching results found."
    await reply_message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)


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
                new_domain = str(url.replace("www.", ""))
                if exclude_url is not None:
                    exclude_domain = str(
                        urlparse(exclude_url).netloc.replace("www.", ""))
                if exclude_url and new_domain == exclude_domain:
                    continue
                thumbnail = result.get("thumbnail", None)
                if thumbnail:
                    thumbnail = thumbnail.get("link", None)
                original_image = result.get("original_image", None)
                if original_image:
                    original_image = original_image.get("link")
                local_matches.append(
                    (result['title'], result['link'], thumbnail, original_image))
    return local_matches


async def send_image_match_response(image_matches, reply_message):
    if image_matches == False:
        await reply_message.reply_text(IMAGE_ERROR_MESSAGE, parse_mode="HTML", disable_web_page_preview=True)
        return
    if len(image_matches) == 0:
        await reply_message.reply_text(NO_MATCHES_MESSAGE, parse_mode="HTML", disable_web_page_preview=True)
        return
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
            str(len(image_matches)) + \
            " matching results found. Any available thumbnails will be sent shortly."
        await reply_message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
        if len(images) != 0:
            telegram_images = []
            for image in images:
                try:
                    telegram_images.append(telegram.InputMediaPhoto(image[1], caption=image[0]))
                except Exception as e:
                    print(e)
            try:
                print("SENDING IMAGE")
                await reply_message.reply_media_group(telegram_images)
            except Exception as e:
                print(e)


async def send_website_image_match_response(valid_images, reply_message, website_url):
    count = 0
    for image in valid_images:
        if count == MAX_IMAGES_PER_WEBSITE:
            return
        else:
            try:
                if count >= 3:
                    min_total = 64 * 64
                elif count >= 6:
                    min_total = 80 * 80
                elif count >= 13:
                    min_total = 100 * 100
                else:
                    min_total = 32 * 32
                if image.attrs['total_size'] < min_total:
                    continue
                image_matches = await run_image_match(image.attrs['src'], website_url)
                if image_matches == False:
                    await reply_message.reply_text(WEBSITE_ERROR_MESSAGE)
                elif len(image_matches) == 0:
                    await reply_message.reply_photo(image.attrs['src'], caption=NO_MATCHES_MESSAGE)
                else:
                    message = "Matching Results:\n\n"
                    images = []
                    for result in image_matches[0:3]:
                        if result[1] is None:
                            continue
                        elif result[3] is None or result[2] is None:
                            message += (result[0] + "     |    <a href='" +
                                        result[1] + "'>Live Page</a>\n\n")
                        else:
                            message += (result[0] + "     |     <a href='" + result[1] +
                                        "'>Live Page</a>     |    <a href='" + result[3] + "'>Image</a>\n\n")
                        if result[2] is not None and result[2].startswith("http"):
                            images.append((result[0], result[2]))
                    await reply_message.reply_photo(image.attrs['src'], caption=message, parse_mode="HTML")
                    if len(images) != 0:
                        telegram_images = []
                        for i in images:
                            try:
                                telegram_images.append(
                                    telegram.InputMediaPhoto(i[1], caption=i[0]))
                            except Exception as e:
                                print(e)
                    await reply_message.reply_media_group(telegram_images)
            except Exception as e:
                print(e)
            count += 1
    await reply_message.reply_text("Finished processing website: " + website_url)


async def process_site_text_blob(text, exclude_url, exact_match=False):
    text_matches = await run_text_match(text.split(" ")[0: MAX_WORD_COUNT], exact_match, exclude_url)
    if text_matches == False:
        return None
    if len(text_matches) == 0:
        return 'Text from website: "' + str(text) + '"\n\n\nNo matching results.'
    else:
        if len(text_matches) == 1:
            displayed_results = text_matches[0][0:2]
        elif len(text_matches) == 2:
            displayed_results = text_matches[0][0:2] + text_matches[1][0:2]
        else:
            displayed_results = text_matches[0][0:2] + \
                text_matches[1][0:2] + text_matches[2][0:2]
        message = 'Text from website: "' + \
            str(text) + '"\n\n\nMatching Results:\n\n'
        for result in displayed_results:
            if result[1] is None:
                continue
            else:
                message += (result[0] + "     |    <a href='" +
                            result[1] + "'>Live Page</a>\n\n")
        return message


async def send_website_text_match_response(visible_texts, website_url, reply_message, exact_match):
    for visible_text in visible_texts:
        message = await process_site_text_blob(html.escape(visible_text), website_url, exact_match)
        if message:
            await reply_message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
