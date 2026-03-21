from js import Response, Headers, fetch
import json
from urllib.parse import quote
import base64


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
            f"上游非JSON HTTP {status} | URL: {full_url} | 前200字: {text[:200]}"
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