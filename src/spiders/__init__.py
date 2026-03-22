# ================================================================
#  Spider 注册表
#  
#  添加新 mw-movie 类站点：只需在 REGISTRY 添加一条，不需要写代码
#  添加全新类型站点：需要在 spiders/ 下写新的 .py 文件
#
#  entry.py 永远不需要修改
# ================================================================

REGISTRY = [
    # ---- 荐片：独特 API，用专门的 spider ----
    {
        "name": "jianpian",
        "module": "spiders.jianpian",
        "class": "JianpianSpider",
        "urls": ["https://000.hfr1107.top/live/py/荐片.py"],
        "aliases": ["荐片"],
    },

    # ---- 金牌：mw-movie 通用引擎 ----
    {
        "name": "jinpai",
        "module": "spiders.mw_movie",
        "class": "MwMovieSpider",
        "urls": ["https://000.hfr1107.top/live/py/金牌.py"],
        "aliases": ["金牌"],
        "ext": {
            "site": "https://m.sdzhgt.com"
        }
    },

    # ---- 文才：mw-movie 通用引擎，多域名测速 ----
    {
        "name": "wencai",
        "module": "spiders.mw_movie",
        "class": "MwMovieSpider",
        "urls": [
            "https://7337.kstore.vip/py/文才.py",
            "https://000.hfr1107.top/live/py/文才.py"
        ],
        "aliases": ["文才", "文采"],
        "ext": {
            "site": "https://m.hkybqufgh.com,https://m.sizhengxt.com,https://m.9zhoukj.com,https://m.jiabaide.cn"
        }
    },
]