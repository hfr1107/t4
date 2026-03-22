from js import Response, URL, Headers, fetch
import json
import base64
import time
from urllib.parse import quote, unquote

# ================================================================
#  工具函数
# ================================================================

def build_url(base, params=None):
    if not params:
        return base
    parts = [f"{quote(str(k))}={quote(str(v))}" for k, v in params.items() if v is not None]
    if not parts:
        return base
    return base + ('&' if '?' in base else '?') + '&'.join(parts)


async def fetch_raw(url, headers_dict=None):
    if headers_dict:
        h = Headers.new()
        for k, v in headers_dict.items():
            h.set(k, v)
        resp = await fetch(url, headers=h)
    else:
        resp = await fetch(url)
    return resp.status, await resp.text()


async def api_json(url, params=None, headers_dict=None):
    full = build_url(url, params)
    st, text = await fetch_raw(full, headers_dict)
    if not text or not text.strip():
        raise Exception(f"空响应 HTTP {st} | {full}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise Exception(f"非JSON HTTP {st} | {full} | {text[:200]}")


def decode_ext(s):
    if not s:
        return {}
    try:
        pad = len(s) % 4
        if pad:
            s += '=' * (4 - pad)
        return json.loads(base64.b64decode(s).decode('utf-8'))
    except Exception:
        return {}


def _json(data, status=200):
    h = Headers.new()
    h.set("Content-Type", "application/json; charset=utf-8")
    h.set("Access-Control-Allow-Origin", "*")
    h.set("Access-Control-Allow-Methods", "GET, OPTIONS")
    return Response.new(json.dumps(data, indent=2, ensure_ascii=False),
                        status=status, headers=h)


# ================================================================
#  注册 Spider
# ================================================================

SPIDERS = {}
URL_TO_NAME = {}
ALIAS_TO_NAME = {}
_errors = []


def _reg(cfg):
    name = cfg.get('name','')
    mod = cfg.get('module','')
    cls = cfg.get('class','')
    if not all([name, mod, cls]):
        return
    try:
        m = __import__(mod, fromlist=[cls])
        c = getattr(m, cls)
        try:
            SPIDERS[name] = c(ext=cfg.get('ext'))
        except TypeError:
            SPIDERS[name] = c()
        for u in cfg.get('urls', []):
            URL_TO_NAME[u] = name
        for a in cfg.get('aliases', []):
            ALIAS_TO_NAME[a] = name
    except Exception as e:
        _errors.append(f"{name}: {e}")


try:
    import spiders
    for cfg in getattr(spiders, 'REGISTRY', []):
        _reg(cfg)
except Exception as e:
    _errors.append(f"discover: {e}")


# ================================================================
#  路由
# ================================================================

def _find(path, url):
    # ?url= 参数
    up = url.searchParams.get("url")
    if up:
        uc = unquote(up).rstrip('&').rstrip('?')
        if uc in URL_TO_NAME:
            return URL_TO_NAME[uc]
        for ru, n in URL_TO_NAME.items():
            if uc in ru or ru in uc:
                return n
        fn = uc.rstrip('/').split('/')[-1]
        fb = fn[:-3] if fn.endswith('.py') else fn
        if fb in SPIDERS:
            return fb
        if fb in ALIAS_TO_NAME:
            return ALIAS_TO_NAME[fb]
        return None

    # 路径
    c = path.strip('/')
    if not c or c in ('debug', 'list'):
        return None
    f = c.split('/')[0]
    b = f[:-3] if f.endswith('.py') else f
    if b in SPIDERS:
        return b
    if b in ALIAS_TO_NAME:
        return ALIAS_TO_NAME[b]
    for u, n in URL_TO_NAME.items():
        fn = u.rstrip('/').split('/')[-1]
        fb = fn[:-3] if fn.endswith('.py') else fn
        if b == fb:
            return n
    return None


# ================================================================
#  分发
# ================================================================

async def _dispatch(sp, url):
    ac   = url.searchParams.get("ac")
    t    = url.searchParams.get("t")
    tid  = url.searchParams.get("tid")
    pg   = url.searchParams.get("pg")
    ext  = url.searchParams.get("ext")
    extp = url.searchParams.get("extend")
    ids  = url.searchParams.get("ids")
    flag = url.searchParams.get("flag")
    play = url.searchParams.get("play")
    wd   = url.searchParams.get("wd")
    quick= url.searchParams.get("quick")
    fv   = url.searchParams.get("filter")

    if wd is not None and wd != "":
        return _json(await sp.searchContent(wd, quick or "", pg or "1"))

    if play is not None:
        if hasattr(sp, 'playerContentAsync'):
            return _json(await sp.playerContentAsync(flag or "", play))
        return _json(sp.playerContent(flag or "", play))

    if ac == "detail" and ids:
        il = [i.strip() for i in ids.split(",") if i.strip()]
        return _json(await sp.detailContent(il)) if il else _json({"error":"ids空"},400)

    cat = t or tid
    if cat:
        return _json(await sp.categoryContent(cat, pg or "1", fv or "", decode_ext(ext or extp or "")))

    if ac == "homeVideo":
        return _json(await sp.homeVideoContent())

    import asyncio
    r = await sp.homeContent(True) if asyncio.iscoroutinefunction(sp.homeContent) else sp.homeContent(True)
    try:
        hv = await sp.homeVideoContent()
        r['list'] = hv.get('list', [])
    except Exception:
        r['list'] = []
    return _json(r)


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
        return _json({
            "alive": True,
            "spiders": list(SPIDERS.keys()),
            "urls": dict(URL_TO_NAME),
            "aliases": dict(ALIAS_TO_NAME),
            "errors": _errors,
        })

    if path == "/list":
        return _json({"spiders": list(SPIDERS.keys())})

    try:
        name = _find(path, url)
        if name and name in SPIDERS:
            return await _dispatch(SPIDERS[name], url)

        if not path or path == '/':
            return _json({
                "msg": "TVBox Spider Proxy",
                "spiders": list(SPIDERS.keys()),
                "usage": ["/<name>?filter=true","/<name>?wd=关键词",
                          "?url=http://xxx.py&filter=true","/debug","/list"]
            })

        return _json({"error": f"未找到: {path}", "spiders": list(SPIDERS.keys())}, 404)
    except Exception as e:
        return _json({"error": str(e)}, 500)
