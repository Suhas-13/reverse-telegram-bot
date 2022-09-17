import numpy as np
from bs4.element import Comment
import math
from PIL import ImageFile
from constants import *
import validators
from urllib import request as ulreq
from urllib.parse import urljoin
import os

def tag_visible(element):
    if element.parent.name in [
            'style', 'script', 'head', 'title', 'meta', '[document]'
    ]:
        return False
    if isinstance(element, Comment):
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


async def get_images(soup):
    return soup.findAll("img") + soup.findAll("svg")


async def check_javascript_required(page_html):
    if "need to enable JavaScript" in page_html:
        return True
    return False


async def generate_sub_lists(word_list, max_words_per_list):
    if len(word_list) == 0:
        return []
    return np.array_split(word_list, math.ceil(len(word_list)/max_words_per_list))

'''
checks image URL and returns image size if available
'''
def getsizes(url):
    try:
        file = ulreq.urlopen(url)
        size = file.headers.get("content-length")
        if size:
            size = int(size)
        p = ImageFile.Parser()
        while True:
            data = file.read(1024)
            if not data:
                break
            p.feed(data)
            if p.image:
                return size, p.image.size
        file.close()
    except Exception as e:
        print(e)
        return None
    return None


async def excluded_image(image):
    for excluded_word in EXCLUDED_WORDS:
        if excluded_word in str(image.attrs):
            return True
    return not validators.url(image.attrs['src'])


async def get_visible_texts_sorted(text_elements):
    visible_texts = filter(tag_visible, text_elements)
    visible_texts = [t.strip() for t in visible_texts]
    visible_texts = [i for i in visible_texts if i.strip() != '']
    visible_texts = [i.replace('"', '') for i in visible_texts if len(
        i) >= MIN_CHARS_PER_WEBSITE_TEXT and len(i.split(" ")) >= MIN_WORDS_PER_WEBSITE_TEXT]
    visible_texts = list(set(visible_texts))
    visible_texts.sort(key=lambda s: len(s), reverse=True)
    return visible_texts


async def get_valid_images(images, website_url):
    seen_images = set()
    valid_images = []
    for image in images:
        if 'src' not in image.attrs or not image.attrs['src']:
            continue
        if not image.attrs['src'].startswith("http"):
            image.attrs['src'] = urljoin(website_url, image.attrs['src'])
        if image.attrs['src'] in seen_images:
            continue
        if await excluded_image(image):
            continue
        image_size = getsizes(image.attrs['src'])
        if image_size and image_size[1]:
            if image_size[1][0] >= 32 and image_size[1][1] >= 32:
                image.attrs['size'] = image_size[1]
                image.attrs['total_size'] = image_size[1][0] * \
                    image_size[1][1]
                valid_images.append(image)
        seen_images.add(image.attrs['src'])
    valid_images.sort(
        key=lambda x: x.attrs['total_size'], reverse=True)
    return valid_images


