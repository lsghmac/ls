# -*- coding: utf-8 -*-
# by @星河
# 修复版本 - 参考最新三合一.js重构虎牙、斗鱼、B站直播逻辑
# 修复：虎牙清晰度选择，确保ratio参数正确传递码率值
# 修复：斗鱼切换分辨率只能播放1秒的问题（每次重新获取安全密钥和签名）
# 修复：B站使用getRoomPlayInfo接口获取直播流
import json
import re
import sys
import time
import hashlib
import random
import string
import urllib.parse
from base64 import b64decode, b64encode
from urllib.parse import parse_qs
import requests
from pyquery import PyQuery as pq
from bs4 import BeautifulSoup
sys.path.append('..')
from base.spider import Spider
from concurrent.futures import ThreadPoolExecutor


class Spider(Spider):

    def init(self, extend=""):
        self.dy_cookie_cache = ""

    def getName(self):
        return "直播"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
        },
        {
            "User-Agent": "Dart/3.4 (dart:io)"
        }
    ]

    excepturl = 'https://www.baidu.com'

    hosts = {
        "kuaishou": "https://live.kuaishou.com",
        "huya": ["https://www.huya.com", "https://mp.huya.com"],
        "douyu": "https://www.douyu.com",
        "wangyi": "https://cc.163.com",
        "bili": ["https://api.live.bilibili.com", "https://api.bilibili.com"],
        "douyin": "https://live.douyin.com"
    }

    referers = {
        "kuaishou": "https://live.kuaishou.com",
        "huya": "https://live.cdn.huya.com",
        "douyu": "https://m.douyu.com",
        "bili": "https://live.bilibili.com",
        "douyin": "https://live.douyin.com"
    }

    playheaders = {
        'kuaishou': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://live.kuaishou.com'
        },
        "wangyi": {
            "User-Agent": "ExoPlayer",
            "Connection": "Keep-Alive",
            "Icy-MetaData": "1"
        },
        "bili": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://live.bilibili.com'
        },
        'huya': {
            'User-Agent': 'ExoPlayer',
            'Connection': 'Keep-Alive',
            'Icy-MetaData': '1'
        },
        'douyu': {
            'User-Agent': 'libmpv',
            'Icy-MetaData': '1'
        },
        'douyin': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://live.douyin.com'
        }
    }

    def process_bili(self):
        return ('bili', [{'key': 'cate', 'name': '分类',
                          'value': [{'n': '舞蹈', 'v': '舞'}, {'n': '音乐', 'v': '音乐'},
                                    {'n': '手游', 'v': '手游'}, {'n': '网游', 'v': '网游'},
                                    {'n': '单机游戏', 'v': '单机游戏'}, {'n': '虚拟主播', 'v': '虚拟主播'},
                                    {'n': '电台', 'v': '电台'}, {'n': '体育', 'v': '体育'},
                                    {'n': '聊天', 'v': '聊天'}, {'n': '娱乐', 'v': '娱乐'},
                                    {'n': '影视', 'v': '电影'}, {'n': '新闻', 'v': '新闻'}]}])

    def process_douyu(self):
        try:
            self.dyufdata = self.fetch(
                f'{self.referers["douyu"]}/api/cate/list',
                headers=self.headers[1]
            ).json()
            return ('douyu', [{'key': 'cate', 'name': '分类',
                                'value': [{'n': i['cate1Name'], 'v': str(i['cate1Id'])}
                                          for i in self.dyufdata['data']['cate1Info']]}])
        except Exception as e:
            print(f"douyu错误: {e}")
            return 'douyu', None

    def process_douyin(self):
        return ('douyin', [{'key': 'cate', 'name': '分类',
                            'value': [{'n': '娱乐天地', 'v': '10000$3'},
                                      {'n': '科技文化', 'v': '10001$3'},
                                      {'n': '音乐', 'v': '102$4'},
                                      {'n': '游戏', 'v': '103$4'},
                                      {'n': '舞蹈', 'v': '105$4'},
                                      {'n': '聊天', 'v': '101$4'},
                                      {'n': '运动', 'v': '108$4'},
                                      {'n': '生活', 'v': '107$4'},
                                      {'n': '文化', 'v': '106$4'},
                                      {'n': '二次元', 'v': '104$4'}]}])

    def process_kuaishou(self):
        return ('kuaishou', [{'key': 'cate', 'name': '分类',
                              'value': [{'n': '热门', 'v': 'hot'},
                                        {'n': '游戏', 'v': 'game'},
                                        {'n': '才艺', 'v': 'talent'},
                                        {'n': '二次元', 'v': 'acg'},
                                        {'n': '音乐', 'v': 'music'},
                                        {'n': '知识', 'v': 'knowledge'},
                                        {'n': '户外', 'v': 'outdoor'},
                                        {'n': '美食', 'v': 'food'},
                                        {'n': '体育', 'v': 'sports'},
                                        {'n': '购物', 'v': 'shopping'}]}])

    def process_bili(self):
        result = {}
        cateManual = {
            "快手": "kuaishou",
            "虎牙": "huya",
            "斗鱼": "douyu",
            "网易": "wangyi",
            "B站": "bili",
            "抖音": "douyin"
        }
        classes = []
        filters = {
            'huya': [{'key': 'cate', 'name': '分类',
                      'value': [{'n': '网游', 'v': '1'}, {'n': '单机', 'v': '2'},
                                {'n': '娱乐', 'v': '8'}, {'n': '手游', 'v': '3'}]}]
        }

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.process_kuaishou): 'kuaishou',
                executor.submit(self.process_bili): 'bili',
                executor.submit(self.process_douyu): 'douyu',
                executor.submit(self.process_douyin): 'douyin'
            }

            for future in futures:
                platform, filter_data = future.result()
                if filter_data:
                    filters[platform] = filter_data

        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {}
        pagecount = 9999
        result['page'] = pg
        result['limit'] = 90
        result['total'] = 999999
        if tid == 'wangyi':
            vdata, pagecount = self.wyccContent(tid, pg, filter, extend, vdata)
        elif 'kuaishou' in tid:
            vdata, pagecount = self.kuaishouContent(tid, pg, filter, extend, vdata)
        elif 'bili' in tid:
            vdata, pagecount = self.biliContent(tid, pg, filter, extend, vdata)
        elif 'huya' in tid:
            vdata, pagecount = self.huyaContent(tid, pg, filter, extend, vdata)
        elif 'douyu' in tid:
            vdata, pagecount = self.douyuContent(tid, pg, filter, extend, vdata)
        elif 'douyin' in tid:
            vdata, pagecount = self.douyinContent(tid, pg, filter, extend, vdata)
        elif 'kuaishou' in tid:
            vdata, pagecount = self.kuaishouContent(tid, pg, filter, extend, vdata)
        result['list'] = vdata
        result['pagecount'] = pagecount
        return result

    def wyccContent(self, tid, pg, filter, extend, vdata):
        params = {
            'format': 'json',
            'start': (int(pg) - 1) * 20,
            'size': '20',
        }
        response = self.fetch(f'{self.hosts[tid]}/api/category/live/', params=params, headers=self.headers[0]).json()
        for i in response['lives']:
            if i.get('cuteid'):
                bvdata = self.buildvod(
                    vod_id=f"{tid}@@{i['cuteid']}",
                    vod_name=i.get('title'),
                    vod_pic=i.get('cover'),
                    vod_remarks=i.get('nickname'),
                    style={"type": "rect", "ratio": 1.33}
                )
                vdata.append(bvdata)
        return vdata, 9999

    def biliContent(self, tid, pg, filter, extend, vdata):
        try:
            cid = extend.get('cate', tid) if extend else tid
            url = f'https://search.bilibili.com/live?keyword={cid}&page={pg}'

            req_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
                'Referer': 'https://www.bilibili.com/'
            }

            detail = requests.get(url=url, headers=req_headers)
            detail.encoding = "utf-8"
            doc = BeautifulSoup(detail.text, "lxml")

            for vod in doc.find_all('div', class_="video-list-item"):
                names = vod.find('h3', class_="bili-live-card__info--tit")
                if not names:
                    continue
                name = names.text.strip().replace('直播中', '')
                link = names.find('a')['href']
                room_id = link.split('bilibili.com/')[1].split('?')[0] if 'bilibili.com/' in link else ''
                if not room_id:
                    continue
                pic = vod.find('img')['src']
                if 'http' not in pic:
                    pic = "https:" + pic
                remarks = vod.find('a', class_="bili-live-card__info--uname")
                remark = remarks.text.strip() if remarks else ''

                v = self.buildvod(
                    vod_id=f"bili@@{room_id}",
                    vod_name=name,
                    vod_pic=pic,
                    vod_remarks=remark,
                    style={"type": "rect", "ratio": 1.33}
                )
                vdata.append(v)

            return vdata, 9999
        except Exception as e:
            print(f"B站内容获取错误: {e}")
            return vdata, 1

    def douyinContent(self, tid, pg, filter, extend, vdata):
        try:
            cid = extend.get('cate', '10000$3') if extend else '10000$3'
            page = int(pg or 1)
            offset = 15 * (page - 1)
            parts = cid.split('$')
            if len(parts) < 2:
                return vdata, 1
            partition, ptype = parts[0], parts[1]

            params = {
                "aid": "6383",
                "app_name": "douyin_web",
                "live_id": "1",
                "device_platform": "web",
                "language": "zh-CN",
                "browser_language": "zh-CN",
                "browser_platform": "Win32",
                "browser_name": "Chrome",
                "browser_version": "120.0.0.0",
                "partition": partition,
                "partition_type": ptype,
                "count": "15",
                "offset": str(offset),
                "web_rid": self._generate_device_id(),
                "cookie_enabled": "true",
                "screen_width": "1920",
                "screen_height": "1080"
            }

            headers = self._get_douyin_headers()
            urls = [
                "https://live.douyin.com/webcast/web/partition/detail/room/v2/",
                "https://webcast.amemv.com/webcast/web/partition/detail/room/v2/",
            ]

            for url in urls:
                try:
                    resp = self.fetch(url, headers=headers, params=params, verify=False)
                    data = resp.json()
                    if data.get('status_code') != 0:
                        continue
                    if not data.get('data', {}).get('data'):
                        break
                    items = data['data']['data']
                    for it in items:
                        web_rid = it.get('web_rid') or self._generate_device_id()
                        room = it['room']
                        v = self.buildvod(
                            vod_id=f"douyin@@{web_rid}@@{room['id_str']}",
                            vod_name=room['title'],
                            vod_pic=room['cover']['url_list'][0],
                            vod_remarks=f"{room['owner']['nickname']} (🔥{room['stats']['user_count_str']})",
                            style={"type": "rect", "ratio": 1.33}
                        )
                        vdata.append(v)
                    break
                except Exception:
                    continue

            return vdata, 9999
        except Exception as e:
            print(f"抖音内容获取错误: {e}")
            return vdata, 1

    def kuaishouContent(self, tid, pg, filter, extend, vdata):
        try:
            tag = extend.get('cate', 'hot') if extend else 'hot'
            page = int(pg or 1)

            ks_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://live.kuaishou.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }

            if tag == 'hot':
                page_url = 'https://live.kuaishou.com/'
            else:
                page_url = f'https://live.kuaishou.com/tag/{tag}'

            resp = requests.get(page_url, headers=ks_headers, timeout=15)
            if resp.status_code != 200:
                return vdata, 1

            soup = BeautifulSoup(resp.text, 'lxml')
            scripts = soup.find_all('script')

            # Strategy 1: 从页面嵌入式 JSON 中提取
            rooms = []
            for script in scripts:
                text = script.string
                if not text:
                    continue
                for pattern in [r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                                r'window\.__NUXT__\s*=\s*({.*?});']:
                    match = re.search(pattern, text, re.DOTALL)
                    if not match:
                        continue
                    try:
                        jdata = json.loads(match.group(1))
                        candidates = []
                        # 尝试多种可能的 JSON 路径
                        for path in [['liveroom', 'liveStream', 'feeds'],
                                     ['feeds'], ['liveRooms'],
                                     ['data', 'list'], ['data', 'rooms'],
                                     ['props', 'pageProps', 'list']]:
                            cur = jdata
                            found = True
                            for key in path:
                                if isinstance(cur, dict) and key in cur:
                                    cur = cur[key]
                                else:
                                    found = False
                                    break
                            if found and isinstance(cur, list):
                                candidates = cur
                                break
                        for item in candidates:
                            if isinstance(item, dict):
                                user_id = (item.get('user_id') or item.get('id_str') or
                                           item.get('userId') or item.get('author', {}).get('id', ''))
                                if not user_id:
                                    continue
                                nick = (item.get('user_name') or item.get('nickname') or
                                        item.get('author', {}).get('name', user_id))
                                title = (item.get('caption') or item.get('title') or nick)
                                cover = (item.get('cover_url') or item.get('cover') or
                                         item.get('coverUrl', ''))
                                watching = (item.get('watching_count') or item.get('user_count') or
                                            item.get('watchingCount', 0))
                                rooms.append((str(user_id), str(nick), str(title), str(cover), str(watching)))
                    except Exception:
                        continue

            if rooms:
                for user_id, nick, title, cover, watching in rooms:
                    v = self.buildvod(
                        vod_id=f"kuaishou@@{user_id}",
                        vod_name=title,
                        vod_pic=cover,
                        vod_remarks=f"{nick} (观看:{watching})",
                        style={"type": "rect", "ratio": 1.33}
                    )
                    vdata.append(v)
                return vdata, 9999

            # Strategy 2: HTML 解析 (针对非 SPA 页面)
            for selector in [('div', {'class': 'live-card'}),
                             ('a', {'href': re.compile(r'/u/')}),
                             ('div', {'class': re.compile(r'live')}),
                             ('li', {'class': re.compile(r'live')})]:
                cards = soup.find_all(selector[0], selector[1])
                if not cards:
                    continue
                for card in cards:
                    if card.name == 'a':
                        link = card.get('href', '')
                    else:
                        a_tag = card.find('a', href=re.compile(r'/u/'))
                        link = a_tag.get('href', '') if a_tag else ''
                    if not link or '/u/' not in link:
                        continue
                    user_id = link.split('/u/')[-1].split('?')[0]
                    name_el = card.find('h3') or card.find('p', class_='name') or card.find('span', class_='name')
                    name = name_el.text.strip() if name_el else user_id
                    pic_el = card.find('img')
                    pic = pic_el.get('src', '') if pic_el else ''
                    v = self.buildvod(
                        vod_id=f"kuaishou@@{user_id}",
                        vod_name=name,
                        vod_pic=pic,
                        vod_remarks='快手直播',
                        style={"type": "rect", "ratio": 1.33}
                    )
                    vdata.append(v)
                if vdata:
                    return vdata, 9999

            return vdata, 1
        except Exception as e:
            print(f"快手内容获取错误: {e}")
            return vdata, 1

    def huyaContent(self, tid, pg, filter, extend, vdata):
        if extend.get('cate') and pg == '1' and 'click' not in tid:
            id = extend.get('cate')
            data = self.fetch(f'{self.referers[tid]}/liveconfig/game/bussLive?bussType={id}',
                              headers=self.headers[1]).json()
            for i in data['data']:
                v = self.buildvod(
                    vod_id=f"click_{tid}@@{int(i['gid'])}",
                    vod_name=i.get('gameFullName'),
                    vod_pic=f'https://huyaimg.msstatic.com/cdnimage/game/{int(i["gid"])}-MS.jpg',
                    vod_tag=1,
                    style={"type": "oval", "ratio": 1}
                )
                vdata.append(v)
            return vdata, 1
        else:
            gid = ''
            if 'click' in tid:
                ids = tid.split('_')[1].split('@@')
                tid = ids[0]
                gid = f'&gameId={ids[1]}'
            data = self.fetch(f'{self.hosts[tid][0]}/cache.php?m=LiveList&do=getLiveListByPage&tagAll=0{gid}&page={pg}',
                              headers=self.headers[1]).json()
            for i in data['data']['datas']:
                if i.get('profileRoom'):
                    v = self.buildvod(
                        f"{tid}@@{i['profileRoom']}",
                        i.get('introduction'),
                        i.get('screenshot'),
                        str(int(i.get('totalCount', '1')) / 10000) + '万',
                        0,
                        i.get('nick'),
                        style={"type": "rect", "ratio": 1.33}

                    )
                    vdata.append(v)
            return vdata, 9999

    def douyuContent(self, tid, pg, filter, extend, vdata):
        if extend.get('cate') and pg == '1' and 'click' not in tid:
            for i in self.dyufdata['data']['cate2Info']:
                if str(i['cate1Id']) == extend['cate']:
                    v = self.buildvod(
                        vod_id=f"click_{tid}@@{i['cate2Id']}",
                        vod_name=i.get('cate2Name'),
                        vod_pic=i.get('icon'),
                        vod_remarks=i.get('count'),
                        vod_tag=1,
                        style={"type": "oval", "ratio": 1}
                    )
                    vdata.append(v)
            return vdata, 1
        else:
            path = f'/japi/weblist/apinc/allpage/6/{pg}'
            if 'click' in tid:
                ids = tid.split('_')[1].split('@@')
                tid = ids[0]
                path = f'/gapi/rkc/directory/mixList/2_{ids[1]}/{pg}'
            url = f'{self.hosts[tid]}{path}'
            data = self.fetch(url, headers=self.headers[1]).json()
            for i in data['data']['rl']:
                v = self.buildvod(
                    vod_id=f"{tid}@@{i['rid']}",
                    vod_name=i.get('rn'),
                    vod_pic=i.get('rs16'),
                    vod_year=str(int(i.get('ol', 1)) / 10000) + '万',
                    vod_remarks=i.get('nn'),
                    style={"type": "rect", "ratio": 1.33}
                )
                vdata.append(v)
            return vdata, 9999

    def detailContent(self, ids):
        ids = ids[0].split('@@')
        if ids[0] == 'wangyi':
            vod = self.wyccDetail(ids)
        elif ids[0] == 'kuaishou':
            vod = self.kuaishouDetail(ids)
        elif ids[0] == 'bili':
            vod = self.biliDetail(ids)
        elif ids[0] == 'huya':
            vod = self.huyaDetail(ids)
        elif ids[0] == 'douyu':
            vod = self.douyuDetail(ids)
        elif ids[0] == 'douyin':
            vod = self.douyinDetail(ids)
        return {'list': [vod]}

    def wyccDetail(self, ids):
        try:
            vdata = self.getpq(f'{self.hosts[ids[0]]}/{ids[1]}', self.headers[0])('script').eq(-1).text()

            def get_quality_name(vbr):
                if vbr <= 600:
                    return "标清"
                elif vbr <= 1000:
                    return "高清"
                elif vbr <= 2000:
                    return "超清"
                else:
                    return "蓝光"

            data = json.loads(vdata)['props']['pageProps']['roomInfoInitData']
            name = data['live'].get('title', ids[0])
            vod = self.buildvod(vod_name=data.get('keywords_suffix'), vod_remarks=data['live'].get('title'),
                                vod_content=data.get('description_suffix'))
            resolution_data = data['live']['quickplay']['resolution']
            all_streams = {}
            sorted_qualities = sorted(resolution_data.items(),
                                      key=lambda x: x[1]['vbr'],
                                      reverse=True)
            for quality, data in sorted_qualities:
                vbr = data['vbr']
                quality_name = get_quality_name(vbr)
                for cdn_name, url in data['cdn'].items():
                    if cdn_name not in all_streams and type(url) == str and url.startswith('http'):
                        all_streams[cdn_name] = []
                    if isinstance(url, str) and url.startswith('http'):
                        all_streams[cdn_name].extend([quality_name, url])
            plists = []
            names = []
            for i, (cdn_name, stream_list) in enumerate(all_streams.items(), 1):
                names.append(f'线路{i}')
                pstr = f"{name}${ids[0]}@@{self.e64(json.dumps(stream_list))}"
                plists.append(pstr)
            vod['vod_play_from'] = "$$$".join(names)
            vod['vod_play_url'] = "$$$".join(plists)
            return vod
        except Exception as e:
            return self.handle_exception(e)

    def biliDetail(self, ids):
        try:
            room_id = ids[1]
            url = f'{self.hosts["bili"][0]}/xlive/web-room/v2/index/getRoomPlayInfo?room_id={room_id}&platform=web&protocol=0,1&format=0,1,2&codec=0,1'
            data = self.fetch(url, headers=self.headers[0]).json()

            content = '欢迎观看哔哩直播'
            vod = self.buildvod(vod_name='B站直播', vod_content=content)

            setup = data['data']['playurl_info']['playurl']['stream']

            bofang = ''
            xianlu = ''
            nam = 0
            for stream in setup:
                try:
                    host = stream['format'][nam]['codec'][0]['url_info'][1]['host']
                    base = stream['format'][nam]['codec'][0]['base_url']
                    extra = stream['format'][nam]['codec'][0]['url_info'][1]['extra']
                    url = host + base + extra
                    nam += 1
                    bofang += f'{nam}号线路$bili@@{url}#'
                except (KeyError, IndexError):
                    continue

            if bofang:
                bofang = bofang[:-1]
            xianlu = '哔哩专线'

            vod['vod_play_from'] = xianlu
            vod['vod_play_url'] = bofang
            return vod

        except Exception as e:
            print(f"B站详情错误: {e}")
            return self.handle_exception(e)

    def douyinDetail(self, ids):
        try:
            if len(ids) < 3:
                return self.handle_exception(Exception("抖音参数不足"))
            web_rid, room_id = ids[1], ids[2]

            url = "https://live.douyin.com/webcast/room/web/enter/"
            params = {
                "aid": "6383",
                "app_name": "douyin_web",
                "live_id": "1",
                "device_platform": "web",
                "enter_from": "web_live",
                "browser_language": "zh-CN",
                "browser_platform": "Win32",
                "browser_name": "Chrome",
                "browser_version": "120.0.0.0",
                "web_rid": web_rid,
                "room_id_str": room_id,
                "enter_source": "",
                "is_need_double_stream": "false"
            }

            headers = self._get_douyin_headers()
            r = self.fetch(url, params=params, headers=headers, verify=False)
            data = r.json()
            if not data.get('data', {}).get('data'):
                return self.handle_exception(Exception("抖音获取房间信息失败"))
            info = data['data']['data'][0]

            resolution_map = {
                "FULL_HD1": "蓝光",
                "HD1": "超清",
                "ORIGION": "原画",
                "SD1": "标清",
                "SD2": "高清"
            }

            flv_pull = info.get('stream_url', {}).get('flv_pull_url', {})
            flv_episodes = []
            for k, v in flv_pull.items():
                name = resolution_map.get(k, k)
                flv_episodes.append(f"{name}$douyin@@{v}")

            hls_pull = info.get('stream_url', {}).get('hls_pull_url_map', {})
            hls_episodes = []
            for k, v in hls_pull.items():
                name = resolution_map.get(k, k)
                hls_episodes.append(f"{name}$douyin@@{v}")

            vod_play_from = ""
            vod_play_url = ""
            if flv_episodes:
                vod_play_from += "FLV$$$"
                vod_play_url += "#".join(flv_episodes) + "$$$"
            if hls_episodes:
                vod_play_from += "HLS"
                vod_play_url += "#".join(hls_episodes)

            vod_play_from = vod_play_from.rstrip("$$$")
            vod_play_url = vod_play_url.rstrip("$$$")

            vod = self.buildvod(
                vod_name=info['title'],
                vod_pic=info['cover']['url_list'][0],
                vod_actor=info['owner']['nickname'],
                vod_content=info['title'],
                vod_play_from=vod_play_from,
                vod_play_url=vod_play_url
            )
            return vod
        except Exception as e:
            print(f"抖音详情错误: {e}")
            return self.handle_exception(e)

    def kuaishouDetail(self, ids):
        try:
            if len(ids) < 2:
                return self.handle_exception(Exception("快手参数不足"))
            user_id = ids[1]

            ks_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://live.kuaishou.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }

            url = f'{self.hosts["kuaishou"]}/u/{user_id}'
            resp = self.fetch(url, headers=ks_headers, verify=False)
            html = resp.text

            # 解析 window.__INITIAL_STATE__ 或最后一个 script 标签中的 JSON
            soup = BeautifulSoup(html, 'lxml')
            scripts = soup.find_all('script')
            init_state = None

            for script in scripts:
                text = script.string
                if not text:
                    continue
                # 尝试匹配 window.__INITIAL_STATE__
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', text, re.DOTALL)
                if match:
                    try:
                        init_state = json.loads(match.group(1))
                        break
                    except Exception:
                        pass
                # 尝试匹配最后一个包含 liveroom 的 script
                if 'liveroom' in text and 'liveStream' in text:
                    try:
                        json_match = re.search(r'\{.*"liveroom".*\}', text, re.DOTALL)
                        if json_match:
                            init_state = json.loads(json_match.group(0))
                            break
                    except Exception:
                        pass

            if not init_state:
                # 尝试从最后一个 script 提取
                for script in reversed(scripts):
                    text = script.string
                    if text and ('liveroom' in text or 'liveStream' in text):
                        try:
                            # 尝试提取 JSON 对象
                            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                            if json_match:
                                init_state = json.loads(json_match.group(1))
                                break
                        except Exception:
                            continue

            if not init_state:
                return self.handle_exception(Exception("快手解析页面数据失败"))

            liveroom = init_state.get('liveroom', init_state)
            if not liveroom:
                return self.handle_exception(Exception("快手未获取到直播信息"))

            live_stream = liveroom.get('liveStream', liveroom)
            author = liveroom.get('author', {})
            nick = author.get('name', user_id)
            title = live_stream.get('caption', nick)

            play_urls = live_stream.get('playUrls', [])
            if not play_urls:
                return self.handle_exception(Exception("快手无可用播放地址"))

            episodes = []
            for pu in play_urls:
                adapt_set = pu.get('adaptationSet', {})
                representations = adapt_set.get('representation', [])
                if not isinstance(representations, list):
                    representations = [representations]
                for rep in representations:
                    quality = rep.get('name', '流畅')
                    url = rep.get('url', '') or rep.get('mainUrl', '')
                    if url:
                        episodes.append(f"{quality}$kuaishou@@{url}")

            if not episodes:
                return self.handle_exception(Exception("快手无可用播放地址"))

            vod = self.buildvod(
                vod_name=title,
                vod_actor=nick,
                vod_content=title,
                vod_play_from='快手直播',
                vod_play_url='#'.join(episodes)
            )
            return vod

        except Exception as e:
            print(f"快手详情错误: {e}")
            return self.handle_exception(e)

    def huyaDetail(self, ids):
        try:
            room_id = ids[1]

            api_url = f'{self.hosts[ids[0]][1]}/cache.php?m=Live&do=profileRoom&roomid={room_id}'
            res = self.fetch(api_url, headers=self.headers[0])

            if res.status_code != 200:
                return self.handle_exception(Exception(f"API请求失败: {res.status_code}"))

            data = res.json()
            if not data or not data.get('data'):
                return self.handle_exception(Exception("房间数据为空"))

            room_data = data['data']

            uid = room_data.get('profileInfo', {}).get('uid')
            stream_info = room_data.get('stream', {})
            live_data = room_data.get('liveData', {})

            if not uid:
                return self.handle_exception(Exception("缺少uid"))

            base_stream_list = stream_info.get('baseSteamInfoList', [])
            if not base_stream_list:
                return self.handle_exception(Exception("无直播流信息"))

            base_stream = base_stream_list[0]
            stream_name = base_stream.get('sStreamName')
            if not stream_name:
                return self.handle_exception(Exception("无法获取streamName"))

            vod = self.buildvod(
                vod_name=live_data.get('introduction', '虎牙直播'),
                type_name=live_data.get('gameFullName', ''),
                vod_director=live_data.get('nick', ''),
                vod_remarks=live_data.get('contentIntro', ''),
            )

            cdn_list = []
            for stream in base_stream_list:
                cdn_type = stream.get('sCdnType', 'AL')
                flv_url = stream.get('sFlvUrl', '')
                hls_url = stream.get('sHlsUrl', '')
                stream_name_cdn = stream.get('sStreamName', stream_name)

                if flv_url:
                    cdn_list.append({
                        'cdn': cdn_type,
                        'flv_base': flv_url,
                        'hls_base': hls_url,
                        'stream_name': stream_name_cdn,
                        'priority': stream.get('iWebPriorityRate', 0)
                    })

            cdn_list.sort(key=lambda x: x['priority'], reverse=True)

            rate_array = stream_info.get('rateArray', [])

            if not rate_array and 'vMultiStreamInfo' in room_data:
                rate_array = room_data['vMultiStreamInfo']

            if not rate_array:
                rate_array = [
                    {'sDisplayName': '蓝光4M', 'iBitRate': 4000},
                    {'sDisplayName': '蓝光', 'iBitRate': 3000},
                    {'sDisplayName': '超清', 'iBitRate': 2000},
                    {'sDisplayName': '高清', 'iBitRate': 1200},
                    {'sDisplayName': '流畅', 'iBitRate': 500}
                ]

            filtered_rates = []
            seen_bitrates = set()

            for rate in rate_array:
                bit_rate = rate.get('iBitRate', 0)
                name = rate.get('sDisplayName', '')

                if bit_rate in seen_bitrates:
                    continue

                if bit_rate == 2000 and ('高清' in name or '720' in name):
                    name = '超清'
                elif bit_rate == 1200 and ('标清' in name or '480' in name):
                    name = '高清'
                elif bit_rate == 2000 and name == '原画':
                    name = '超清'

                seen_bitrates.add(bit_rate)
                filtered_rates.append({
                    'sDisplayName': name,
                    'iBitRate': bit_rate
                })

            sorted_rates = sorted(filtered_rates, key=lambda x: x['iBitRate'], reverse=True)

            play_lines = []
            line_names = []

            for cdn_idx, cdn in enumerate(cdn_list[:3]):
                cdn_name = cdn['cdn']
                line_names.append(f"线路{cdn_idx + 1}({cdn_name})")

                qualities = []
                for rate in sorted_rates:
                    quality_name = rate['sDisplayName']
                    bit_rate = rate['iBitRate']

                    quality_url = self._generate_huya_play_url(
                        cdn, uid, stream_name, bit_rate
                    )

                    qualities.extend([quality_name, quality_url])

                encoded_qualities = self.e64(json.dumps(qualities))
                play_lines.append(f"{live_data.get('introduction', '直播')}${ids[0]}@@{encoded_qualities}")

            vod['vod_play_from'] = "$$$".join(line_names)
            vod['vod_play_url'] = "$$$".join(play_lines)

            return vod

        except Exception as e:
            return self.handle_exception(e)

    def _generate_huya_play_url(self, cdn, uid, stream_name, bit_rate):
        flv_base = cdn['flv_base']
        stream = cdn['stream_name']

        timestamp = int(time.time())
        seqid = f"{uid}{timestamp}"
        ss = hashlib.md5(f"{seqid}|huya_adr|102".encode()).hexdigest()
        ws_time = hex(timestamp + 21600)[2:]

        ws_secret = hashlib.md5(
            f"DWq8BcJ3h6DJt6TY_{uid}_{stream_name}_{ss}_{ws_time}".encode()
        ).hexdigest()

        base_url = f"{flv_base}/{stream}.flv"

        if bit_rate > 0:
            ratio_param = f"ratio={bit_rate}"
        else:
            ratio_param = "ratio=2000"

        play_url = (
            f"{base_url}?{ratio_param}&wsSecret={ws_secret}&wsTime={ws_time}"
            f"&ctype=huya_adr&seqid={seqid}&uid={uid}"
            f"&fs=bgct&ver=1&t=102"
        )

        return play_url

    def douyuDetail(self, ids):
        try:
            channel = ids[1]
            headers = self.gethr(0, zr=f'{self.hosts[ids[0]]}/{channel}')

            session = {}

            try:
                home_res = self.fetch(f'{self.hosts[ids[0]]}/{channel}', headers=headers)
                if home_res.headers.get('Set-Cookie'):
                    cookie_str = home_res.headers.get('Set-Cookie')
                    did_match = re.search(r'dy_did=([a-f0-9]{32})', cookie_str)
                    if did_match:
                        device_id = did_match.group(1)
                    else:
                        device_id = self._generate_random_hex(32)
                else:
                    device_id = self._generate_random_hex(32)
            except:
                device_id = self._generate_random_hex(32)

            session['dy_did'] = device_id
            session['mantine-color-scheme-value'] = 'light'

            betard_res = self.fetch(f'{self.hosts[ids[0]]}/betard/{channel}', headers=headers).json()
            if not betard_res or not betard_res.get('room'):
                return self.handle_exception(Exception("获取房间信息失败"))

            room_info = betard_res['room']
            vname = room_info.get('room_name', '斗鱼直播')

            vod = self.buildvod(
                vod_name=vname,
                vod_remarks=room_info.get('second_lvl_name', ''),
                vod_director=room_info.get('nickname', ''),
            )

            sec_url = f"{self.hosts[ids[0]]}/wgapi/livenc/liveweb/websec/getEncryption?did={device_id}"
            sec_res = self.fetch(sec_url, headers=headers).json()

            if not sec_res or sec_res.get('error') != 0:
                return self.handle_exception(Exception("获取加密密钥失败"))

            security_data = sec_res['data']
            secret_key = security_data.get('key')
            random_str = security_data.get('rand_str')
            enc_time = security_data.get('enc_time', 1)
            enc_data = security_data.get('enc_data')

            current_time = int(time.time())

            current = random_str
            for _ in range(enc_time):
                current = hashlib.md5(f"{current}{secret_key}".encode()).hexdigest()

            signature = hashlib.md5(f"{current}{secret_key}{channel}{current_time}".encode()).hexdigest()

            play_payload = {
                'enc_data': enc_data,
                'tt': str(current_time),
                'did': device_id,
                'auth': signature,
                'cdn': '',
                'rate': '',
                'hevc': '0',
                'fa': '0',
                'ive': '0'
            }

            play_api = f"{self.hosts[ids[0]]}/lapi/live/getH5PlayV1/{channel}"

            play_headers = headers.copy()
            cookie_str = '; '.join([f"{k}={v}" for k, v in session.items()])
            play_headers['Cookie'] = cookie_str
            play_headers['Content-Type'] = 'application/x-www-form-urlencoded'

            play_res = requests.post(play_api, data=play_payload, headers=play_headers, timeout=10).json()

            if not play_res or play_res.get('error') != 0:
                play_res = self._try_legacy_douyu_api(channel, device_id, signature, current_time, play_headers)
                if not play_res:
                    return self.handle_exception(Exception("获取播放地址失败"))

            stream_info = play_res.get('data', {})

            rtmp_live = stream_info.get('rtmp_live', '')
            if rtmp_live:
                did_match = re.search(r'did=([a-f0-9]{32})', rtmp_live)
                if did_match and did_match.group(1) != device_id:
                    device_id = did_match.group(1)
                    session['dy_did'] = device_id
                    play_payload['did'] = device_id
                    play_res = requests.post(play_api, data=play_payload, headers=play_headers, timeout=10).json()
                    if play_res and play_res.get('error') == 0:
                        stream_info = play_res.get('data', {})

            stream_url = None
            if stream_info.get('rtmp_url') and stream_info.get('rtmp_live'):
                stream_url = f"{stream_info['rtmp_url']}/{stream_info['rtmp_live']}"
            elif stream_info.get('hls_url'):
                stream_url = stream_info['hls_url']

            if not stream_url:
                return self.handle_exception(Exception("无法获取播放地址"))

            multirates = stream_info.get('multirates', [])

            qualities = []

            if multirates:
                sorted_rates = sorted(multirates, key=lambda x: x.get('bit', 0), reverse=True)
                for rate in sorted_rates:
                    bit_rate = rate.get('rate', -1)
                    name = rate.get('name', f"{bit_rate}P")

                    qualities.extend([name, f"#{bit_rate}"])
            else:
                qualities = ['原画', '#-1']

            session_info = {
                'channel': channel,
                'device_id': device_id,
                'secret_key': secret_key,
                'random_str': random_str,
                'enc_time': enc_time,
                'enc_data': enc_data
            }
            encoded_session = self.e64(json.dumps(session_info))

            encoded_qualities = self.e64(json.dumps(qualities))
            vod['vod_play_from'] = '斗鱼直播'
            vod['vod_play_url'] = f"{vname}${ids[0]}@@{encoded_qualities}@@{encoded_session}"

            return vod

        except Exception as e:
            return self.handle_exception(e)

    def _generate_random_hex(self, length):
        hex_chars = '0123456789abcdef'
        return ''.join(random.choice(hex_chars) for _ in range(length))

    def _try_legacy_douyu_api(self, channel, device_id, signature, timestamp, headers):
        try:
            legacy_payload = {
                'did': device_id,
                'tt': str(timestamp),
                'sign': signature,
                'cdn': '',
                'rate': '-1',
                'ver': 'Douyu_223061205',
                'iar': '1',
                'ive': '1',
                'hevc': '0',
                'fa': '0'
            }
            legacy_api = f"https://www.douyu.com/lapi/live/getH5Play/{channel}"
            res = requests.post(legacy_api, data=legacy_payload, headers=headers, timeout=10)
            return res.json() if res.status_code == 200 else None
        except:
            return None

    def _get_douyu_play_url(self, channel, device_id, secret_key, random_str, enc_time, enc_data, rate):
        try:
            current_time = int(time.time())

            current = random_str
            for _ in range(enc_time):
                current = hashlib.md5(f"{current}{secret_key}".encode()).hexdigest()

            signature = hashlib.md5(f"{current}{secret_key}{channel}{current_time}".encode()).hexdigest()

            play_payload = {
                'enc_data': enc_data,
                'tt': str(current_time),
                'did': device_id,
                'auth': signature,
                'cdn': '',
                'rate': str(rate) if rate > 0 else '',
                'hevc': '0',
                'fa': '0',
                'ive': '0'
            }

            play_api = f"https://www.douyu.com/lapi/live/getH5PlayV1/{channel}"

            headers = {
                'User-Agent': self.headers[0]['User-Agent'],
                'Referer': f'https://www.douyu.com/{channel}',
                'Origin': 'https://www.douyu.com',
                'Cookie': f'dy_did={device_id}; mantine-color-scheme-value=light',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            play_res = requests.post(play_api, data=play_payload, headers=headers, timeout=10).json()

            if not play_res or play_res.get('error') != 0:
                return self._get_douyu_play_url_legacy(channel, device_id, signature, current_time, rate)

            stream_info = play_res.get('data', {})

            if stream_info.get('rtmp_live'):
                did_match = re.search(r'did=([a-f0-9]{32})', stream_info['rtmp_live'])
                if did_match and did_match.group(1) != device_id:
                    return self._get_douyu_play_url(channel, did_match.group(1), secret_key, random_str, enc_time, enc_data, rate)

            if stream_info.get('rtmp_url') and stream_info.get('rtmp_live'):
                return f"{stream_info['rtmp_url']}/{stream_info['rtmp_live']}"
            elif stream_info.get('hls_url'):
                return stream_info['hls_url']

            return None
        except Exception as e:
            print(f"获取斗鱼播放URL失败: {e}")
            return None

    def _get_douyu_play_url_legacy(self, channel, device_id, signature, timestamp, rate):
        try:
            legacy_payload = {
                'did': device_id,
                'tt': str(timestamp),
                'sign': signature,
                'cdn': '',
                'rate': str(rate) if rate > 0 else '-1',
                'ver': 'Douyu_223061205',
                'iar': '1',
                'ive': '1',
                'hevc': '0',
                'fa': '0'
            }
            legacy_api = f"https://www.douyu.com/lapi/live/getH5Play/{channel}"

            headers = {
                'User-Agent': self.headers[0]['User-Agent'],
                'Referer': f'https://www.douyu.com/{channel}',
                'Cookie': f'dy_did={device_id}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            res = requests.post(legacy_api, data=legacy_payload, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get('error') == 0:
                    stream_info = data.get('data', {})
                    if stream_info.get('rtmp_url') and stream_info.get('rtmp_live'):
                        return f"{stream_info['rtmp_url']}/{stream_info['rtmp_live']}"
            return None
        except:
            return None

    def searchContent(self, key, quick, pg="1"):
        pass

    def playerContent(self, flag, id, vipFlags):
        try:
            ids = id.split('@@')
            p = 1
            if ids[0] in ['wangyi']:
                p, url = 0, json.loads(self.d64(ids[1]))
            elif ids[0] == 'kuaishou':
                p, url = 0, ids[1] if len(ids) > 1 else id
            elif ids[0] == 'bili':
                p, url = 0, ids[1] if len(ids) > 1 else id
            elif ids[0] == 'huya':
                p, url = self.huyaplay(ids)
            elif ids[0] == 'douyu':
                p, url = self.douyuplay(ids)
            elif ids[0] == 'douyin':
                p, url = 0, ids[1] if len(ids) > 1 else id
            return {'parse': p, 'url': url, 'header': self.playheaders[ids[0]]}
        except Exception as e:
            return {'parse': 1, 'url': self.excepturl, 'header': self.headers[0]}

    def huyaplay(self, ids):
        try:
            decoded = json.loads(self.d64(ids[1]))
            return 0, decoded
        except Exception as e:
            print(f"虎牙播放解析错误: {e}")
            return 1, self.excepturl

    def douyuplay(self, ids):
        try:
            if len(ids) < 3:
                decoded = json.loads(self.d64(ids[1]))
                return 0, decoded

            qualities = json.loads(self.d64(ids[1]))
            session_info = json.loads(self.d64(ids[2]))

            channel = session_info['channel']
            device_id = session_info['device_id']
            secret_key = session_info['secret_key']
            random_str = session_info['random_str']
            enc_time = session_info['enc_time']
            enc_data = session_info['enc_data']

            result = []
            for i in range(0, len(qualities), 2):
                name = qualities[i]
                rate_marker = qualities[i + 1]

                if rate_marker.startswith('#'):
                    rate = int(rate_marker[1:])
                else:
                    rate = -1

                play_url = self._get_douyu_play_url(
                    channel, device_id, secret_key, random_str,
                    enc_time, enc_data, rate
                )

                if play_url:
                    result.extend([name, play_url])

            if not result:
                return 1, self.excepturl

            return 0, result
        except Exception as e:
            print(f"斗鱼播放解析错误: {e}")
            return 1, self.excepturl

    # ==================== 抖音辅助方法 ====================

    def _generate_device_id(self):
        timestamp = self._base36_encode(int(time.time() * 1000))
        random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=13))
        return f"{timestamp}{random_part}"

    @staticmethod
    def _base36_encode(num):
        alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
        if num == 0:
            return '0'
        res = []
        while num > 0:
            num, rem = divmod(num, 36)
            res.append(alphabet[rem])
        return ''.join(reversed(res))

    def _get_douyin_cookie(self):
        if self.dy_cookie_cache:
            return self.dy_cookie_cache
        try:
            resp = self.fetch(self.hosts['douyin'], headers=self.headers[0], verify=False)
            cookies = resp.headers.get('set-cookie', '')
            if cookies:
                match = re.search(r'ttwid=([^;]+)', cookies)
                if match:
                    self.dy_cookie_cache = f"ttwid={match.group(1)}"
        except Exception:
            pass
        return self.dy_cookie_cache

    def _get_douyin_headers(self):
        cookie = self._get_douyin_cookie()
        hd = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.hosts['douyin']
        }
        if cookie:
            hd["Cookie"] = cookie
        return hd

    def localProxy(self, param):
        pass

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def josn_to_params(self, params, skip_empty=False):
        query = []
        for k, v in params.items():
            if skip_empty and not v:
                continue
            query.append(f"{k}={v}")
        return "&".join(query)

    def params_to_json(self, query_string):
        parsed_data = parse_qs(query_string)
        result = {key: value[0] for key, value in parsed_data.items()}
        return result

    def buildvod(self, vod_id='', vod_name='', vod_pic='', vod_year='', vod_tag='', vod_remarks='', style='',
                 type_name='', vod_area='', vod_actor='', vod_director='',
                 vod_content='', vod_play_from='', vod_play_url=''):
        vod = {
            'vod_id': vod_id,
            'vod_name': vod_name,
            'vod_pic': vod_pic,
            'vod_year': vod_year,
            'vod_tag': 'folder' if vod_tag else '',
            'vod_remarks': vod_remarks,
            'style': style,
            'type_name': type_name,
            'vod_area': vod_area,
            'vod_actor': vod_actor,
            'vod_director': vod_director,
            'vod_content': vod_content,
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url
        }
        vod = {key: value for key, value in vod.items() if value}
        return vod

    def getpq(self, url, headers=None, cookies=None):
        data = self.fetch(url, headers=headers, cookies=cookies).text
        try:
            return pq(data)
        except Exception as e:
            print(f"解析页面错误: {str(e)}")
            return pq(data.encode('utf-8'))

    def gethr(self, index, rf='', zr=''):
        headers = self.headers[index]
        if zr:
            headers['referer'] = zr
        else:
            headers['referer'] = f"{self.referers[rf]}/"
        return headers

    def handle_exception(self, e):
        print(f"报错: {str(e)}")
        return {'vod_play_from': '哎呀翻车啦', 'vod_play_url': f'翻车啦${self.excepturl}'}
