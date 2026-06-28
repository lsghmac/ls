# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习及爬虫技术交流。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。
"""
{
    "key": "xxx",
    "name": "xxx",
    "type": 3,
    "api": "./ApptoV5无加密.py",
    "ext": "http://domain.com"
}
"""

import re,sys,uuid
from base.spider import Spider
sys.path.append('..')

class Spider(Spider):
    host,config,local_uuid,parsing_config = '','','',[]
    headers = {
        'User-Agent': "Dart/2.19 (dart:io)",
        'Accept-Encoding': "gzip",
        'appto-local-uuid': local_uuid
    }

    def init(self, extend=''):
        try:
            host = extend.strip() if extend else ''
            if not host.startswith('http'):
                return {}
            if not re.match(r'^https?://[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*(:\d+)?/?$', host):
                try:
                    host_ = self.fetch(host).json()
                    self.host = host_.get('domain') or host
                except:
                    self.host = host
            else:
                self.host = host
            self.local_uuid = str(uuid.uuid4())
            response = self.fetch(f'{self.host}/apptov5/v1/config/get?p=android&__platform=android', headers=self.headers).json()
            config = response.get('data') or {}
            self.config = config
            parsing_conf = config.get('get_parsing', {}).get('lists') or []
            parsing_config = {}
            for i in parsing_conf:
                if i.get('config'):
                    label = []
                    for j in i['config']:
                        if j.get('type') == 'json':
                            label.append(j.get('label'))
                    parsing_config[i.get('key')] = label
            self.parsing_config = parsing_config
            return None
        except Exception as e:
            print(f'初始化异常：{e}')
            return {}

    def detailContent(self, ids):
        try:
            response = self.fetch(f"{self.host}/apptov5/v1/vod/getVod?id={ids[0]}",headers=self.headers).json()
            data3 = response.get('data') or {}
            videos = []
            vod_play_url = ''
            vod_play_from = ''
            for i in data3.get('vod_play_list') or []:
                play_url = ''
                for j in i.get('urls') or []:
                    play_url += f"{j.get('name','')}${i.get('player_info',{}).get('from','')}@{j.get('url','')}#"
                vod_play_from += i.get('player_info',{}).get('show','') + '$$$'
                vod_play_url += play_url.rstrip('#') + '$$$'
            vod_play_url = vod_play_url.rstrip('$$$')
            vod_play_from = vod_play_from.rstrip('$$$')
            videos.append({
                'vod_id': data3.get('vod_id'),
                'vod_name': data3.get('vod_name'),
                'vod_content': data3.get('vod_content'),
                'vod_remarks': data3.get('vod_remarks'),
                'vod_director': data3.get('vod_director'),
                'vod_actor': data3.get('vod_actor'),
                'vod_year': data3.get('vod_year'),
                'vod_area': data3.get('vod_area'),
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url
            })
            return {'list': videos}
        except Exception as e:
            print(f'detailContent异常：{e}')
            return {'list': []}

    def searchContent(self, key, quick, pg='1'):
        try:
            url = f"{self.host}/apptov5/v1/search/lists?wd={key}&page={pg}&type=&__platform=android"
            response = self.fetch(url, headers=self.headers).json()
            data_list = response.get('data', {}).get('data') or []
            for i in data_list:
                pic = i.get('vod_pic') or ''
                if pic.startswith('mac://'):
                    i['vod_pic'] = pic.replace('mac://', 'http://', 1)
            total = response.get('data', {}).get('total') or 0
            return {'list': data_list, 'page': pg, 'total': total}
        except Exception as e:
            print(f'searchContent异常：{e}')
            return {'list': [], 'page': pg, 'total': 0}

    def playerContent(self, flag, id, vipflags):
        default_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'
        parsing_config = self.parsing_config
        parts = id.split('@')
        if len(parts) != 2:
            return {'parse': 0, 'url': id, 'header': {'User-Agent': default_ua}}
        playfrom, rawurl = parts
        label_list = parsing_config.get(playfrom)
        if not label_list:
            return {'parse': 0, 'url': rawurl, 'header': {'User-Agent': default_ua}}
        result = {'parse': 1, 'url': rawurl, 'header': {'User-Agent': default_ua}}
        for label in label_list:
            payload = {
                'play_url': rawurl,
                'label': label,
                'key': playfrom
            }
            try:
                response = self.post(
                    f"{self.host}/apptov5/v1/parsing/proxy?__platform=android",
                    data=payload,
                    headers=self.headers
                ).json()
            except Exception as e:
                print(f"请求异常: {e}")
                continue
            if not isinstance(response, dict):
                continue
            if response.get('code') == 422:
                continue
            data = response.get('data')
            if not isinstance(data, dict):
                continue
            url = data.get('url')
            if not url:
                continue
            ua = data.get('UA') or data.get('UserAgent') or default_ua
            result = {
                'parse': 0,
                'url': url,
                'header': {'User-Agent': ua}
            }
            break
        return result

    def homeContent(self, filter):
        config = self.config
        if not config:
            return {}
        home_cate = config.get('get_home_cate') or []
        classes = []
        for i in home_cate:
            cate_id = i.get('cate_id') or i.get('cate') or i.get('id') or i.get('type_id')
            cate_name = i.get('title') or i.get('cate_name') or i.get('name') or i.get('type_name')
            if cate_id and cate_name:
                classes.append({'type_id': cate_id, 'type_name': cate_name})
        return {'class': classes}

    def homeVideoContent(self):
        try:
            response = self.fetch(f'{self.host}/apptov5/v1/home/data?id=1&mold=1&__platform=android',headers=self.headers).json()
            data = response.get('data') or {}
            vod_list = []
            for i in data.get('sections') or []:
                for j in i.get('items') or []:
                    vod_pic = j.get('vod_pic') or ''
                    if vod_pic.startswith('mac://'):
                        vod_pic = vod_pic.replace('mac://', 'http://', 1)
                    vod_list.append({
                        "vod_id": j.get('vod_id'),
                        "vod_name": j.get('vod_name'),
                        "vod_pic": vod_pic,
                        "vod_remarks": j.get('vod_remarks')
                    })
            return {'list': vod_list}
        except Exception as e:
            print(f'homeVideoContent异常：{e}')
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            ext = extend or {}
            response = self.fetch(f"{self.host}/apptov5/v1/vod/lists?area={ext.get('area','')}&lang={ext.get('lang','')}&year={ext.get('year','')}&order={ext.get('sort','time')}&type_id={tid}&type_name=&page={pg}&pageSize=21&__platform=android", headers=self.headers).json()
            data = response.get('data') or {}
            data2 = data.get('data') or []
            for i in data2:
                pic = i.get('vod_pic') or ''
                if pic.startswith('mac://'):
                    i['vod_pic'] = pic.replace('mac://', 'http://', 1)
            return {'list': data2, 'page': pg, 'total': data.get('total', 0)}
        except Exception as e:
            print(f'categoryContent异常：{e}')
            return {'list': [], 'page': pg, 'total': 0}

    def getName(self):
        return "AppToV5"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass
