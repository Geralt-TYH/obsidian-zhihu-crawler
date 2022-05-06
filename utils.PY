import re

def filter_title_str(str):
    filterStr = re.sub("[\/\\\\\"<>\|]",' ',str)
    filterStr = re.sub("\?", '？', filterStr)
    filterStr = re.sub(":", '：', filterStr)
    return filterStr

