SERP_API_KEY = open("serpapi_key.txt", "r").read().strip()
TELEGRAM_API_KEY = open("telegram_key.txt", "r").read().strip()
MAX_CHAR_COUNT = 128
MAX_WORD_COUNT = 90
MIN_CHARS_PER_WEBSITE_TEXT = 30
MIN_WORDS_PER_WEBSITE_TEXT = 10
MAX_IMAGES_PER_WEBSITE = 15
MAX_WORDS_PER_QUERY = 32
MAX_TEXTS_PER_WEBSITE = 3
OVER_CHAR_COUNT_MESSAGE = "One or more words in the text you submitted is over {} characters. Unfortunately, the maximum word length at this time is {} characters."
OVER_WORD_COUNT_MESSAGE = "The text you have submitted is over the limit of {} words per text. Please re-submit with fewer words."
TEXT_USAGE_FORMAT = "Incorrect usage of this command. Command Usage: /text Sample text to be checked goes here"
TEXT_ERROR_MESSAGE = "An error occured while checking the text you submitted. Please try again shortly. If the error continues to occur please contact the developer."
WEBSITE_ERROR_MESSAGE = "An error occured while checking some part of the website you submitted. If the error continues to occur please contact the developer."
IMAGE_ERROR_MESSAGE = "An error occured while checking an image you submitted. Please try again shortly. If the error continues to occur please contact the developer."
NO_MATCHES_MESSAGE = "Our bot couldn't find any matches. This does not guarantee the uniqueness of the text/image/contract."
WEBSITE_USAGE_FORMAT = "Incorrect usage of this command. Command Usage: /website https://example.com"
CONTRACT_USAGE_FORMAT = "Incorrect usage of this command. Comamnd Usage: /contract CONTRACT_ADDRESS"
INVALID_URL_MESSAGE = "The wesbite you entered was not in the correct format. Websites should be in the format: http://example.com"
NO_TEXT_FOUND = "Not enough text content found on the website meeting conditions for check (minimum 10 words and 30 characters per piece of text)."
CONTRACT_ERROR_MESSAGE = "An error occured while searching for matching contracts. Please check that you provided a valid contract address."
JAVASCRIPT_REQUIRED_MESSAGE = "Unfortunately websites that require JavaScript are not supported at this time.\n\nIf you believe this website does not require JavaScript, please contact the developer."
EXCLUDED_WORDS = ["twitter", "telegram", "youtube",
                  "instagram", "discord", "reddit", "tiktok"]
WHITELIST_TXT_FILE = "users.txt"
ADMIN_SPECIFY_USER = "Please specify a user or list of users to be added/removed."
