from js import Response, URL, Headers, fetch
import json
import base64
import time
from urllib.parse import quote, unquote

# ================================================================
#  通用工具（spider 通过 import entry 使用）
# ================================================================

def build_url(base, params=None):
    if not params:
        return base
    parts = []
    for k, v in params.items():
        if v is None:
            continue
        parts.append(f"{quote(str(k))}={quote(str(v))}")
    if not parts:
        return base
    sep = '&' if '?' in base else '?'
    return base + sep + '&'.join(parts)


async def fetch_raw(url, headers_dict=None):
    if headers_dict:
        h = Headers.new()
        for k, v in headers_dict.items():
            h.set(k, v)
        resp = await fetch(url, headers=h)
    else:
        resp = await fetch(url)
    text = await resp.text()
    return resp.status, text


async def api_json(url, params=None, headers_dict=None):
    full_url = build_url(url, params)
    status, text = await fetch_raw(full_url, headers_dict)
    if not text or not text.strip():
        raise Exception(f"上游空响应 HTTP {status} | {full_url}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise Exception(
            f"上游非JSON HTTP {status} | URL: {full_url} | "
            f"前200字: {text[:200]}"
        )


def decode_ext(ext_str):
    if not ext_str:
        return {}
    try:
        pad = len(ext_str) % 4
        if pad:
            ext_str += '=' * (4 - pad)
        decoded = base64.b64decode(ext_str).decode('utf-8')
        return json.loads(decoded)
    except Exception:
        return {}


def json_response(data, status=200):
    h = Headers.new()
    h.set("Content-Type", "application/json; charset=utf-8")
    h.set("Access-Control-Allow-Origin", "*")
    h.set("Access-Control-Allow-Methods", "GET, OPTIONS")
    body = json.dumps(data, indent=2, ensure_ascii=False)
    return Response.new(body, status=status, headers=h)


# ================================================================
#  Spider 注册
# ================================================================

SPIDERS = {}
URL_TO_NAME = {}
ALIAS_TO_NAME = {}
_init_errors = []


def _try_register(cfg):
    name = cfg.get('name', '')
    module_name = cfg.get('module', '')
    class_name = cfg.get('class', '')
    urls = cfg.get('urls', [])
    aliases = cfg.get('aliases', [])
    ext = cfg.get('ext')

    if not name or not module_name or not class_name:
        return
    try:
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name)
        try:
            instance = cls(ext=ext)
        except TypeError:
            instance = cls()
        SPIDERS[name] = instance
        for u in urls:
            URL_TO_NAME[u] = name
        for a in aliases:
            ALIAS_TO_NAME[a] = name
    except Exception as e:
        _init_errors.append(f"{name}: {e}")


def _auto_discover():
    try:
        import spiders as _sp
        if hasattr(_sp, 'REGISTRY'):
            for cfg in _sp.REGISTRY:
                _try_register(cfg)
    except Exception as e:
        _init_errors.append(f"auto_discover: {e}")


_auto_discover()


# ================================================================
#  远程 JSON 配置
# ================================================================

_json_cache = {"data": None, "ts": 0}
JSON_CONFIG_URL = "http://000.hfr1107.top/live/py.json"


async def _load_json_config():
    now = time.time()
    if _json_cache["data"] and (now - _json_cache["ts"]) < 300:
        return _json_cache["data"]
    try:
        status, text = await fetch_raw(JSON_CONFIG_URL)
        if status == 200 and text:
            config = json.loads(text)
            _json_cache["data"] = config
            _json_cache["ts"] = now
            for item in config:
                u = item.get("url", "")
                n = item.get("name", "")
                if u and n:
                    URL_TO_NAME[u] = n
            return config
    except Exception:
        pass
    return _json_cache.get("data") or []


# ================================================================
#  路由
# ================================================================

def _resolve_spider_name(path, url_obj):
    url_param = url_obj.searchParams.get("url")
    if url_param:
        url_clean = unquote(url_param).rstrip('&').rstrip('?')
        name = URL_TO_NAME.get(url_clean)
        if name:
            return name
        for reg_url, n in URL_TO_NAME.items():
            if url_clean in reg_url or reg_url in url_clean:
                return n
        fn = url_clean.rstrip('/').split('/')[-1]
        fn_base = fn[:-3] if fn.endswith('.py') else fn
        if fn_base in SPIDERS:
            return fn_base
        if fn_base in ALIAS_TO_NAME:
            return ALIAS_TO_NAME[fn_base]
        return None

    clean_path = path.strip('/')
    if not clean_path or clean_path in ('debug', 'list'):
        return None
    first = clean_path.split('/')[0]
    base = first[:-3] if first.endswith('.py') else first
    if base in SPIDERS:
        return base
    if base in ALIAS_TO_NAME:
        return ALIAS_TO_NAME[base]
    for url, name in URL_TO_NAME.items():
        fn = url.rstrip('/').split('/')[-1]
        fn_base = fn[:-3] if fn.endswith('.py') else fn
        if base == fn_base:
            return name
    return None


# ================================================================
#  通用请求分发
# ================================================================

async def _handle_spider(spider, url_obj):
    ac       = url_obj.searchParams.get("ac")
    t        = url_obj.searchParams.get("t")
    tid      = url_obj.searchParams.get("tid")
    pg       = url_obj.searchParams.get("pg")
    ext      = url_obj.searchParams.get("ext")
    extend_p = url_obj.searchParams.get("extend")
    ids      = url_obj.searchParams.get("ids")
    flag     = url_obj.searchParams.get("flag")
    play     = url_obj.searchParams.get("play")
    wd       = url_obj.searchParams.get("wd")
    quick    = url_obj.searchParams.get("quick")
    f_val    = url_obj.searchParams.get("filter")

    # 搜索
    if wd is not None and wd != "":
        result = await spider.searchContent(wd, quick or "", pg or "1")
        return json_response(result)

    # 播放
    if play is not None:
        if hasattr(spider, 'playerContentAsync'):
            result = await spider.playerContentAsync(flag or "", play)
        else:
            result = spider.playerContent(flag or "", play)
        return json_response(result)

    # 详情
    if ac == "detail" and ids:
        ids_list = [i.strip() for i in ids.split(",") if i.strip()]
        if not ids_list:
            return json_response({"error": "ids为空"}, 400)
        result = await spider.detailContent(ids_list)
        return json_response(result)

    # 分类
    cat_id = t or tid
    if cat_id:
        ext_str = ext or extend_p or ""
        extend_obj = decode_ext(ext_str)
        result = await spider.categoryContent(
            cat_id, pg or "1", f_val or "", extend_obj
        )
        return json_response(result)

    # 推荐
    if ac == "homeVideo":
        result = await spider.homeVideoContent()
        return json_response(result)

    # 首页
    import asyncio
    if asyncio.iscoroutinefunction(spider.homeContent):
        result = await spider.homeContent(True)
    else:
        result = spider.homeContent(True)

    try:
        hv = await spider.homeVideoContent()
        result['list'] = hv.get('list', [])
    except Exception:
        result['list'] = []
    return json_response(result)


# ================================================================
#  入口
# ================================================================

async def on_fetch(request, env):
    url = URL.new(request.url)
    path = url.pathname

    if request.method == "OPTIONS":
        h = Headers.new()
        h.set("Access-Control-Allow-Origin", "*")
        h.set("Access-Control-Allow-Methods", "GET, OPTIONS")
        return Response.new("", status=204, headers=h)

    if path == "/debug" or path.endswith("/debug"):
        info = {
            "worker_alive": True,
            "registered_spiders": list(SPIDERS.keys()),
            "url_to_name": dict(URL_TO_NAME),
            "alias_to_name": dict(ALIAS_TO_NAME),
            "init_errors": _init_errors,
        }
        try:
            config = await _load_json_config()
            info["json_config"] = config
        except Exception as e:
            info["json_config_error"] = str(e)
        return json_response(info)

    if path == "/list":
        config = await _load_json_config()
        return json_response({
            "spiders": list(SPIDERS.keys()),
            "json_config": config
        })

    await _load_json_config()

    try:
        spider_name = _resolve_spider_name(path, url)
        if spider_name and spider_name in SPIDERS:
            return await _handle_spider(SPIDERS[spider_name], url)

        if not path or path == '/':
            return json_response({
                "message": "TVBox Spider Proxy",
                "spiders": list(SPIDERS.keys()),
                "usage": [
                    "/<name>?filter=true",
                    "/<name>?t=1&ac=detail&pg=1&ext=e30%3D",
                    "/<name>?ac=detail&ids=123",
                    "/<name>?wd=关键词",
                    "?url=http://xxx.py&filter=true",
                    "/debug", "/list"
                ]
            })

        return json_response({
            "error": f"未找到spider: {path}",
            "available": list(SPIDERS.keys())
        }, 404)

    except Exception as e:
        return json_response({"error": str(e)}, 500)