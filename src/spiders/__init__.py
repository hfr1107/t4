# ================================================================
#  Spider 注册表
#  添加新 spider: 
#    1. 在 spiders/ 目录添加 xxx.py 文件
#    2. 在下面 REGISTRY 添加一条
#  删除 spider:
#    1. 删除 .py 文件
#    2. 删除 REGISTRY 中对应条目
#  主程序 entry.py 永远不需要修改
# ================================================================

REGISTRY = [
    {
        "name": "jianpian",
        "module": "spiders.jianpian",
        "class": "JianpianSpider",
        "urls": ["http://000.hfr1107.top/live/py/荐片.py"],
        "aliases": ["荐片"]
    },
    {
        "name": "jinpai",
        "module": "spiders.jinpai",
        "class": "JinpaiSpider",
        "urls": ["http://000.hfr1107.top/live/py/金牌.py"],
        "aliases": ["金牌"]
    },
    {
        "name": "wencai",
        "module": "spiders.jinpai",
        "class": "JinpaiSpider",
        "urls": ["http://000.hfr1107.top/live/py/文才.py"],
        "aliases": ["文才"]
    },
]