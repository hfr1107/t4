"""
通用 mw-movie API Spider 引擎
覆盖: 金牌、文才等所有使用 mw-movie API 架构的站点
只需在 __init__.py 配置不同域名即可

支持特性:
- MD5→SHA1 签名
- 多域名自动选择
- 动态获取分类/筛选
- 多清晰度播放
- 搜索、详情、首页推荐
"""
import json
import hashlib
import time
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
        self._host_tested = False
        # 播放来源名称，可通过 ext 自定义
        self._play_from = "mw-movie"

        if ext:
            sites = ext.get('site', '')
            if isinstance(sites, str):
                self._host_list = [s.strip() for s in sites.split(',') if s.strip()]
            elif isinstance(sites, list):
                self._host_list = sites
            if self._host_list:
                self._host = self._host_list[0]
            if ext.get('play_from'):
                self._play_from = ext['play_from']

    async def _get_host(self):
        """获取可用域名，多域名时测速选最快"""
        if self._host and self._host_tested:
            return self._host
        if not self._host_list:
            return self._host

        if len(self._host_list) == 1:
            self._host = self._host_list[0]
            self._host_tested = True
            return self._host

        import entry
        best_url = self._host_list[0]
        best_time = float('inf')

        for url in self._host_list:
            try:
                start = time.time()
                status, text = await entry.fetch_raw(
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
        self._host_tested = True
        return self._host

    def _md5(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _sha1(self, text):
        return hashlib.sha1(text.encode('utf-8')).hexdigest()

    def _join_params(self, params):
        """按原始顺序拼接参数（签名需要）"""
        return '&'.join(f"{k}={v}" for k, v in params.items())

    def _make_headers(self, params=None):
        """生成带签名的请求头"""
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
        """vodName → vod_name, typeId1 → type_id1"""
        result = []
        for i, c in enumerate(field):
            if c.isupper() and i > 0:
                prev = field[i - 1]
                if prev != '_' and prev.islower():
                    result.append('_')
            result.append(c.lower())
        return ''.join(result)

    def _convert_vod(self, items):
        """将上游 camelCase 字段转为 snake_case"""
        result = []
        for item in items:
            vod = {}
            for k, v in item.items():
                vod[self._convert_field(k)] = v
            if 'vod_id' in vod:
                vod['vod_id'] = str(vod['vod_id'])
            result.append(vod)
        return result

    def _pick_remarks(self, v):
        """根据 type_id1 选择 vod_remarks"""
        if v.get('type_id1') == 1:
            return v.get('vod_version', v.get('vod_remarks', ''))
        return v.get('vod_remarks', v.get('vod_version', ''))

    # ============================================================
    #  homeContent — 动态获取分类和筛选
    # ============================================================

    async def homeContent(self, filter_flag):
        import entry
        host = await self._get_host()

        cdata = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/get/filer/type",
            headers_dict=self._make_headers()
        )
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

        sort_base = [
            {"n": "最近更新", "v": "2"},
            {"n": "人气高低", "v": "3"},
            {"n": "评分高低", "v": "4"}
        ]

        filters = {}
        for tid, d in fdata.get('data', {}).items():
            cur_sort = sort_base.copy()
            if tid == '1':
                cur_sort = cur_sort[1:]

            fl = [
                {"key": "type", "name": "类型",
                 "value": [{"n": i.get("itemText", ""), "v": i.get("itemValue", "")}
                           for i in d.get("typeList", [])]},
            ]
            plot = d.get("plotList", [])
            if plot:
                fl.append({
                    "key": "v_class", "name": "剧情",
                    "value": [{"n": i.get("itemText", ""), "v": i.get("itemText", "")}
                              for i in plot]
                })
            fl.extend([
                {"key": "area", "name": "地区",
                 "value": [{"n": i.get("itemText", ""), "v": i.get("itemText", "")}
                           for i in d.get("districtList", [])]},
                {"key": "year", "name": "年份",
                 "value": [{"n": i.get("itemText", ""), "v": i.get("itemText", "")}
                           for i in d.get("yearList", [])]},
                {"key": "lang", "name": "语言",
                 "value": [{"n": i.get("itemText", ""), "v": i.get("itemText", "")}
                           for i in d.get("languageList", [])]},
                {"key": "sort", "name": "排序", "value": cur_sort}
            ])
            filters[tid] = fl

        return {'class': classes, 'filters': filters}

    # ============================================================
    #  homeVideoContent — 首页推荐
    # ============================================================

    async def homeVideoContent(self):
        import entry
        host = await self._get_host()
        all_items = []

        try:
            d1 = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/v1/home/all/list",
                headers_dict=self._make_headers()
            )
            for section in d1.get('data', {}).values():
                if isinstance(section, dict) and 'list' in section:
                    all_items.extend(section['list'])
        except Exception:
            pass

        try:
            d2 = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/home/hotSearch",
                headers_dict=self._make_headers()
            )
            all_items.extend(d2.get('data', []))
        except Exception:
            pass

        vods = self._convert_vod(all_items)
        result = []
        for v in vods:
            result.append({
                'vod_id': v.get('vod_id', ''),
                'vod_name': v.get('vod_name', ''),
                'vod_pic': v.get('vod_pic', ''),
                'vod_remarks': self._pick_remarks(v)
            })
        return {'list': result}

    # ============================================================
    #  categoryContent — 分类列表
    # ============================================================

    async def categoryContent(self, tid, pg, filter_flag, extend):
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

        qs = self._join_params(params)
        data = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/video/list?{qs}",
            headers_dict=self._make_headers(params)
        )

        items = data.get('data', {}).get('list', [])
        vods = self._convert_vod(items)
        result = []
        for v in vods:
            result.append({
                'vod_id': v.get('vod_id', ''),
                'vod_name': v.get('vod_name', ''),
                'vod_pic': v.get('vod_pic', ''),
                'vod_remarks': self._pick_remarks(v)
            })

        return {
            'list': result, 'page': pg,
            'pagecount': 9999, 'limit': 30, 'total': 999999
        }

    # ============================================================
    #  detailContent — 详情
    # ============================================================

    async def detailContent(self, ids):
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
        # 文才格式: name$vodId@@nid
        # 金牌格式: name$vodId/nid
        # 统一用 @@ 分隔（兼容文才原始格式）
        episode_list = res.get('episodeList', [])
        vod_play_url = []
        for i in episode_list:
            ep_name = i.get('name', '')
            if len(episode_list) <= 1:
                ep_name = vod.get('vod_name', ep_name)
            ep_id = f"{vid}@@{i.get('nid', '')}"
            vod_play_url.append(f"{ep_name}${ep_id}")

        vod['vod_play_from'] = self._play_from
        vod['vod_play_url'] = '#'.join(vod_play_url)
        vod['vod_id'] = str(vid)

        # 补充标准字段
        vod.setdefault('vod_name', '')
        vod.setdefault('vod_pic', '')
        vod.setdefault('vod_year', str(res.get('vodYear', '')))
        vod.setdefault('vod_area', res.get('vodArea', ''))
        vod.setdefault('vod_actor', res.get('vodActor', ''))
        vod.setdefault('vod_director', res.get('vodDirector', ''))
        vod.setdefault('vod_content', res.get('vodContent', ''))
        vod.setdefault('type_name', res.get('typeName', ''))
        vod.setdefault('vod_remarks', res.get('vodRemarks', ''))

        # 清理不需要的原始字段
        for key in list(vod.keys()):
            if key.startswith('episode') or key.startswith('source_list'):
                del vod[key]

        return {'list': [vod]}

    # ============================================================
    #  playerContent — 播放（核心修复）
    # ============================================================

    def playerContent(self, flag, pid):
        """同步播放（不应被调用，走 Async）"""
        return {"url": pid, "parse": 0}

    async def playerContentAsync(self, flag, pid):
        """
        异步播放 — 签名请求获取真实播放地址
        
        pid 格式: vodId@@nid (文才/统一格式)
                  vodId/nid  (金牌旧格式，兼容)
        
        返回格式需兼容 TVBox:
        - 单个URL: {"url": "http://...", "parse": 0}
        - 多清晰度: {"url": "http://...", "parse": 0}
          （选最高清晰度返回，或返回数组让客户端选择）
        """
        import entry
        host = await self._get_host()

        # 兼容两种分隔符
        if '@@' in pid:
            parts = pid.split('@@')
        elif '/' in pid:
            parts = pid.split('/')
        else:
            return {"url": self.error_url, "parse": 0}

        if len(parts) < 2:
            return {"url": self.error_url, "parse": 0}

        _id, _nid = parts[0], parts[1]

        # 签名参数 — 文才多了 clientType
        sign_params = {'clientType': '1', 'id': _id, 'nid': _nid}

        play_header = {
            'User-Agent': self.ua,
            'sec-ch-ua-platform': '"Windows"',
            'DNT': '1',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'Origin': host,
            'Referer': f'{host}/'
        }

        try:
            pdata = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/v2/video/episode/url"
                f"?clientType=1&id={_id}&nid={_nid}",
                headers_dict=self._make_headers(sign_params)
            )

            url_list = pdata.get('data', {}).get('list', [])
            if not url_list:
                return {"url": self.error_url, "header": play_header, "parse": 0}

            # ★ 关键：文才返回多清晰度列表
            # 本地 py 返回交替数组 [名称,url,名称,url,...]
            # TVBox 客户端能处理这种格式
            # 我们也按相同格式返回

            if len(url_list) == 1:
                # 只有一个清晰度，直接返回 URL
                play_url = url_list[0].get('url', self.error_url)
                return {
                    "url": play_url,
                    "header": play_header,
                    "parse": 0
                }
            else:
                # 多清晰度 — 返回交替数组 [名称, url, 名称, url, ...]
                vlist = []
                for item in url_list:
                    vlist.append(item.get('resolutionName', ''))
                    vlist.append(item.get('url', ''))

                return {
                    "url": vlist,
                    "header": play_header,
                    "parse": 0
                }

        except Exception as e:
            return {
                "url": self.error_url,
                "header": play_header,
                "parse": 0,
                "error": str(e)
            }

    # ============================================================
    #  searchContent — 搜索
    # ============================================================

    async def searchContent(self, key, quick="", pg="1"):
        import entry
        host = await self._get_host()

        params = {
            "keyword": key,
            "pageNum": str(pg),
            "pageSize": "12",
            "sourceCode": "1"
        }
        qs = self._join_params(params)

        try:
            data = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/video/searchByWord?{qs}",
                headers_dict=self._make_headers(params)
            )
            items = data.get('data', {}).get('result', {}).get('list', [])
            vods = self._convert_vod(items)
            result = []
            for v in vods:
                result.append({
                    'vod_id': v.get('vod_id', ''),
                    'vod_name': v.get('vod_name', ''),
                    'vod_pic': v.get('vod_pic', ''),
                    'vod_remarks': self._pick_remarks(v)
                })
            return {'list': result, 'page': pg, 'limit': 12}
        except Exception:
            return {'list': [], 'limit': 12}