"""
通用 mw-movie API Spider 引擎
覆盖: 金牌、文才，以及所有使用相同 API 架构的站点
只需在 __init__.py 的 REGISTRY 中配置不同域名即可

支持特性:
- MD5→SHA1 签名
- 多域名自动选择（测速）
- 动态获取分类/筛选
- 搜索、详情、播放、首页推荐
"""
import json
import hashlib
import time
import re
import uuid


def _ts():
    return str(int(time.time() * 1000))


class MwMovieSpider:
    def __init__(self, ext=None):
        self.ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        self.error_url = (
            "https://sf1-cdn-tos.huoshanstatic.com/obj/media-fe/"
            "xgplayer_doc_video/mp4/xgplayer-demo-720p.mp4"
        )
        self.sign_key = 'cb808529bae6b6be45ecfab29a4889bc'
        self._host = ""
        self._host_list = []
        self._home_cache = None

        # 从 ext 配置解析域名
        if ext and ext.get('site'):
            sites = ext['site']
            if isinstance(sites, str):
                self._host_list = [s.strip() for s in sites.split(',') if s.strip()]
            elif isinstance(sites, list):
                self._host_list = sites
            if self._host_list:
                self._host = self._host_list[0]

    async def _get_host(self):
        """获取最快的域名（简单实现：CF Workers 中用 fetch 测速）"""
        if self._host:
            return self._host
        if not self._host_list:
            return ""

        if len(self._host_list) == 1:
            self._host = self._host_list[0]
            return self._host

        import entry
        best_url = self._host_list[0]
        best_time = float('inf')

        for url in self._host_list:
            try:
                start = time.time()
                status, _ = await entry.fetch_raw(
                    f"{url}/api/mw-movie/anonymous/get/filer/type",
                    self._make_headers()
                )
                elapsed = time.time() - start
                if status == 200 and elapsed < best_time:
                    best_time = elapsed
                    best_url = url
            except Exception:
                pass

        self._host = best_url
        return self._host

    def _md5(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _sha1(self, text):
        return hashlib.sha1(text.encode('utf-8')).hexdigest()

    def _join_params(self, params):
        return '&'.join(f"{k}={v}" for k, v in params.items())

    def _make_headers(self, params=None):
        if params is None:
            params = {}
        t = _ts()
        sign_params = dict(params)
        sign_params['key'] = self.sign_key
        sign_params['t'] = t
        sign_str = self._join_params(sign_params)
        sign = self._sha1(self._md5(sign_str))
        return {
            'User-Agent': self.ua,
            'Accept': 'application/json, text/plain, */*',
            'sign': sign,
            't': t,
            'deviceid': str(uuid.uuid4()),
        }

    def _convert_field(self, field):
        """vodName -> vod_name 转换"""
        f = field
        if f.startswith('vod') and len(f) > 3 and f[3:4].isupper():
            f = 'vod_' + f[3:]
        elif f.startswith('type') and len(f) > 4 and f[4:5].isupper():
            f = 'type_' + f[4:]
        # camelCase -> snake_case
        result = []
        for i, c in enumerate(f):
            if c.isupper() and i > 0 and f[i-1] != '_':
                result.append('_')
            result.append(c.lower())
        return ''.join(result)

    def _convert_vod(self, items):
        """将上游数据的字段名转换为标准格式"""
        result = []
        for item in items:
            vod = {}
            for k, v in item.items():
                new_key = self._convert_field(k)
                vod[new_key] = v
            # 确保关键字段存在且为字符串
            if 'vod_id' in vod:
                vod['vod_id'] = str(vod['vod_id'])
            result.append(vod)
        return result

    async def homeContent(self, filter_flag):
        """首页分类 + 筛选 — 动态从 API 获取"""
        import entry
        host = await self._get_host()

        # 获取分类
        cdata = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/get/filer/type",
            headers_dict=self._make_headers()
        )
        # 获取筛选
        fdata = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/v1/get/filer/list",
            headers_dict=self._make_headers()
        )

        classes = []
        for k in cdata.get('data', []):
            classes.append({
                'type_id': str(k.get('typeId', '')),
                'type_name': k.get('typeName', ''),
            })

        sort_values = [
            {"n": "最近更新", "v": "2"},
            {"n": "人气高低", "v": "3"},
            {"n": "评分高低", "v": "4"}
        ]

        filters = {}
        for tid, d in fdata.get('data', {}).items():
            current_sort = sort_values.copy()
            if tid == '1':
                current_sort = current_sort[1:]  # 电影去掉"最近更新"

            filter_list = [
                {"key": "type", "name": "类型",
                 "value": [{"n": i.get("itemText",""), "v": i.get("itemValue","")}
                           for i in d.get("typeList", [])]},
            ]

            # 剧情（可能为空）
            plot_list = d.get("plotList", [])
            if plot_list:
                filter_list.append({
                    "key": "v_class", "name": "剧情",
                    "value": [{"n": i.get("itemText",""), "v": i.get("itemText","")}
                              for i in plot_list]
                })

            filter_list.extend([
                {"key": "area", "name": "地区",
                 "value": [{"n": i.get("itemText",""), "v": i.get("itemText","")}
                           for i in d.get("districtList", [])]},
                {"key": "year", "name": "年份",
                 "value": [{"n": i.get("itemText",""), "v": i.get("itemText","")}
                           for i in d.get("yearList", [])]},
                {"key": "lang", "name": "语言",
                 "value": [{"n": i.get("itemText",""), "v": i.get("itemText","")}
                           for i in d.get("languageList", [])]},
                {"key": "sort", "name": "排序", "value": current_sort}
            ])

            filters[tid] = filter_list

        return {'class': classes, 'filters': filters}

    async def homeVideoContent(self):
        """首页推荐"""
        import entry
        host = await self._get_host()

        all_items = []

        # 尝试获取首页列表
        try:
            data1 = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/v1/home/all/list",
                headers_dict=self._make_headers()
            )
            for section in data1.get('data', {}).values():
                if isinstance(section, dict) and 'list' in section:
                    all_items.extend(section['list'])
        except Exception:
            pass

        # 获取热搜
        try:
            data2 = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/home/hotSearch",
                headers_dict=self._make_headers()
            )
            all_items.extend(data2.get('data', []))
        except Exception:
            pass

        videos = self._convert_vod(all_items)
        # 精简字段
        result = []
        for v in videos:
            item = {
                'vod_id': v.get('vod_id', ''),
                'vod_name': v.get('vod_name', ''),
                'vod_pic': v.get('vod_pic', ''),
                'vod_remarks': v.get('vod_version', '') if v.get('type_id1') == 1 else v.get('vod_remarks', '')
            }
            result.append(item)
        return {'list': result}

    async def categoryContent(self, tid, pg, filter_flag, extend):
        """分类列表"""
        import entry
        host = await self._get_host()

        params = {
            "area": extend.get('area', ''),
            "filterStatus": "1",
            "lang": extend.get('lang', ''),
            "pageNum": str(pg),
            "pageSize": "30",
            "sort": extend.get('sort', '1'),
            "sortBy": "1",
            "type": extend.get('type', ''),
            "type1": str(tid),
            "v_class": extend.get('v_class', ''),
            "year": extend.get('year', '')
        }

        query_str = self._join_params(params)
        data = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/video/list?{query_str}",
            headers_dict=self._make_headers(params)
        )

        items = data.get('data', {}).get('list', [])
        videos = self._convert_vod(items)
        result = []
        for v in videos:
            result.append({
                'vod_id': v.get('vod_id', ''),
                'vod_name': v.get('vod_name', ''),
                'vod_pic': v.get('vod_pic', ''),
                'vod_remarks': v.get('vod_version', '') if v.get('type_id1') == 1 else v.get('vod_remarks', '')
            })

        return {
            'list': result,
            'page': pg,
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        }

    async def detailContent(self, ids):
        """详情"""
        import entry
        host = await self._get_host()
        vid = ids[0]

        data = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/video/detail?id={vid}",
            headers_dict=self._make_headers({'id': vid})
        )

        res = data.get('data', {})
        vods = self._convert_vod([res])
        vod = vods[0] if vods else {}

        # 构建播放列表
        episode_list = res.get('episodeList', [])
        vod_play_url = []
        for i in episode_list:
            name = i.get('name', '')
            if len(episode_list) <= 1:
                name = vod.get('vod_name', name)
            ep_id = f"{vid}@@{i.get('nid', '')}"
            vod_play_url.append(f"{name}${ep_id}")

        vod['vod_play_from'] = 'mw-movie'
        vod['vod_play_url'] = '#'.join(vod_play_url)

        # 清理不需要的字段
        for key in list(vod.keys()):
            if key.startswith('episode') or key.startswith('source_list'):
                del vod[key]

        return {'list': [vod]}

    def playerContent(self, flag, pid):
        """同步播放（简单返回）"""
        return {"url": pid, "parse": 0}

    async def playerContentAsync(self, flag, pid):
        """异步播放 — 需要签名获取真实 URL"""
        import entry
        host = await self._get_host()

        ids = pid.split('@@')
        if len(ids) < 2:
            return {"url": self.error_url, "parse": 0}

        _id, _nid = ids[0], ids[1]
        params = {'clientType': '1', 'id': _id, 'nid': _nid}

        h2 = {
            'User-Agent': self.ua,
            'Origin': host,
            'Referer': f'{host}/'
        }

        try:
            pdata = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/v2/video/episode/url?clientType=1&id={_id}&nid={_nid}",
                headers_dict=self._make_headers(params)
            )
            # 文才返回多清晰度列表
            url_list = pdata.get('data', {}).get('list', [])
            if url_list:
                # 返回最高清晰度
                play_url = url_list[0].get('url', self.error_url)
            else:
                play_url = self.error_url
        except Exception:
            play_url = self.error_url

        return {"url": play_url, "header": h2, "parse": 0}

    async def searchContent(self, key, quick="", pg="1"):
        """搜索"""
        import entry
        host = await self._get_host()

        params = {
            "keyword": key,
            "pageNum": str(pg),
            "pageSize": "12",
            "sourceCode": "1"
        }
        query_str = self._join_params(params)

        try:
            data = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/video/searchByWord?{query_str}",
                headers_dict=self._make_headers(params)
            )
            items = data.get('data', {}).get('result', {}).get('list', [])
            videos = self._convert_vod(items)
            result = []
            for v in videos:
                result.append({
                    'vod_id': v.get('vod_id', ''),
                    'vod_name': v.get('vod_name', ''),
                    'vod_pic': v.get('vod_pic', ''),
                    'vod_remarks': v.get('vod_version', '') if v.get('type_id1') == 1 else v.get('vod_remarks', '')
                })
            return {'list': result, 'page': pg, 'limit': 12}
        except Exception:
            return {'list': [], 'limit': 12}