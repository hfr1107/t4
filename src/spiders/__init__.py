# ================================================================
#  Spider 注册表
#
#  添加 mw-movie 类新站点: 只需添加一条配置，零代码
#  添加全新类型 API:  需要在 spiders/ 写新 .py
#  entry.py 永远不需要修改
# ================================================================

REGISTRY = [
    # ---- 荐片: 独特 API ----
    {
        "name": "jianpian",
        "module": "spiders.jianpian",
        "class": "JianpianSpider",
        "urls": ["http://000.hfr1107.top/live/py/荐片.py"],
        "aliases": ["荐片"],
    },

    # ---- 金牌: mw-movie 引擎 ----
    {
        "name": "jinpai",
        "module": "spiders.mw_movie",
        "class": "MwMovieSpider",
        "urls": ["http://000.hfr1107.top/live/py/金牌.py"],
        "aliases": ["金牌"],
        "ext": {
            "site": "https://m.sdzhgt.com",
            "play_from": "老僧酿酒"
        }
    },

    # ---- 文才: mw-movie 引擎，多域名 ----
    {
        "name": "wencai",
        "module": "spiders.mw_movie",
        "class": "MwMovieSpider",
        "urls": [
            "https://7337.kstore.vip/py/文才.py",
            "https://7337.kstore.vip/py/文采.py",
            "http://000.hfr1107.top/live/py/文才.py",
            "http://000.hfr1107.top/live/py/文采.py"
        ],
        "aliases": ["文才", "文采"],
        "ext": {
            "site": "https://m.hkybqufgh.com,https://m.sizhengxt.com,https://m.9zhoukj.com,https://m.jiabaide.cn",
            "play_from": "文才"
        }
    },

    # ---- 示例: 添加新的 mw-movie 站点只需加这几行 ----
    # {
    #     "name": "newsite",
    #     "module": "spiders.mw_movie",
    #     "class": "MwMovieSpider",
    #     "urls": ["http://xxx/新站.py"],
    #     "aliases": ["新站"],
    #     "ext": {
    #         "site": "https://new-domain.com",
    #         "play_from": "新站线路"
    #     }
    # },
]