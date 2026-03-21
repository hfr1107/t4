from js import Response, URL, Headers, fetch
import json
from urllib.parse import unquote

from .spider_base import json_response, decode_ext, fetch_raw
from .spiders import init_spiders, URL_TO_NAME

# 初始化所有 spider
SPIDERS = init_spiders()

# JSON 配置缓存
_json_config_cache = {"data": None, "ts": 0}
JSON_CONFIG_URL = "http://000.hfr1107.top/live/py.json"


async def _load_json_config():
    """加载远程 JSON 配置并更新 URL_TO_NAME"""
    import time
    now = time.time()
    # 缓存 5 分钟
    if _json_config_cache["data"] and (now - _json_config_cache["ts"]) < 300:
        return _json_config_cache["data"]
    try:
        status, text = await fetch_raw(JSON_CONFIG_URL)
        if status == 200 and text:
            config = json.loads(text)
            _json_config_cache["data"] = config
            _json_config_cache["ts"] = now
            # 动态更新 URL_TO_NAME
            for item in config:
                if item.get("url") and item.get("name"):
                    URL_TO_NAME[item["url"]] = item["name"]
            return config
    except Exception:
        pass
    return _json_config_cache.get("data") or []


def _resolve_spider_name(path, url_obj):
    """
    从请求路径或 url 参数解析出 spider 名称
    
    支持：
    1. /jianpian?... → name = "jianpian"
    2. /荐片.py?... → 兼容旧路径，查找 URL_TO_NAME
    3. ?url=http://xxx/荐片.py&... → 从 url 参数查找
    """
    # 方式3: ?url= 参数
    url_param = url_obj.searchParams.get("url")
    if url_param:
        url_param = unquote(url_param)
        # 精确匹配
        name = URL_TO_NAME.get(url_param)
        if name:
            return name
        # 模糊匹配：尝试去掉尾部 & 等
        url_clean = url_param.rstrip('&').rstrip('?')
        name = URL_TO_NAME.get(url_clean)
        if name:
            return name
        # 遍历查找
        for registered_url, n in URL_TO_NAME.items():
            if url_clean in registered_url or registered_url in url_clean:
                return n
        return None

    # 方式1: /jianpian 或 /jianpian/xxx
    # 方式2: /荐片.py
    clean_path = path.strip('/')
    if not clean_path:
        return None

    # 取第一段路径
    first_segment = clean_path.split('/')[0]

    # 去掉 .py 后缀
    if first_segment.endswith('.py'):
        first_segment_base = first_segment[:-3]
    else:
        first_segment_base = first_segment

    # 直接匹配 spider 名称
    if first_segment_base in SPIDERS:
        return first_segment_base

    # 查找 URL_TO_NAME 中文件名匹配
    for url, name in URL_TO_NAME.items():
        # 从 URL 提取文件名
        url_filename = url.rstrip('/').split('/')[-1]
        if url_filename.endswith('.py'):
            url_filename_base = url_filename[:-3]
        else:
            url_filename_base = url_filename
        if first_segment_base == url_filename_base:
            return name

    return None


async def _handle_spider_request(spider, url_obj):
    """通用 spider 请求处理"""
    # 读取参数
    ac = url_obj.searchParams.get("ac")
    t = url_obj.searchParams.get("t")
    tid = url_obj.searchParams.get("tid")
    pg = url_obj.searchParams.get("pg")
    ext = url_obj.searchParams.get("ext")
    extend = url_obj.searchParams.get("extend")
    ids = url_obj.searchParams.get("ids")
    flag = url_obj.searchParams.get("flag")
    play = url_obj.searchParams.get("play")
    wd = url_obj.searchParams.get("wd")
    quick = url_obj.searchParams.get("quick")
    f_val = url_obj.searchParams.get("filter")

    # 1. 搜索
    if wd is not None and wd != "":
        result = await spider.searchContent(wd, quick or "", pg or "1")
        return json_response(result)

    # 2. 播放
    if play is not None:
        # 优先使用异步播放方法（如金牌需要签名）
        if hasattr(spider, 'playerContentAsync'):
            result = await spider.playerContentAsync(flag or "", play)
        else:
            result = spider.playerContent(flag or "", play)
        return json_response(result)

    # 3. 详情
    if ac == "detail" and ids:
        ids_list = [i.strip() for i in ids.split(",") if i.strip()]
        if not ids_list:
            return json_response({"error": "ids为空"}, 400)
        result = await spider.detailContent(ids_list)
        return json_response(result)

    # 4. 分类列表
    cat_id = t or tid
    if cat_id:
        ext_str = ext or extend or ""
        extend_obj = decode_ext(ext_str)
        result = await spider.categoryContent(
            cat_id, pg or "1", f_val or "", extend_obj
        )
        return json_response(result)

    # 5. 推荐
    if ac == "homeVideo":
        result = await spider.homeVideoContent()
        return json_response(result)

    # 6. 首页（默认）
    result = spider.homeContent(True)
    try:
        hv = await spider.homeVideoContent()
        result['list'] = hv.get('list', [])
    except Exception:
        result['list'] = []
    return json_response(result)


async def handle_debug(url_obj):
    """调试端点"""
    info = {
        "worker_alive": True,
        "registered_spiders": list(SPIDERS.keys()),
        "url_to_name": {k: v for k, v in URL_TO_NAME.items()},
    }
    # 加载远程配置
    try:
        config = await _load_json_config()
        info["json_config"] = config
    except Exception as e:
        info["json_config_error"] = str(e)

    return json_response(info)


async def handle_list_spiders():
    """列出所有可用的 spider"""
    config = await _load_json_config()
    spiders_info = []
    for name, spider in SPIDERS.items():
        spiders_info.append({
            "name": name,
            "available": True
        })
    return json_response({
        "spiders": spiders_info,
        "json_config": config
    })


async def on_fetch(request, env):
    url = URL.new(request.url)
    path = url.pathname

    # OPTIONS
    if request.method == "OPTIONS":
        h = Headers.new()
        h.set("Access-Control-Allow-Origin", "*")
        h.set("Access-Control-Allow-Methods", "GET, OPTIONS")
        return Response.new("", status=204, headers=h)

    # /debug
    if path == "/debug" or path.endswith("/debug"):
        return await handle_debug(url)

    # /list — 列出所有 spider
    if path == "/list":
        return await handle_list_spiders()

    # 加载远程 JSON 配置（更新 URL_TO_NAME）
    await _load_json_config()

    try:
        # 解析 spider 名称
        spider_name = _resolve_spider_name(path, url)

        if spider_name and spider_name in SPIDERS:
            spider = SPIDERS[spider_name]
            return await _handle_spider_request(spider, url)

        # 没有匹配到任何 spider
        # 如果路径为空或根路径，显示帮助
        if not path or path == '/':
            # 检查是否有 url 参数但未匹配
            url_param = url.searchParams.get("url")
            if url_param:
                return json_response({
                    "error": f"未找到匹配的spider",
                    "url_param": unquote(url_param),
                    "registered": list(SPIDERS.keys()),
                    "hint": "请确认该URL已在JSON配置或URL_TO_NAME中注册"
                }, 404)
            
            return json_response({
                "message": "TVBox Spider Proxy",
                "available_spiders": list(SPIDERS.keys()),
                "usage": [
                    "/jianpian?filter=true",
                    "/jinpai?filter=true",
                    "?url=http://xxx/荐片.py&filter=true",
                    "/debug",
                    "/list"
                ]
            })

        return json_response({
            "error": f"未找到spider: {path}",
            "available": list(SPIDERS.keys())
        }, 404)

    except Exception as e:
        return json_response({"error": str(e)}, 500)