from .jianpian import JianpianSpider
from .jinpai import JinpaiSpider

# 注册表：name -> Spider 类实例
SPIDER_REGISTRY = {}


def init_spiders():
    global SPIDER_REGISTRY
    SPIDER_REGISTRY = {
        "jianpian": JianpianSpider(),
        "jinpai": JinpaiSpider(),
    }
    return SPIDER_REGISTRY


# URL -> name 映射（用于 ?url=xxx 方式查找）
URL_TO_NAME = {
    "http://000.hfr1107.top/live/py/荐片.py": "jianpian",
    "http://000.hfr1107.top/live/py/金牌.py": "jinpai",
}