"""荐片 Spider — 完整移植自本地版荐片.py"""
import json
from ..spider_base import api_json, fetch_raw, build_url


class JianpianSpider:
    def __init__(self):
        self.host = 'https://ev5356.970xw.com'
        self.ua = (
            'Mozilla/5.0 (Linux; Android 9; V2196A'
            'Build/PQ3A.190705.08211809; wv) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Version/4.0 Chrome/91.0.4472.114 '
            'Mobile Safari/537.36;webank/h5face;'
            'webank/1.0;netType:NETWORK_WIFI;'
            'appVersion:416;packageName:com.jp3.xg3'
        )
        self._ihost = ""

    def _headers(self):
        return {
            'User-Agent': self.ua,
            'Referer': self.host,
            'Accept': 'application/json, text/plain, */*'
        }

    async def _get_ihost(self):
        if self._ihost:
            return self._ihost
        try:
            data = await api_json(
                f"{self.host}/api/appAuthConfig",
                headers_dict=self._headers()
            )
            h = data['data']['imgDomain']
            self._ihost = f"https://{h}" if not h.startswith('http') else h
        except Exception:
            self._ihost = self.host
        return self._ihost

    def homeContent(self, filter_flag):
        classes = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '动漫'},
            {'type_id': '4', 'type_name': '综艺'}
        ]
        year_val = [
            {"v": "107", "n": "2025"}, {"v": "119", "n": "2024"},
            {"v": "153", "n": "2023"}, {"v": "101", "n": "2022"},
            {"v": "118", "n": "2021"}, {"v": "16", "n": "2020"},
            {"v": "7", "n": "2019"}, {"v": "2", "n": "2018"},
            {"v": "3", "n": "2017"}, {"v": "22", "n": "2016"},
            {"v": "2015", "n": "2015以前"}
        ]
        area_val = [
            {"v": "1", "n": "国产"}, {"v": "3", "n": "香港"},
            {"v": "6", "n": "台湾"}, {"v": "5", "n": "美国"},
            {"v": "18", "n": "韩国"}, {"v": "2", "n": "日本"}
        ]
        sort_val = [
            {"v": "update", "n": "最新"},
            {"v": "hot", "n": "最热"},
            {"v": "rating", "n": "评分"}
        ]
        cate_val = [
            {"v": "1", "n": "剧情"}, {"v": "2", "n": "爱情"},
            {"v": "3", "n": "动画"}, {"v": "4", "n": "喜剧"},
            {"v": "5", "n": "战争"}, {"v": "6", "n": "歌舞"},
            {"v": "7", "n": "古装"}, {"v": "8", "n": "奇幻"},
            {"v": "9", "n": "冒险"}, {"v": "10", "n": "动作"},
            {"v": "11", "n": "科幻"}, {"v": "12", "n": "悬疑"},
            {"v": "13", "n": "犯罪"}, {"v": "14", "n": "家庭"},
            {"v": "15", "n": "传记"}, {"v": "16", "n": "运动"},
            {"v": "18", "n": "惊悚"}, {"v": "20", "n": "短片"},
            {"v": "21", "n": "历史"}, {"v": "22", "n": "音乐"},
            {"v": "23", "n": "西部"}, {"v": "24", "n": "武侠"},
            {"v": "25", "n": "恐怖"}
        ]
        common = [
            {"key": "area", "name": "地區", "value": area_val},
            {"key": "year", "name": "年代", "value": year_val},
            {"key": "sort", "name": "排序", "value": sort_val}
        ]
        filters = {
            "1": [{"key": "cateId", "name": "分类", "value": cate_val}] + common,
            "2": common, "3": common, "4": common
        }
        return {'class': classes, 'filters': filters}

    async def homeVideoContent(self):
        ihost = await self._get_ihost()
        data = await api_json(
            f"{self.host}/api/slide/list?pos_id=88",
            headers_dict=self._headers()
        )
        videos = []
        for item in data.get('data', []):
            videos.append({
                'vod_id': str(item.get('jump_id', '')),
                'vod_name': item.get('title', ''),
                'vod_pic': f"{ihost}{item.get('thumbnail', '')}",
                'vod_remarks': ''
            })
        return {'list': videos}

    async def categoryContent(self, tid, pg, filter_flag, extend):
        ihost = await self._get_ihost()
        params = {
            'fcate_pid': str(tid),
            'page': str(pg),
            'category_id': str(extend.get('cateId', '')),
            'area': str(extend.get('area', '')),
            'year': str(extend.get('year', '')),
            'type': str(extend.get('cateId', '')),
            'sort': str(extend.get('sort', ''))
        }
        data = await api_json(
            f"{self.host}/api/crumb/list",
            params=params,
            headers_dict=self._headers()
        )
        videos = []
        for item in data.get('data', []):
            videos.append({
                'vod_id': str(item.get('id', '')),
                'vod_name': item.get('title', ''),
                'vod_pic': f"{ihost}{item.get('path', '')}",
                'vod_remarks': item.get('mask', ''),
                'vod_year': ''
            })
        return {
            'list': videos,
            'page': pg,
            'pagecount': 99999,
            'limit': 15,
            'total': 99999
        }

    async def detailContent(self, ids):
        vid = ids[0]
        data = await api_json(
            f"{self.host}/api/video/detailv2?id={vid}",
            headers_dict=self._headers()
        )
        res = data.get('data', {})
        play_from = ['边下边播']
        play_url = []
        for source in res.get('source_list_source', []):
            if source.get('name') == '常规线路':
                parts = []
                for part in source.get('source_list', []):
                    name = part.get('source_name', part.get('weight', ''))
                    parts.append(f"{name}${part.get('url', '')}")
                play_url.append('#'.join(parts))
                break
        vod = {
            'vod_id': str(vid),
            'type_name': '/'.join(
                [t.get('name', '') for t in res.get('types', [])]
            ),
            'vod_year': str(res.get('year', '')),
            'vod_area': str(res.get('area', '')),
            'vod_remarks': res.get('mask', ''),
            'vod_content': res.get('description', ''),
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url)
        }
        return {'list': [vod]}

    def playerContent(self, flag, vid):
        if ".m3u8" in vid:
            return {'parse': 0, 'url': vid}
        else:
            return {'parse': 0, 'url': f"tvbox-xg:{vid}"}

    async def searchContent(self, key, quick="", pg="1"):
        ihost = await self._get_ihost()
        params = {
            'key': key, 'category_id': '88',
            'page': str(pg), 'pageSize': '20'
        }
        data = await api_json(
            f"{self.host}/api/v2/search/videoV2",
            params=params,
            headers_dict=self._headers()
        )
        key_lower = key.lower()
        filtered = [
            item for item in data.get('data', [])
            if key_lower in item.get('title', '').lower()
        ]
        videos = []
        for item in filtered:
            videos.append({
                'vod_id': str(item.get('id', '')),
                'vod_name': item.get('title', ''),
                'vod_pic': f"{ihost}{item.get('thumbnail', '')}",
                'vod_remarks': item.get('mask', ''),
                'vod_year': ''
            })
        return {'list': videos, 'limit': 20}