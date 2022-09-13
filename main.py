import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes
import math
import numpy as np
MAX_CHAR_COUNT = 128
MAX_WORD_COUNT = 90
OVER_CHAR_COUNT_MESSAGE = "One or more words in the text you submitted is over {} characters. Unfortunately, the maximum word length at this time is {} characters."
OVER_WORD_COUNT_MESSAGE = "The text you have submitted is over the limit of {} words per text. Please re-submit with fewer words."
TEXT_USAGE_FORMAT = "Incorrect usage of this command. Command Usage: /text Sample text to be checked goes here"

def generate_sub_lists(word_list, max_words_per_list):
    return np.array_split(word_list, math.ceil(len(word_list)/max_words_per_list))


def run_text_match(word_list):
    word_list = generate_sub_lists(word_list)


def split(a, minSize):
    numGroups = int(len(a) / minSize)
    return [a[i::numGroups] for i in range(numGroups)]


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
    text_matches = run_text_match(word_list)
    await update.message.reply_text(update.message.text)


def main():
    application = Application.builder().token(
        "5787383683:AAHT4lguZldPEp0k3uDK-48zCP4rpOJUzYs").build()
    application.add_handler(CommandHandler("text", text_process))
    application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
