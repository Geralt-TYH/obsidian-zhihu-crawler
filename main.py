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
from utils import filter_title_str
import json

from markdownify import MarkdownConverter

parser = argparse.ArgumentParser(description='知乎文章剪藏')
parser.add_argument('collection_url', metavar='collection_url', type=str,nargs=1,
                    help='收藏夹（支持公开和私密收藏夹）的网址')

# 读取cookies
def load_cookies():
    try:
        with open('cookies.json', 'r') as f:
            cookies_list = json.load(f)
        cookies_dict = {}
        for cookie in cookies_list:
            cookies_dict[cookie['name']] = cookie['value']
        return cookies_dict
    except FileNotFoundError:
        print("未找到cookies.json文件，将使用无登录模式访问（部分内容可能无法获取）")
        return {}

cookies = load_cookies()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Connection": "keep-alive",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.8"
}

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

        downloadDir = os.path.join(os.path.expanduser("~"), "Downloads", "剪藏")
        if not os.path.exists(downloadDir):
            os.mkdir(downloadDir)
        assetsDir = os.path.join(downloadDir,'assets')
        if not os.path.exists(assetsDir):
            os.mkdir(assetsDir)

        img_content = requests.get(url=src, headers=headers, cookies=cookies).content
        img_content_name = src.split('?')[0].split('/')[-1]

        imgPath = os.path.join(assetsDir,img_content_name)
        with open(imgPath, 'wb') as fp:
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
        if (el.attrs and 'data-reference-link' in el.attrs) or ('class' in el.attrs and ('ReferenceList-backLink' in el.attrs['class'])):
            text = '[^{}]: '.format(href[5])
            return '%s' % text

        return super(ObsidianStyleConverter, self).convert_a(el, text, convert_as_inline)

    def convert_li(self, el, text, convert_as_inline):
        if el and el.find('a', {'aria-label': 'back'}) is not None:
            return '%s\n' % ((text or '').strip())

        return super(ObsidianStyleConverter, self).convert_li(el, text, convert_as_inline)


def markdownify(html, **options):
    return ObsidianStyleConverter(**options).convert(html)


# 获取收藏夹的回答总数
def get_article_nums_of_collection(collection_id):
    """
    :param starturl: 收藏夹连接
    :return: 收藏夹的页数
    """
    try:
        collection_url = "https://www.zhihu.com/api/v4/collections/{}/items".format(collection_id)
        html = requests.get(collection_url, headers=headers, cookies=cookies)
        html.raise_for_status()

        # 页面总数
        return html.json()['paging'].get('totals')
    except:
        return None


# 解析出每个回答的具体链接
def get_article_urls_in_collection(collection_id):
    collection_id =collection_id.replace('\n','')

    offset = 0
    limit = 20

    article_nums = get_article_nums_of_collection(collection_id)

    url_list = []
    title_list = []
    while offset < article_nums:
        collection_url = "https://www.zhihu.com/api/v4/collections/{}/items?offset={}&limit={}".format(collection_id,
                                                                                                       offset, limit)
        try:
            html = requests.get(collection_url, headers=headers, cookies=cookies)
            content = html.json()
        except:
            return None

        for el in content['data']:
            url_list.append(el['content']['url'])
            try:
                if el['content']['type'] == 'answer':
                    title_list.append(el['content']['question']['title'])
                else:
                    title_list.append(el['content']['title'])
            except:
                print('********')
                print('TBD 非回答, 非专栏, 想法类收藏暂时无法处理')
                for k, v in el['content'].items():
                    if k in ['type', 'url']:
                        print(k, v)
                print('********')
                url_list.pop()

        offset += limit

    return url_list, title_list


# 获得单条答案的数据
def get_single_answer_content(answer_url):
    # all_content = {}
    # question_id, answer_id = re.findall('https://www.zhihu.com/question/(\d+)/answer/(\d+)', answer_url)[0]

    html_content = requests.get(answer_url, headers=headers, cookies=cookies)
    soup = BeautifulSoup(html_content.text, "lxml")
    try:
        answer_content = soup.find('div', class_="AnswerCard").find("div", class_="RichContent-inner")
    except:
        print(answer_url, 'failed')
        return -1
    # 去除不必要的style标签
    for el in answer_content.find_all('style'):
        el.extract()

    for el in answer_content.select('img[src*="data:image/svg+xml"]'):
        el.extract()
    
    for el in answer_content.find_all('a'): # 处理回答中的卡片链接
        aclass = el.get('class')
        if isinstance(aclass, list):
            if aclass[0] == 'LinkCard':
                linkcard_name = el.get('data-text')
                el.string = linkcard_name if linkcard_name is not None else el.get('href')
        else:
            pass
        try:
            if el.get('href').startswith('mailto'): # 特殊bug, 正文的aaa@bbb.ccc会被识别为邮箱, 嵌入<a href='mailto:xxx'>中, markdown转换时会报错
                el.name = 'p'
        except:
            print(answer_url, el) # 一些广告卡片, 不需要处理
        
    # 添加html外层标签
    answer_content = html_template(answer_content)

    return answer_content


# 获取单条专栏文章的内容
def get_single_post_content(paper_url):
    html_content = requests.get(paper_url, headers=headers, cookies=cookies)
    soup = BeautifulSoup(html_content.text, "lxml")
    post_content = soup.find("div", class_="Post-RichText")
    # 去除不必要的style标签
    if post_content:
        for el in post_content.find_all('style'):
            el.extract()

        for el in post_content.select('img[src*="data:image/svg+xml"]'):
            el.extract()
        
        for el in post_content.find_all('a'): # 处理专栏文章中的卡片链接
            aclass = el.get('class')
            if isinstance(aclass, list):
                if aclass[0] == 'LinkCard':
                    linkcard_name = el.get('data-text')
                    el.string = linkcard_name if linkcard_name is not None else el.get('href')
            else:
                pass
            try:
                if el.get('href').startswith('mailto'): # 特殊bug, 正文的aaa@bbb.ccc会被识别为邮箱, 嵌入<a href='mailto:xxx'>中, markdown转换时会报错
                    el.name = 'p'
            except:
                print(paper_url, el)
    else:
        post_content = "该文章链接被404, 无法直接访问"

    # 添加html外层标签
    post_content = html_template(post_content)

    return post_content


def html_template(data):
    # api content
    html = '''
        <html>
        <head>
        </head>
        <body>
        %s
        </body>
        </html>
        ''' % data
    return html



if __name__=='__main__':
    args = parser.parse_args()
    collection_url = args.collection_url[0]
    collection_id = collection_url.split('?')[0].split('/')[-1]
    urls, titles = get_article_urls_in_collection(collection_id)

    assert len(urls) == len(titles), '地址标题列表长度不一致'

    print('共获取 %d 篇可导出回答或专栏' % len(urls))

    downloadDir = os.path.join(os.path.expanduser("~"), "Downloads", "剪藏")
    if not os.path.exists(downloadDir):
        os.mkdir(downloadDir)

    for  i in tqdm(range(len(urls))):
        content = None
        url = urls[i]
        title = titles[i]

        if os.path.exists(os.path.join(downloadDir, filter_title_str(title) + ".md")): # 跳过已经保存的文件
            continue

        if url.find('zhuanlan') != -1:
            content = get_single_post_content(url)
        else:
            content = get_single_answer_content(url)
        
        if content == -1:
            print(url, 'get content failed.')
            continue
        
        try:
            md = markdownify(content, heading_style="ATX")
            md = '> %s\n' % url + md
            id = url.split('/')[-1]

            with open(os.path.join(downloadDir, filter_title_str(title) + ".md"), "w", encoding='utf-8') as md_file:
                md_file.write(md)
            # print("{} 转换成功".format(id))
            time.sleep(random.randint(1,5))
        except Exception as e:
            print(content)
            print(e)
            print(url, 'error')

    print("全部下载完毕")

# def testMarkdownifySingleAnswer():
#     url = "https://www.zhihu.com/question/506166712/answer/2271842801"
#     content = get_single_answer_content(url)
#     md = markdownify(content, heading_style="ATX")
#     id = url.split('/')[-1]
#
#     downloadDir = os.path.join(os.path.expanduser("~"), "Downloads", "剪藏")
#     if not os.path.exists(downloadDir):
#         os.mkdir(downloadDir)
#     with open(os.path.join(downloadDir, id + ".md"), "w", encoding='utf-8') as md_file:
#         md_file.write(md)
#     print("{} 转换成功".format(id))
#
# def testMarkdownifySinglePost():
#     url = 'https://zhuanlan.zhihu.com/p/386395767'
#     content = get_single_post_content(url)
#     md = markdownify(content, heading_style="ATX")
#     id = url.split('/')[-1]
#     with open("./" + id + ".md", "w", encoding='utf-8') as md_file:
#         md_file.write(md)
#     print("{} 转换成功".format(id))
#
#
# # if __name__ == '__main__':
# #     testMarkdownifySingleAnswer()
#



