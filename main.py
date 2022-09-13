import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes

MAX_CHAR_COUNT = 128
MAX_WORD_COUNT = 90
OVER_CHAR_COUNT_MESSAGE = "One or more words in the text you submitted is over {} characters. Unfortunately, the maximum word length at this time is {} characters.".format(MAX_CHAR_COUNT, MAX_CHAR_COUNT)
OVER_WORD_COUNT_MESSAGE = "The text you have submitted is over the limit of {} words per text. Please re-submit with fewer words.".format(MAX_WORD_COUNT)

async def text_process(update, context) -> None:

    word_list = context.args
    if len(word_list) >= MAX_WORD_COUNT:
        await update.message.reply_text(OVER_WORD_COUNT_MESSAGE)
        return
    for word in word_list:
        if len(word) >= MAX_CHAR_COUNT:
            await update.message.reply_text(OVER_CHAR_COUNT_MESSAGE)
            return
    
    await update.message.reply_text(update.message.text)
def main():
    application = Application.builder().token("5787383683:AAHT4lguZldPEp0k3uDK-48zCP4rpOJUzYs").build()
    application.add_handler(CommandHandler("text", text_process))
    application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())