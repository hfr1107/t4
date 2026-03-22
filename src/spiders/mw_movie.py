import json
import hashlib
import time
import uuid
from collections import OrderedDict


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
        self._play_from = "mw-movie"
        self._device_id = str(uuid.uuid4())

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
        if self._host and self._host_tested:
            return self._host
        if not self._host_list:
            return self._host
        if len(self._host_list) == 1:
            self._host = self._host_list[0]
            self._host_tested = True
            return self._host
        import entry
        best = self._host_list[0]
        best_t = float('inf')
        for url in self._host_list:
            try:
                s = time.time()
                st, _ = await entry.fetch_raw(
                    f"{url}/api/mw-movie/anonymous/get/filer/type",
                    self._make_headers()
                )
                e = time.time() - s
                if st == 200 and e < best_t:
                    best_t = e
                    best = url
            except Exception:
                pass
        self._host = best
        self._host_tested = True
        return self._host

    def _md5(self, t):
        return hashlib.md5(t.encode('utf-8')).hexdigest()

    def _sha1(self, t):
        return hashlib.sha1(t.encode('utf-8')).hexdigest()

    def _jp(self, p):
        return '&'.join(f"{k}={v}" for k, v in p.items())

    def _make_sign(self, params):
        t = _ts()
        sp = OrderedDict(params)
        sp['key'] = self.sign_key
        sp['t'] = t
        return t, self._sha1(self._md5(self._jp(sp)))

    def _make_headers(self, params=None):
        if params is None:
            params = OrderedDict()
        elif not isinstance(params, OrderedDict):
            params = OrderedDict(params)
        t, sign = self._make_sign(params)
        return {
            'User-Agent': self.ua,
            'Accept': 'application/json, text/plain, */*',
            'sign': sign, 't': t,
            'deviceid': self._device_id,
        }

    def _cf(self, field):
        r = []
        for i, c in enumerate(field):
            if c.isupper() and i > 0 and field[i-1] != '_' and field[i-1].islower():
                r.append('_')
            r.append(c.lower())
        return ''.join(r)

    def _cv(self, items):
        out = []
        for item in items:
            v = {self._cf(k): val for k, val in item.items()}
            if 'vod_id' in v:
                v['vod_id'] = str(v['vod_id'])
            out.append(v)
        return out

    def _remark(self, v):
        if v.get('type_id1') == 1:
            return v.get('vod_version', v.get('vod_remarks', ''))
        return v.get('vod_remarks', v.get('vod_version', ''))

    def _slim(self, vods):
        return [{
            'vod_id': v.get('vod_id', ''),
            'vod_name': v.get('vod_name', ''),
            'vod_pic': v.get('vod_pic', ''),
            'vod_remarks': self._remark(v)
        } for v in vods]

    async def homeContent(self, filter_flag):
        import entry
        host = await self._get_host()
        cd = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/get/filer/type",
            headers_dict=self._make_headers()
        )
        fd = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/v1/get/filer/list",
            headers_dict=self._make_headers()
        )
        classes = [{'type_id': str(k.get('typeId','')), 'type_name': k.get('typeName','')}
                   for k in cd.get('data', [])]
        sb = [{"n":"最近更新","v":"2"},{"n":"人气高低","v":"3"},{"n":"评分高低","v":"4"}]
        filters = {}
        for tid, d in fd.get('data', {}).items():
            cs = sb[1:] if tid == '1' else sb.copy()
            fl = [{"key":"type","name":"类型",
                   "value":[{"n":i.get("itemText",""),"v":i.get("itemValue","")}
                            for i in d.get("typeList",[])]}]
            pl = d.get("plotList", [])
            if pl:
                fl.append({"key":"v_class","name":"剧情",
                           "value":[{"n":i.get("itemText",""),"v":i.get("itemText","")} for i in pl]})
            fl += [
                {"key":"area","name":"地区",
                 "value":[{"n":i.get("itemText",""),"v":i.get("itemText","")} for i in d.get("districtList",[])]},
                {"key":"year","name":"年份",
                 "value":[{"n":i.get("itemText",""),"v":i.get("itemText","")} for i in d.get("yearList",[])]},
                {"key":"lang","name":"语言",
                 "value":[{"n":i.get("itemText",""),"v":i.get("itemText","")} for i in d.get("languageList",[])]},
                {"key":"sort","name":"排序","value":cs}
            ]
            filters[tid] = fl
        return {'class': classes, 'filters': filters}

    async def homeVideoContent(self):
        import entry
        host = await self._get_host()
        items = []
        try:
            d1 = await entry.api_json(f"{host}/api/mw-movie/anonymous/v1/home/all/list",
                                       headers_dict=self._make_headers())
            for s in d1.get('data', {}).values():
                if isinstance(s, dict) and 'list' in s:
                    items.extend(s['list'])
        except Exception:
            pass
        try:
            d2 = await entry.api_json(f"{host}/api/mw-movie/anonymous/home/hotSearch",
                                       headers_dict=self._make_headers())
            items.extend(d2.get('data', []))
        except Exception:
            pass
        return {'list': self._slim(self._cv(items))}

    async def categoryContent(self, tid, pg, ff, extend):
        import entry
        host = await self._get_host()
        p = OrderedDict([
            ("area", extend.get('area','')), ("filterStatus","1"),
            ("lang", extend.get('lang','')), ("pageNum", str(pg)),
            ("pageSize","30"), ("sort", extend.get('sort','1')),
            ("sortBy","1"), ("type", extend.get('type','')),
            ("type1", str(tid)), ("v_class", extend.get('v_class','')),
            ("year", extend.get('year',''))
        ])
        d = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/video/list?{self._jp(p)}",
            headers_dict=self._make_headers(p))
        return {
            'list': self._slim(self._cv(d.get('data',{}).get('list',[]))),
            'page': pg, 'pagecount': 9999, 'limit': 30, 'total': 999999
        }

    async def detailContent(self, ids):
        import entry
        host = await self._get_host()
        vid = ids[0]
        sp = OrderedDict([("id", vid)])
        d = await entry.api_json(
            f"{host}/api/mw-movie/anonymous/video/detail?id={vid}",
            headers_dict=self._make_headers(sp))
        res = d.get('data', {})
        vods = self._cv([res])
        vod = vods[0] if vods else {}
        el = res.get('episodeList', [])
        pu = []
        for i in el:
            n = i.get('name', '')
            if len(el) <= 1:
                n = vod.get('vod_name', n)
            pu.append(f"{n}${vid}@@{i.get('nid','')}")
        vod['vod_play_from'] = self._play_from
        vod['vod_play_url'] = '#'.join(pu)
        vod['vod_id'] = str(vid)
        for k in ('vod_name','vod_pic','vod_content','type_name','vod_remarks',
                   'vod_year','vod_area','vod_actor','vod_director'):
            vod.setdefault(k, '')
        for k in list(vod.keys()):
            if k.startswith('episode') or k.startswith('source_'):
                del vod[k]
        return {'list': [vod]}

    def playerContent(self, flag, pid):
        return {"url": pid, "parse": 0}

    async def playerContentAsync(self, flag, pid):
        import entry
        host = await self._get_host()
        parts = pid.split('@@') if '@@' in pid else pid.split('/')
        if len(parts) < 2:
            return {"url": self.error_url, "parse": 0}
        _id, _nid = parts[0], parts[1]
        sp = OrderedDict([("clientType","1"),("id",_id),("nid",_nid)])
        t, sign = self._make_sign(sp)
        rh = {'User-Agent':self.ua,'Accept':'application/json, text/plain, */*',
              'sign':sign,'t':t,'deviceid':self._device_id}
        ph = {'User-Agent':self.ua,'Origin':host,'Referer':f'{host}/',
              'sec-ch-ua-platform':'"Windows"','DNT':'1',
              'sec-ch-ua':'"Not/A)Brand";v="8","Chromium";v="126","Google Chrome";v="126"',
              'sec-ch-ua-mobile':'?0'}
        try:
            pd = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/v2/video/episode/url"
                f"?clientType=1&id={_id}&nid={_nid}",
                headers_dict=rh)
            ul = pd.get('data',{}).get('list',[])
            if not ul:
                return {"url":self.error_url,"header":ph,"parse":0}
            if len(ul) == 1:
                return {"url":ul[0].get('url',self.error_url),"header":ph,"parse":0}
            vl = []
            for i in ul:
                vl.append(i.get('resolutionName',''))
                vl.append(i.get('url',''))
            return {"url":vl,"header":ph,"parse":0}
        except Exception:
            return {"url":self.error_url,"header":ph,"parse":0}

    async def searchContent(self, key, quick="", pg="1"):
        import entry
        host = await self._get_host()
        p = OrderedDict([("keyword",key),("pageNum",str(pg)),("pageSize","12"),("sourceCode","1")])
        try:
            d = await entry.api_json(
                f"{host}/api/mw-movie/anonymous/video/searchByWord?{self._jp(p)}",
                headers_dict=self._make_headers(p))
            return {
                'list': self._slim(self._cv(d.get('data',{}).get('result',{}).get('list',[]))),
                'page': pg, 'limit': 12
            }
        except Exception:
            return {'list':[], 'limit':12}
