# ================================================================
#  Spider 注册表
#
#  添加 mw-movie 类站点: 加一条配置即可
#  添加新类型: 写 .py 文件 + 加配置
#  删除: 删配置 + 删文件 → 推送
# ================================================================

REGISTRY = [
    {
        "name": "jianpian",
        "module": "spiders.jianpian",
        "class": "JianpianSpider",
        "urls": ["http://000.hfr1107.top/live/py/荐片.py"],
        "aliases": ["荐片"],
    },
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
    {
        "name": "wencai",
        "module": "spiders.mw_movie",
        "class": "MwMovieSpider",
        "urls": ["http://000.hfr1107.top/live/py/文才.py"],
        "aliases": ["文才"],
        "ext": {
            "site": "https://m.hkybqufgh.com,https://m.sizhengxt.com,https://m.9zhoukj.com,https://m.jiabaide.cn",
            "play_from": "文才"
        }
    },
]
