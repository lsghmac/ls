# -*- coding: utf-8 -*-
"""
金牌影视 DRPY Spider for OK影视
配置: {"key":"金牌影视","type":3,"api":"https://.../Jpys.py","ext":"https://y2s52n7.com,https://m.hkybqufgh.com,https://m.sizhengxt.com,https://m.9zhoukj.com,https://m.jiabaide.cn"}
"""
from base.spider import Spider
import sys, json

class Spider(Spider):
    sites = []
    site = ''
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'}

    def init(self, extend=''):
        self.sites = [s.strip() for s in extend.split(',') if s.strip()]
        self.site = self.sites[0] if self.sites else ''
        for s in self.sites:
            try:
                r = self.fetch(f'{s}/api.php/v1.home/types', headers=self.headers).json()
                if r.get('code') == 0:
                    self.site = s
                    break
            except:
                continue

    def homeContent(self, filter):
        classes = []
        vod_list = []
        try:
            r = self.fetch(f'{self.site}/api.php/v1.home/types', headers=self.headers).json()
            if r.get('code') == 0:
                for item in (r.get('data') or []):
                    classes.append({'type_id': item.get('type_id'), 'type_name': item.get('type_name')})
            r2 = self.fetch(f'{self.site}/api.php/v1.vod/HomeIndex?page=1&limit=20', headers=self.headers).json()
            if r2.get('code') == 0:
                vod_list = r2.get('data') or []
        except:
            pass
        return {'class': classes, 'list': vod_list}

    def homeVideoContent(self):
        try:
            r = self.fetch(f'{self.site}/api.php/v1.vod/HomeIndex?page=1&limit=30', headers=self.headers).json()
            return {'list': r.get('data') or []}
        except:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            url = f'{self.site}/api.php/v1.classify/content?page={pg}&type_id={tid}'
            ext = extend or {}
            if ext.get('year'): url += f"&year={ext['year']}"
            if ext.get('area'): url += f"&area={ext['area']}"
            return self.fetch(url, headers=self.headers).json()
        except:
            return {'list': [], 'page': pg, 'pagecount': 1}

    def detailContent(self, ids):
        try:
            vid = ids[0]
            if vid.startswith('http'):
                return {'list': [{'vod_id': vid}]}
            r = self.fetch(f'{self.site}/api.php/v1.vod/detail?vod_id={vid}', headers=self.headers).json()
            if r.get('code') == 0 and r.get('data'):
                d = r['data']
                vod = {
                    'vod_id': d.get('vod_id', vid),
                    'vod_name': d.get('vod_name', ''),
                    'vod_pic': d.get('vod_pic', ''),
                    'vod_year': d.get('vod_year', ''),
                    'vod_area': d.get('vod_area', ''),
                    'vod_actor': d.get('vod_actor', ''),
                    'vod_director': d.get('vod_director', ''),
                    'vod_content': d.get('vod_content', ''),
                    'vod_play_from': d.get('vod_play_from', '金牌影视'),
                    'vod_play_url': d.get('vod_play_url', '')
                }
                return {'list': [vod]}
            return {'list': []}
        except:
            return {'list': []}

    def searchContent(self, key, quick, pg='1'):
        try:
            import urllib.parse
            url = f'{self.site}/api.php/v1.search/data?wd={urllib.parse.quote(key)}'
            return self.fetch(url, headers=self.headers).json()
        except:
            return {'list': []}

    def playerContent(self, flag, id, vipflags):
        try:
            r = self.fetch(f'{self.site}/api.php/v1.player/details?vod_id={id}', headers=self.headers).json()
            if r.get('code') == 0 and r.get('data'):
                d = r['data']
                return {'parse': 0, 'url': d.get('url', id), 'header': self.headers}
        except:
            pass
        return {'parse': 0, 'url': id, 'header': self.headers}

    def getName(self):
        return "金牌影视"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass
