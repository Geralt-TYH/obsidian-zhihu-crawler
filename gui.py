#!/usr/bin/python3
import re
from tkinter import *
from tkinter.scrolledtext import ScrolledText
from main import get_article_urls_in_collection,get_single_post_content,get_single_answer_content,markdownify
from tqdm import tqdm
import os
import time
import random
import sys
from utils import filter_title_str

class myStdout():	# 重定向类
    def __init__(self):
    	# 将其备份
        self.stdoutbak = sys.stdout
        self.stderrbak = sys.stderr
        # 重定向
        sys.stdout = self
        sys.stderr = self

    def flush(self):
        pass

    def write(self, info):
        # info信息即标准输出sys.stdout和sys.stderr接收到的输出信息
        contents.insert(END, info+'\n')	# 在多行文本控件最后一行插入print信息
        contents.update()	# 更新显示的文本，不加这句插入的信息无法显示
        contents.see(END)	# 始终显示最后一行，不加这句，当文本溢出控件最后一行时，不会自动显示最后一行

    def restoreStd(self):
        # 恢复标准输出
        sys.stdout = self.stdoutbak
        sys.stderr = self.stderrbak

def validate_url(url):
    url_regex = r'^((http|https):\/\/)?(www\.)?zhihu\.com.*'
    matchObj = re.match(url_regex,url)
    if matchObj:
        return True
    else:
        return False

def clip():
    collection_url = entry_url.get()

    if not validate_url(collection_url):
        print("非知乎网址，其他形式不支持")
        return
    collection_id = collection_url.split('?')[0].split('/')[-1]

    urls, titles = get_article_urls_in_collection(collection_id)

    for  i in  tqdm(range(len(urls))):
        time.sleep(random.randint(1, 5))

        content = None
        url = urls[i]
        title = titles[i]

        if url.find('zhuanlan')!=-1:
            content = get_single_post_content(url)
        else:
            content = get_single_answer_content(url)

        md = markdownify(content, heading_style="ATX")
        id = url.split('/')[-1]

        downloadDir = os.path.join(os.path.expanduser("~"), "Downloads", "剪藏")
        if not os.path.exists(downloadDir):
            os.mkdir(downloadDir)

        with open(os.path.join(downloadDir,filter_title_str(title) + ".md") , "w", encoding='utf-8') as md_file:
            md_file.write(md)

    print("全部下载完毕")


mystd = myStdout()
root = Tk()
root.geometry("400x450")
root.title("zhihu crawler")
frame = Frame(root)
frame.pack()

contents = ScrolledText(root)
contents.pack(side=BOTTOM, expand=True, fill=BOTH)

# 输入框
entry_url = Entry(root, text="url")
entry_url.pack( side = LEFT,expand=True, fill=X)

btn = Button(root,text='开始剪藏',command=clip)
btn.pack(side=RIGHT)

# Tkinter主事件循环
root.mainloop()

# 恢复标准输出
mystd.restoreStd()