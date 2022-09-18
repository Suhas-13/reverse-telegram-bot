import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bs4 import BeautifulSoup
import validators
import requests
from constants import *
from matches import *
from whitelist import *



whitelisted_users = get_whitelisted_users(WHITELIST_TXT_FILE)
whitelisted_admins = ["blake_eth", "insertcustomname"]


def check_whitelisted(func):
    async def wrapper(update, context, *args, **kwargs):
        if update.message.from_user.username is None or update.message.from_user.username.lower().replace("@", "") not in whitelisted_users:
            await update.message.reply_text("You are not authorized to use the bot. Please contact the administrator.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def check_admin(func):
    async def wrapper(update, context,  *args, **kwargs):
        if update.message.from_user.username is None or update.message.from_user.username.lower().replace("@", "") not in whitelisted_admins:
            await update.message.reply_text("You are not authorized to add or remove users. Please contact the administrator.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def add_hourglass(func):
    async def wrapper(update, context, *args, **kwargs):
        hourglass_message = await update.message.reply_text("⌛")
        return_value = None
        try:
            return_value = await func(update, context, hourglass_message, *args, **kwargs)
        except Exception as e:
            print(e)
        await hourglass_message.delete()
        return return_value
    return wrapper

@check_whitelisted
async def start(update, context):
    await update.message.reply_text(START_MESSAGE)

@check_admin
async def add_users(update, context):
    user_list = context.args
    if len(user_list) == 0:
        await update.message.reply_text(ADMIN_SPECIFY_USER)
        return  
    add_whitelist_users(WHITELIST_TXT_FILE, whitelisted_users, user_list)
    await update.message.reply_text("User(s) have been added to the white list.")

@check_admin
async def remove_users(update, context):
    user_list = context.args
    if len(user_list) == 0:
        await update.message.reply_text(ADMIN_SPECIFY_USER)
        return  
    remove_whitelist_users(WHITELIST_TXT_FILE, whitelisted_users, user_list)
    await update.message.reply_text("User(s) have been removed to the white list.")

@check_admin
async def get_users(update, context):
    await update.message.reply_text("User list: " + "\n".join([str(i) for i in whitelisted_users]))


'''
called when the user uses the /text or /text_exact command. 
attempts up to 3 reverse search queries (based on text size) and returns results to user
'''
@check_whitelisted
@add_hourglass
async def text_process(update, context, delay_message, exact_match=False) -> None:
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



@check_whitelisted
@add_hourglass
async def contract(update, context, delay_message) -> None:
    await update.message.reply_text("Sorry, this command is currently unavailable")

'''
called when the user uses the /logo command
reverse searches the attached image and provides the user with the results
'''
@check_whitelisted
@add_hourglass
async def logo_process(update, context, delay_message) -> None:
    file_path = None
    provider = ""
    if context.args and len(context.args) != 0:
        provider = context.args[1].lower()
    elif update.message.caption and len(update.message.caption.split(" ")) >= 2:
        provider = update.message.caption.split(" ")[1]
    provider_list = ["google", "yandex"]
    if provider not in provider_list:
        await update.message.reply_text("Provider not found. Defaulting to Yandex.")
        provider = "yandex"
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
    else:
        await update.message.reply_text("Please attach an image to be checked along with the command.")
        return
    if file_path:
        # attempts to find matching images
        image_matches = await run_image_match(file_path, provider)
        # if an error occured while processing image matches
        await send_image_match_response(image_matches, update.message)


'''
called when the user uses /website or /website_exact
downloads website source and then reverse searches largest images and text blobs before returning it to the user
'''
@check_whitelisted
@add_hourglass
async def process_site(update, context, delay_message, exact_match=False):
    if len(context.args) < 1:
        await update.message.reply_text(WEBSITE_USAGE_FORMAT)
        return
    elif len(context.args) >= 2:
        provider = context.args[1]
    else:
        provider = "yandex"
    website_url = context.args[0]
    if not validators.url(website_url):
        await update.message.reply_text(INVALID_URL_MESSAGE)
        return
    try:
        response = requests.get(website_url)
    except Exception as e:
        print(e)
        await update.message.reply_text("Unable to reach the specified website. Please check if it is currently available. If the problem keeps occuring, please contact the administrator.")
        return
    if not response:
        await update.message.reply_text("Received Error Code: " + str(response.status_code) + " while trying to reach website. Please try again shortly. This could be because the website is behind a WAF like Cloudflare.")
        return
    else:
        # processes website source
        page_html = response.content.decode("utf-8", errors='ignore')
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
        await send_website_image_match_response(valid_images, update.message, website_url, provider)


async def process_site_exact(update, context):
    await process_site(update, context, exact_match=True)


async def text_process_exact(update, context):
    await text_process(update, context, exact_match=True)


def main():
    application = Application.builder().token(TELEGRAM_API_KEY).build()
    application.add_handler(CommandHandler("text", text_process))
    application.add_handler(CommandHandler("text_exact", text_process_exact))
    application.add_handler(CommandHandler("website", process_site))
    application.add_handler(CommandHandler("add_users", add_users))
    application.add_handler(CommandHandler("remove_users", remove_users))
    application.add_handler(CommandHandler("get_users", get_users))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("contract", contract))
    application.add_handler(CommandHandler(
        "website_exact", process_site_exact))
    application.add_handler(MessageHandler(
        filters.CAPTION | filters.COMMAND, logo_process))
    application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
