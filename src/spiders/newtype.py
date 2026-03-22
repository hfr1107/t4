class NewTypeSpider:
    def __init__(self, ext=None):
        self.host = "https://xxx.com"
    
    def homeContent(self, filter_flag):
        return {'class': [...], 'filters': {...}}
    
    async def homeVideoContent(self):
        import entry
        data = await entry.api_json(f"{self.host}/api/...")
        return {'list': [...]}
    
    async def categoryContent(self, tid, pg, filter_flag, extend):
        ...
    
    async def detailContent(self, ids):
        ...
    
    def playerContent(self, flag, pid):
        return {"url": pid, "parse": 0}
    
    # 如果播放需要异步请求：
    async def playerContentAsync(self, flag, pid):
        ...
    
    async def searchContent(self, key, quick="", pg="1"):
        ...
