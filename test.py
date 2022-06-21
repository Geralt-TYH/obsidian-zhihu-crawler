import os
import time
import random

from tqdm import tqdm
from main import get_single_answer_content, markdownify, get_single_post_content, get_article_urls_in_collection
from utils import filter_title_str


def testMarkdownifySingleAnswer():
    url = "https://www.zhihu.com/question/440620770/answer/2146710668"
    id = url.split('/')[-1]

    md = get_single_answer_content(url)

    downloadDir = os.path.join(os.path.expanduser("~"), "Downloads", "剪藏")
    if not os.path.exists(downloadDir):
        os.mkdir(downloadDir)
    with open(os.path.join(downloadDir, id + ".md"), "w", encoding='utf-8') as md_file:
        md_file.write(md)
    print("{} 转换成功".format(id))

def testMarkdownifySinglePost():
    url = 'https://zhuanlan.zhihu.com/p/20236294'
    md = get_single_post_content(url)
    id = url.split('/')[-1]
    with open("./" + id + ".md", "w", encoding='utf-8') as md_file:
        md_file.write(md)
    print("{} 转换成功".format(id))

def testMarkdownifyCollecton():
    collection_url = "https://www.zhihu.com/collection/146879065"
    collection_id = collection_url.split('?')[0].split('/')[-1]
    urls, titles = get_article_urls_in_collection(collection_id)

    for i in tqdm(range(len(urls))):
        content = None
        url = urls[i]
        title = titles[i]

        try:
            if url.find('zhuanlan') != -1:
                md = get_single_post_content(url)
            else:
                md = get_single_answer_content(url)
        except:
            print("发生错误内容标题：", title)
            print("发生错误内容链接：", url)

        downloadDir = os.path.join(os.path.expanduser("~"), "Downloads", "剪藏")
        if not os.path.exists(downloadDir):
            os.mkdir(downloadDir)

        with open(os.path.join(downloadDir, filter_title_str(title) + ".md"), "w", encoding='utf-8') as md_file:
            md_file.write(md)

        time.sleep(random.randint(1, 5))
    print("全部下载完毕")


if __name__ == '__main__':
    testMarkdownifySingleAnswer()