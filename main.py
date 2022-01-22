# -*- coding:utf-8 -*-
import os
import random
import sys
import time
import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import argparse

from markdownify import MarkdownConverter

parser = argparse.ArgumentParser(description='知乎文章剪藏')
parser.add_argument('collection_url', metavar='collection_url', type=str,nargs=1,
                    help='收藏夹（必须是公开的收藏夹）的网址')

class ObsidianStyleConverter(MarkdownConverter):
    """
    Create a custom MarkdownConverter that adds two newlines after an image
    """

    def chomp(self, text):
        """
        If the text in an inline tag like b, a, or em contains a leading or trailing
        space, strip the string and return a space as suffix of prefix, if needed.
        This function is used to prevent conversions like
            <b> foo</b> => ** foo**
        """
        prefix = ' ' if text and text[0] == ' ' else ''
        suffix = ' ' if text and text[-1] == ' ' else ''
        text = text.strip()
        return (prefix, suffix, text)

    def convert_img(self, el, text, convert_as_inline):
        alt = el.attrs.get('alt', None) or ''
        src = el.attrs.get('src', None) or ''
        if not os.path.exists('剪藏'):
            os.mkdir('剪藏')

        if not os.path.exists('剪藏/assets'):
            os.mkdir('剪藏/assets')

        img_content = requests.get(url=src, headers=headers).content
        img_content_name = src.split('?')[0].split('/')[-1]

        with open("./剪藏/assets/" + img_content_name, 'wb') as fp:
            fp.write(img_content)

        return '![[%s]]\n(%s)\n\n' % (img_content_name, alt)

    def convert_a(self, el, text, convert_as_inline):
        prefix, suffix, text = self.chomp(text)
        if not text:
            return ''
        href = el.get('href')
        # title = el.get('title')

        if el.get('aria-labelledby') and el.get('aria-labelledby').find('ref') > -1:
            text = text.replace('[', '[^')
            return '%s' % text

        if (el.attrs and 'data-reference-link' in el.attrs) or (el.attrs['class'] and ('ReferenceList-backLink' in el.attrs['class'])):
            text = '[^{}]: '.format(href[5])
            return '%s' % text

        return super(ObsidianStyleConverter, self).convert_a(el, text, convert_as_inline)

    def convert_li(self, el, text, convert_as_inline):
        if el and el.find('a', {'aria-label': 'back'}) is not None:
            return '%s\n' % ((text or '').strip())

        return super(ObsidianStyleConverter, self).convert_li(el, text, convert_as_inline)


def markdownify(html, **options):
    return ObsidianStyleConverter(**options).convert(html)


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Connection": "keep-alive",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.8"}


# 获取收藏夹的回答总数
def get_article_nums_of_collection(collection_id):
    """
    :param starturl: 收藏夹连接
    :return: 收藏夹的页数
    """
    try:
        collection_url = "https://www.zhihu.com/api/v4/collections/{}/items".format(collection_id)
        html = requests.get(collection_url, headers=headers)
        html.raise_for_status()

        # 页面总数
        return html.json()['paging'].get('totals')
    except:
        return None


# 解析出每个回答的具体链接
def get_article_urls_in_collection(collection_id):
    offset = 0
    limit = 20

    article_nums = get_article_nums_of_collection(collection_id)

    url_list = []
    title_list = []
    while offset < article_nums:
        collection_url = "https://www.zhihu.com/api/v4/collections/{}/items?offset={}&limit={}".format(collection_id,
                                                                                                       offset, limit)
        try:
            html = requests.get(collection_url, headers=headers)
            content = html.json()
        except:
            return None

        for el in content['data']:
            url_list.append(el['content']['url'])
            if el['content']['type'] == 'answer':
                title_list.append(el['content']['question']['title'])
            else:
                title_list.append(el['content']['title'])

        offset += limit

    return url_list,title_list


# 获得单条答案的数据
def get_single_answer_content(answer_url):
    # all_content = {}
    # question_id, answer_id = re.findall('https://www.zhihu.com/question/(\d+)/answer/(\d+)', answer_url)[0]

    html_content = requests.get(answer_url, headers=headers)
    soup = BeautifulSoup(html_content.text, "lxml")
    answer_content = soup.find('div', class_="AnswerCard").find("div", class_="RichContent-inner")
    # 去除不必要的style标签
    for el in answer_content.find_all('style'):
        el.extract()

    for el in answer_content.select('img[src*="data:image/svg+xml"]'):
        el.extract()
    # 添加html外层标签
    answer_content = html_template(answer_content)

    return answer_content


# 获取单条专栏文章的内容
def get_single_post_content(paper_url):
    html_content = requests.get(paper_url, headers=headers)
    soup = BeautifulSoup(html_content.text, "lxml")
    post_content = soup.find("div", class_="Post-RichText")
    # 去除不必要的style标签
    if post_content:
        for el in post_content.find_all('style'):
            el.extract()

        for el in post_content.select('img[src*="data:image/svg+xml"]'):
            el.extract()
    else:
        post_content = "该文章链接被404，无法直接访问"

    # 添加html外层标签
    post_content = html_template(post_content)

    return post_content


def html_template(data):
    # api content
    html = '''
        <html>
        <head>
        <body>
        %s
        </body>
        </head>
        </html>
        ''' % data
    return html



if __name__=='__main__':
    args = parser.parse_args()
    collection_url = args.collection_url[0]
    collection_id = collection_url.split('?')[0].split('/')[-1]
    urls,titles = get_article_urls_in_collection(collection_id)

    for  i in  tqdm(range(len(urls))):
        content = None
        url = urls[i]
        title = titles[i]

        if url.find('zhuanlan')!=-1:
            content = get_single_post_content(url)
        else:
            content = get_single_answer_content(url)

        md = markdownify(content, heading_style="ATX")
        id = url.split('/')[-1]

        if not os.path.exists("剪藏"):
            os.mkdir("剪藏")
        with open("./剪藏/" + title + ".md", "w", encoding='utf-8') as md_file:
            md_file.write(md)
        # print("{} 转换成功".format(id))
        time.sleep(random.randint(1,5))
    print("全部下载完毕")


def testMarkdownifySingleAnswer():
    url = "https://www.zhihu.com/question/506166712/answer/2271842801"
    content = get_single_answer_content(url)
    md = markdownify(content, heading_style="ATX")
    id = url.split('/')[-1]
    if not os.path.exists("剪藏"):
        os.mkdir("剪藏")
    with open("./剪藏/" + id + ".md", "w", encoding='utf-8') as md_file:
        md_file.write(md)
    print("{} 转换成功".format(id))

def testMarkdownifySinglePost():
    url = 'https://zhuanlan.zhihu.com/p/386395767'
    content = get_single_post_content(url)
    md = markdownify(content, heading_style="ATX")
    id = url.split('/')[-1]
    with open("./" + id + ".md", "w", encoding='utf-8') as md_file:
        md_file.write(md)
    print("{} 转换成功".format(id))


# if __name__ == '__main__':
#     testMarkdownifySingleAnswer()




