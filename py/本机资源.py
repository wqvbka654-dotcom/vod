# 本地资源管理.py - 最终修复版 + 海报获取功能（完整版）
# 基于资源flac内置歌词正常MP3内置乱码版本.py
# 修改：添加网络自动获取歌曲海报功能，并在详情页显示
# 修改：歌词获取逻辑改为 网络优先 -> 本地歌词 -> 内置歌词（增强版）
# 修改：添加详细的歌词调试日志和更多歌词源

import sys
import re
import json
import os
import base64
import hashlib
import time
import urllib.parse
import sqlite3
import glob
from pathlib import Path
from base.spider import Spider

# ==================== 在线直播配置 ====================
ONLINE_LIVE_SOURCES = [
    {
        "id": "migu_live",
        "name": "咪咕直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt",
        "color": "#FF6B6B",
        "remarks": "央视/卫视直播",
        "type": "m3u",
        "ua": "com.android.chrome/3.7.0 (Linux;Android 15)",
        "playerType": 2
    },
    {
        "id": "gongdian_live",
        "name": "宫殿直播",
        "url": "https://gongdian.top/tv/iptv",
        "color": "#4ECDC4",
        "remarks": "宫殿直播源",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "playerType": 2
    },
    {
        "id": "simple_live",
        "name": "简单直播",
        "url": "http://gh-proxy.org/raw.githubusercontent.com/Supprise0901/TVBox_live/main/live.txt",
        "color": "#6BCB77",
        "remarks": "简单直播源",
        "type": "txt"
    }
]

LIVE_CATEGORY_ID = "online_live"
LIVE_CATEGORY_NAME = "📡 在线直播"
LIVE_CACHE_DURATION = 600

# ==================== 全局请求头自动适配配置 ====================
COMMON_HEADERS_LIST = [
    {
        "name": "Chrome浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    },
    {
        "name": "Firefox浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive"
        }
    },
    {
        "name": "okhttp/3",
        "headers": {
            "User-Agent": "okhttp/3.12.11",
            "Accept": "*/*",
            "Connection": "Keep-Alive"
        }
    },
    {
        "name": "手机浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    },
    {
        "name": "Edge浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    },
    {
        "name": "Safari浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    },
    {
        "name": "Android Chrome",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    }
]

DOMAIN_SPECIFIC_HEADERS = {
    "miguvideo.com": [
        {
            "name": "咪咕专用-Android Chrome",
            "headers": {
                "User-Agent": "com.android.chrome/3.7.0 (Linux;Android 15)",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Referer": "https://www.miguvideo.com/"
            }
        },
        {
            "name": "咪咕专用-okhttp",
            "headers": {
                "User-Agent": "okhttp/3.12.11",
                "Accept": "*/*",
                "Connection": "Keep-Alive",
                "Referer": "https://www.miguvideo.com/"
            }
        }
    ],
    "gongdian.top": [
        {
            "name": "宫殿直播专用",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Referer": "https://gongdian.top/",
                "Connection": "keep-alive"
            }
        }
    ],
    "t.061899.xyz": [
        {
            "name": "t源专用",
            "headers": {
                "User-Agent": "okhttp/3.12.11",
                "Referer": "http://t.061899.xyz/",
                "Accept": "*/*"
            }
        }
    ],
    "rihou.cc": [
        {
            "name": "日后源专用-Chrome",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://rihou.cc:555/",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive"
            }
        },
        {
            "name": "日后源专用-okhttp",
            "headers": {
                "User-Agent": "okhttp/3.12.11",
                "Referer": "http://rihou.cc:555/",
                "Accept": "*/*",
                "Connection": "Keep-Alive"
            }
        }
    ]
}
# ==================== 全局请求头自动适配配置结束 ====================

# ==================== 路径配置 ====================
ROOT_PATHS = [
    '/storage/emulated/0/Movies/',
    '/storage/emulated/0/Music/',
    '/storage/emulated/0/Download/KuwoMusic/music/',
    '/storage/emulated/0/Download/',
    '/storage/emulated/0/DCIM/Camera/',
    '/storage/emulated/0/Pictures/',
    '/storage/emulated/0/'
]

PATH_TO_CHINESE = {
    '/storage/emulated/0/Movies/': '电影',
    '/storage/emulated/0/Music/': '音乐',
    '/storage/emulated/0/Download/KuwoMusic/music/': '酷我音乐',
    '/storage/emulated/0/Download/': '下载',
    '/storage/emulated/0/DCIM/Camera/': '相机',
    '/storage/emulated/0/Pictures/': '图片',
    '/storage/emulated/0/': '根目录'
}

# ==================== 数据库兼容配置 ====================
DB_COMPAT_MODE = True
MAX_DB_RESULTS = 50000

DB_FIELD_MAPPING = {
    'id': ['id', 'vid', 'video_id', 'film_id', 'vod_id'],
    'name': ['name', 'title', 'vod_name', 'vod_title'],
    'url': ['url', 'link', 'play_url', 'video_url', 'vod_url', 'vod_play_url'],
    'image': ['image', 'pic', 'cover', 'poster', 'vod_pic'],
    'remarks': ['remarks', 'vod_remarks', 'remark', 'note']
}

print("ℹ️ 本地资源管理加载成功 - 最终修复版 + 海报获取功能 + 歌词优先网络版 + 增强调试")

class DatabaseReader:
    """数据库读取器 - 借鉴FileExplorer.php的优化方案"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 600
    
    def read_sqlite(self, db_path, limit=50000):
        cache_key = f"{db_path}_{os.path.getmtime(db_path)}_{limit}"
        current_time = time.time()
        
        if cache_key in self.cache and current_time - self.cache_time.get(cache_key, 0) < self.cache_duration:
            print(f"📊 使用缓存数据: {os.path.basename(db_path)}, {len(self.cache[cache_key])} 条记录")
            return self.cache[cache_key]
        
        if not os.path.exists(db_path) or not os.access(db_path, os.R_OK):
            return []
        
        out = []
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA cache_size = 10000")
            cursor.execute("PRAGMA page_size = 4096")
            cursor.execute("PRAGMA mmap_size = 30000000000")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'android_%'")
            tables = cursor.fetchall()
            
            skip_tables = ['android_metadata', 'db_config', 'meta', 'crawl_state', 'sqlite_sequence']
            
            for table in tables:
                table_name = table[0]
                if table_name in skip_tables:
                    continue
                items = self.parse_table(cursor, conn, table_name, limit)
                if items:
                    out.extend(items)
                if len(out) >= limit:
                    out = out[:limit]
                    break
            
            conn.close()
        except Exception as e:
            print(f"数据库读取错误: {e}")
            return []
        
        self.cache[cache_key] = out
        self.cache_time[cache_key] = current_time
        return out
    
    def parse_table(self, cursor, conn, table, limit):
        res = []
        try:
            cursor.execute(f"PRAGMA table_info(`{table}`)")
            cols = cursor.fetchall()
            col_names = [col[1] for col in cols]
            
            title_field = self.find_best_match(col_names, ['vod_name', 'name', 'title'])
            url_field = self.find_best_match(col_names, ['play_url', 'vod_play_url', 'vod_url', 'url'])
            pic_field = self.find_best_match(col_names, ['image', 'vod_pic', 'pic'])
            remarks_field = self.find_best_match(col_names, ['vod_remarks', 'remarks'])
            
            if not title_field or not url_field:
                return []
            
            cursor.execute(f"SELECT * FROM `{table}` WHERE `{url_field}` IS NOT NULL AND `{url_field}` != ''")
            rows = cursor.fetchall()
            
            for row in rows:
                row_dict = dict(row)
                play_url_raw = str(row_dict.get(url_field, '')).strip()
                if not play_url_raw:
                    continue
                
                title = str(row_dict.get(title_field, '未命名')).strip()
                
                is_multi = '$' in play_url_raw or '#' in play_url_raw or '$$$' in play_url_raw
                
                item = {
                    'name': title,
                    'url': '' if is_multi else play_url_raw,
                    'play_url': play_url_raw if is_multi else '',
                    'pic': row_dict.get(pic_field, '') if pic_field else '',
                    'remarks': row_dict.get(remarks_field, '') if remarks_field else '',
                }
                res.append(item)
        except Exception as e:
            print(f"解析表 {table} 错误: {e}")
        return res
    
    def find_best_match(self, column_names, candidates):
        for cand in candidates:
            for col in column_names:
                if col.lower() == cand.lower():
                    return col
        for cand in candidates:
            for col in column_names:
                if cand.lower() in col.lower():
                    return col
        return None

class Spider(Spider):
    def getName(self):
        return "本地资源管理"
    
    def init(self, extend=""):
        super().init(extend)
        self.root_paths = ROOT_PATHS
        self.path_to_chinese = PATH_TO_CHINESE
        
        # 在线直播配置
        self.online_live_sources = ONLINE_LIVE_SOURCES
        self.live_category_id = LIVE_CATEGORY_ID
        self.live_category_name = LIVE_CATEGORY_NAME
        self.live_cache = {}
        self.live_cache_time = {}
        self.live_cache_duration = LIVE_CACHE_DURATION
        
        # 请求头适配
        self.common_headers_list = COMMON_HEADERS_LIST
        self.domain_specific_headers = DOMAIN_SPECIFIC_HEADERS
        self.successful_headers_cache = {}
        
        self.default_colors = [
            "#FF6B6B", "#4ECDC4", "#FFD93D", "#6BCB77", "#9D65C9", 
            "#FF8C42", "#A2D729", "#FF6B8B", "#45B7D1", "#96CEB4"
        ]
        
        # 文件类型定义
        self.media_exts = ['mp4', 'mkv', 'avi', 'rmvb', 'mov', 'wmv', 'flv', 'm4v', 'ts', 'm3u8']
        self.audio_exts = ['mp3', 'm4a', 'aac', 'flac', 'wav', 'ogg', 'wma', 'ape']
        self.image_exts = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'ico', 'svg']
        self.list_exts = ['m3u', 'txt', 'json', 'm3u8']
        self.lrc_exts = ['lrc']
        self.db_exts = ['db', 'sqlite', 'sqlite3', 'db3']
        self.magnet_exts = ['magnets', 'magnet', 'bt', 'torrent', 'mgt']
        
        self.file_icons = {
            'folder': 'https://img.icons8.com/color/96/000000/folder-invoices.png',
            'video': 'https://img.icons8.com/color/96/000000/video.png',
            'video_playlist': 'https://img.icons8.com/color/96/000000/playlist.png',
            'audio': 'https://img.icons8.com/color/96/000000/audio-file.png',
            'audio_playlist': 'https://img.icons8.com/color/96/000000/musical-notes.png',
            'image': 'https://img.icons8.com/color/96/000000/image.png',
            'image_playlist': 'https://img.icons8.com/color/96/000000/image-gallery.png',
            'list': 'https://img.icons8.com/color/96/000000/list.png',
            'lrc': 'https://img.icons8.com/color/96/000000/lyrics.png',
            'database': 'https://img.icons8.com/color/96/000000/database.png',
            'magnet': 'https://img.icons8.com/color/96/000000/magnet.png',
            'file': 'https://img.icons8.com/color/96/000000/file.png'
        }
        
        self.TRANSPARENT_GIF = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
        
        # 前缀常量
        self.V_DIR_PREFIX = 'vdir://'
        self.V_ITEM_PREFIX = 'vitem://'
        self.URL_B64U_PREFIX = 'b64u://'
        self.V_ALL_PREFIX = 'vall://'
        self.A_ALL_PREFIX = 'aall://'
        self.FOLDER_PREFIX = 'folder://'
        self.LIST_PREFIX = 'list://'
        self.PICS_PREFIX = 'pics://'
        self.CAMERA_ALL_PREFIX = 'camall://'
        self.MAGNET_PREFIX = 'magnet://'
        self.LIVE_PREFIX = 'live://'

        self.lrc_cache = {}
        self.m3u8_cache = {}
        self.db_reader = DatabaseReader()
        
        # 新增：海报缓存
        self.poster_cache = {}
        
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self.debug_mode = True

    def log(self, msg):
        if self.debug_mode:
            print(f"🔍 [DEBUG] {msg}")

    # ==================== 请求头自动适配函数 ====================
    
    def _get_domain_from_url(self, url):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if ':' in domain:
                domain = domain.split(':')[0]
            return domain
        except:
            return ""
    
    def _try_headers_for_url(self, url, headers_list, source_name=""):
        domain = self._get_domain_from_url(url)
        
        if domain in self.successful_headers_cache:
            cached_headers = self.successful_headers_cache[domain]
            self.log(f"📦 使用缓存的请求头 ({domain}): {cached_headers.get('name', '未知')}")
            try:
                resp = self.session.get(url, headers=cached_headers['headers'], timeout=15)
                if resp.status_code == 200:
                    return resp.text, cached_headers
                else:
                    self.log(f"⚠️ 缓存请求头失效，状态码: {resp.status_code}")
            except:
                self.log(f"⚠️ 缓存请求头请求失败")
        
        for headers_info in headers_list:
            headers_name = headers_info['name']
            headers = headers_info['headers']
            
            self.log(f"🔄 尝试请求头 [{headers_name}] {source_name}")
            try:
                resp = self.session.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    content = resp.text
                    content_length = len(content)
                    self.log(f"✅ 请求头 [{headers_name}] 成功！内容长度: {content_length}")
                    
                    if domain:
                        self.successful_headers_cache[domain] = headers_info
                    
                    return content, headers_info
                else:
                    self.log(f"❌ 请求头 [{headers_name}] 失败，状态码: {resp.status_code}")
            except Exception as e:
                self.log(f"❌ 请求头 [{headers_name}] 异常: {e}")
        
        return None, None
    
    def _fetch_with_auto_headers(self, url):
        domain = self._get_domain_from_url(url)
        self.log(f"🌐 域名: {domain}")
        
        if domain in self.domain_specific_headers:
            self.log(f"🔍 找到域名 [{domain}] 的专用请求头")
            content, headers_info = self._try_headers_for_url(
                url, 
                self.domain_specific_headers[domain],
                f"({domain}专用)"
            )
            if content:
                return content
        
        self.log(f"🔍 尝试通用请求头列表")
        content, headers_info = self._try_headers_for_url(
            url, 
            self.common_headers_list,
            "(通用)"
        )
        if content:
            return content
        
        self.log(f"❌ 所有请求头都尝试失败")
        return None
    
    def _fetch_content_with_ua(self, url, ua=None):
        """通用获取方法，支持自定义 UA"""
        headers = self.common_headers_list[0]['headers'].copy()
        if ua:
            headers["User-Agent"] = ua
            self.log(f"使用自定义 UA: {ua}")
        
        domain = self._get_domain_from_url(url)
        if domain in self.domain_specific_headers:
            headers.update(self.domain_specific_headers[domain][0]['headers'])

        try:
            resp = self.session.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                self.log(f"✅ 成功获取内容，长度: {len(resp.text)}")
                return resp.text
            else:
                self.log(f"❌ 获取失败，状态码: {resp.status_code}")
                return None
        except Exception as e:
            self.log(f"❌ 请求异常: {e}")
            return None
    
    # ==================== 在线直播相关函数 ====================
    
    def _get_source_color(self, index):
        if index < len(self.online_live_sources):
            source = self.online_live_sources[index]
            if 'color' in source:
                return source['color']
        return self.default_colors[index % len(self.default_colors)]
    
    def _generate_colored_icon(self, color, text="直"):
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <rect width="200" height="200" rx="40" ry="40" fill="{color}"/>
            <text x="100" y="140" font-size="120" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-weight="bold">{text}</text>
        </svg>'''
        svg_base64 = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
        return f"data:image/svg+xml;base64,{svg_base64}"
    
    def _fetch_m3u_content(self, url, source=None):
        try:
            self.log(f"正在获取直播源: {url}")
            
            # 如果有自定义UA，先尝试使用
            if source and 'ua' in source:
                headers = {
                    "User-Agent": source['ua'],
                    "Accept": "*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Connection": "keep-alive"
                }
                # 根据域名添加Referer
                if 'miguvideo.com' in url:
                    headers["Referer"] = "https://www.miguvideo.com/"
                elif 'gongdian.top' in url:
                    headers["Referer"] = "https://gongdian.top/"
                
                headers = {k: v for k, v in headers.items() if v is not None}
                self.log(f"使用自定义 UA: {source['ua']}")
                try:
                    resp = self.session.get(url, headers=headers, timeout=15)
                    if resp.status_code == 200:
                        content = resp.text
                        self.log(f"✅ 自定义UA获取成功，长度: {len(content)}")
                        return content
                    else:
                        self.log(f"⚠️ 自定义UA获取失败，状态码: {resp.status_code}")
                except Exception as e:
                    self.log(f"⚠️ 自定义UA请求异常: {e}")
            
            # 失败则尝试自动适配
            content = self._fetch_with_auto_headers(url)
            if content:
                return content
            
            return None
        except Exception as e:
            self.log(f"❌ 网络请求异常: {e}")
            return None
    
    def _parse_m3u_content(self, content):
        """
        解析M3U格式，提取所有节目
        返回节目列表 [{"name": "节目名", "url": "播放地址"}, ...]
        """
        programs = []
        
        lines = content.split('\n')
        current_name = None
        current_tvg_id = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            
            if not line:
                continue
            
            if line.startswith('#EXTINF:'):
                tvg_match = re.search(r'tvg-id="([^"]*)"', line)
                if tvg_match:
                    current_tvg_id = tvg_match.group(1).strip()
                
                name_match = re.search(r'tvg-name="([^"]+)"', line)
                if name_match:
                    current_name = name_match.group(1).strip()
                else:
                    parts = line.split(',')
                    if len(parts) > 1:
                        current_name = parts[-1].strip()
                    else:
                        current_name = "未知节目"
                
                if i < len(lines):
                    next_line = lines[i].strip()
                    if next_line and not next_line.startswith('#'):
                        url = next_line
                        i += 1
                        
                        # 检查URL中是否包含多个节目
                        if '$' in url or '#' in url:
                            self.log(f"📑 检测到多节目源: {current_name}")
                            episodes = self._parse_multi_episodes(url, current_name)
                            for ep in episodes:
                                programs.append({
                                    'name': ep['name'],
                                    'url': ep['url'],
                                    'tvg_id': current_tvg_id
                                })
                                self.log(f"  ✅ 添加子节目: {ep['name']}")
                        else:
                            programs.append({
                                'name': current_name,
                                'url': url,
                                'tvg_id': current_tvg_id
                            })
                            self.log(f"✅ 添加节目: {current_name}")
                        
                        current_name = None
        
        self.log(f"📊 解析完成，共 {len(programs)} 个节目")
        return programs
    
    def _parse_txt_content(self, content):
        """
        解析TXT格式（支持#genre#分类）
        返回节目列表 [{"name": "节目名", "url": "播放地址"}, ...]
        """
        programs = []
        
        lines = content.split('\n')
        current_cat = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ',#genre#' in line:
                current_cat = line.split(',')[0].strip()
                self.log(f"📑 检测到分类: {current_cat}")
                continue
            
            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()
                
                if url and self.is_playable_url(url):
                    if current_cat:
                        # 将分类信息添加到节目名中，格式为 [分类] 节目名
                        display_name = f"[{current_cat}] {name}"
                    else:
                        display_name = name
                    
                    programs.append({
                        'name': display_name,
                        'url': url
                    })
                    self.log(f"✅ 添加节目: {display_name}")
        
        self.log(f"📊 解析完成，共 {len(programs)} 个节目")
        return programs
    
    def _parse_simple_txt(self, content):
        """
        简单的TXT解析器，直接按行解析
        格式：名称,URL 或 名称 URL
        """
        programs = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 跳过可能的注释行
            if '#genre#' in line.lower():
                continue
            
            # 尝试多种分隔符
            name = None
            url = None
            
            # 尝试逗号分隔
            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()
            # 尝试空格分隔
            elif ' ' in line and not line.startswith('http'):
                parts = line.split(' ', 1)
                if len(parts) == 2 and not parts[1].startswith('http'):
                    # 如果第二部分不是URL，可能格式不对
                    pass
                else:
                    name = parts[0].strip()
                    url = parts[1].strip()
            # 尝试制表符分隔
            elif '\t' in line:
                parts = line.split('\t', 1)
                name = parts[0].strip()
                url = parts[1].strip()
            
            # 如果解析出URL，验证是否可播放
            if url and self.is_playable_url(url):
                if not name:
                    name = f"频道{len(programs)+1}"
                programs.append({
                    'name': name,
                    'url': url
                })
                self.log(f"✅ 简单解析添加: {name}")
            elif url:
                self.log(f"⚠️ 跳过不可播放URL: {url[:50]}...")
        
        self.log(f"简单解析完成，共 {len(programs)} 个节目")
        return programs
    
    def _parse_multi_episodes(self, url, channel_name):
        """解析多节目源的多个节目"""
        episodes = []
        
        if '$' in url:
            parts = url.split('#')
            for part in parts:
                if '$' in part:
                    ep_name, ep_url = part.split('$', 1)
                    episodes.append({
                        'name': ep_name.strip(),
                        'url': ep_url.strip()
                    })
                else:
                    episodes.append({
                        'name': f"{channel_name} - 节目{len(episodes)+1}",
                        'url': part
                    })
        else:
            episodes.append({
                'name': channel_name,
                'url': url
            })
        
        return episodes
    
    def _parse_json_content(self, content):
        """解析JSON格式的直播源"""
        programs = []
        try:
            data = json.loads(content)
            
            if isinstance(data, dict):
                # 检查常见的顶层键
                possible_keys = ['list', 'vod', 'videos', 'data', 'items', 'results', 
                                'rows', 'datas', 'data_list', 'video_list', 'movie_list']
                
                item_list = []
                for key in possible_keys:
                    if key in data and isinstance(data[key], list):
                        item_list = data[key]
                        self.log(f"找到顶层键: {key}, 项目数: {len(item_list)}")
                        break
                
                if not item_list and all(isinstance(v, dict) for v in data.values()):
                    item_list = list(data.values())
                    self.log(f"使用字典值作为列表，项目数: {len(item_list)}")
                elif not item_list:
                    item_list = [data]
                    self.log("将整个字典作为单个项目处理")
            elif isinstance(data, list):
                item_list = data
                self.log(f"直接使用数组，项目数: {len(item_list)}")
            else:
                return programs
            
            for item in item_list:
                if not isinstance(item, dict):
                    if isinstance(item, str) and self.is_playable_url(item):
                        programs.append({
                            'name': f'链接{len(programs)+1}',
                            'url': item
                        })
                    continue
                
                # 提取名称
                name = None
                name_fields = ['name', 'title', 'vod_name', 'video_name', 'show_name']
                for field in name_fields:
                    if field in item and item[field]:
                        name = str(item[field]).strip()
                        break
                
                if not name:
                    continue
                
                # 提取URL
                url = ''
                play_url = ''
                
                if 'play_url' in item and item['play_url']:
                    play_url = str(item['play_url']).strip()
                elif 'vod_play_url' in item and item['vod_play_url']:
                    play_url = str(item['vod_play_url']).strip()
                
                if not play_url:
                    url_fields = ['url', 'link', 'video_url', 'vod_url', 'src']
                    for field in url_fields:
                        if field in item and item[field]:
                            url = str(item[field]).strip()
                            break
                
                if not play_url and not url:
                    continue
                
                final_url = play_url if play_url else url
                
                # 检查是否是多节目
                if '$' in final_url or '#' in final_url:
                    episodes = self._parse_multi_episodes(final_url, name)
                    for ep in episodes:
                        programs.append({
                            'name': ep['name'],
                            'url': ep['url']
                        })
                else:
                    programs.append({
                        'name': name,
                        'url': final_url
                    })
            
        except Exception as e:
            self.log(f"JSON解析错误: {e}")
        
        self.log(f"JSON解析完成，共 {len(programs)} 个节目")
        return programs
    
    def _get_live_programs(self, source):
        source_id = source['id']
        current_time = time.time()
        
        if source_id in self.live_cache and current_time - self.live_cache_time.get(source_id, 0) < self.live_cache_duration:
            self.log(f"📦 使用缓存的直播源: {source['name']}, {len(self.live_cache[source_id])} 个节目")
            return self.live_cache[source_id]
        
        url = source['url']
        
        self.log(f"🔍 正在获取直播源: {source['name']} - {url}")
        
        # 通用获取逻辑
        content = self._fetch_m3u_content(url, source)
        
        if content:
            self.log(f"✅ 成功获取内容，长度: {len(content)}")
            
            programs = []
            
            # 根据内容格式和类型选择解析器
            if source.get('type') == 'txt':
                self.log("📄 使用TXT解析器")
                programs = self._parse_txt_content(content)
                if not programs:
                    self.log("⚠️ TXT解析器失败，尝试简单解析器")
                    programs = self._parse_simple_txt(content)
            elif content.strip().startswith('{') or content.strip().startswith('['):
                self.log("📄 检测到JSON格式，使用JSON解析器")
                programs = self._parse_json_content(content)
            else:
                self.log("📄 使用M3U解析器")
                programs = self._parse_m3u_content(content)
                if not programs:
                    self.log("⚠️ M3U解析器失败，尝试简单解析器")
                    programs = self._parse_simple_txt(content)
            
            self.log(f"📊 解析到 {len(programs)} 个节目")
            
            if programs:
                self.live_cache[source_id] = programs
                self.live_cache_time[source_id] = current_time
                return programs
            else:
                self.log(f"⚠️ 解析到0个节目，内容预览: {content[:200]}")
        else:
            self.log(f"❌ 无法获取内容")
        
        return []
    
    def _live_category_content(self, pg):
        vlist = []
        
        for index, source in enumerate(self.online_live_sources):
            self.log(f"正在处理源: {source['name']}")
            
            programs = self._get_live_programs(source)
            program_count = len(programs) if programs else 0
            
            color = self._get_source_color(index)
            first_char = source['name'][0] if source['name'] else "直"
            icon_url = self._generate_colored_icon(color, first_char)
            
            vod_id = self.LIVE_PREFIX + self.b64u_encode(source['id'])
            
            remarks = source.get('remarks', '')
            if program_count > 0:
                remarks += f" {program_count}个节目"
            else:
                remarks += " 加载失败"
            
            vlist.append({
                'vod_id': vod_id,
                'vod_name': source['name'],
                'vod_pic': icon_url,
                'vod_remarks': remarks,
                'vod_tag': 'live_source',
                'style': {'type': 'list'}
            })
        
        self.log(f"最终列表项数量: {len(vlist)}")
        
        return {
            'list': vlist,
            'page': pg,
            'pagecount': 1,
            'limit': len(vlist),
            'total': len(vlist)
        }
    
    def _live_source_detail(self, source_id):
        source = None
        source_index = -1
        for i, s in enumerate(self.online_live_sources):
            if s['id'] == source_id:
                source = s
                source_index = i
                break
        
        if not source:
            self.log(f"❌ 未找到直播源: {source_id}")
            return {'list': []}
        
        color = self._get_source_color(source_index)
        first_char = source['name'][0] if source['name'] else "直"
        icon_url = self._generate_colored_icon(color, first_char)
        
        # 获取所有节目
        all_programs = self._get_live_programs(source)
        if not all_programs:
            return {'list': [{
                'vod_id': self.LIVE_PREFIX + self.b64u_encode(source_id),
                'vod_name': source['name'],
                'vod_pic': icon_url,
                'vod_play_from': '直播源',
                'vod_play_url': f"提示$无法获取直播源，请稍后重试",
                'vod_content': f"直播源: {source['url']}\n状态: 获取失败",
                'style': {'type': 'list'}
            }]}
        
        # ===== 按电视台名称合并相同电视台的不同线路 =====
        channels = {}  # {电视台名: [线路列表]}
        
        for program in all_programs:
            name = program['name']
            url = program['url']
            
            # 清理名称，移除可能的分组标记
            clean_name = re.sub(r'^\[[^\]]+\]\s*', '', name)
            clean_name = re.sub(r'\s*[\[\(（]\s*\d+\s*[\]\)）]\s*$', '', clean_name)  # 移除末尾的 [数字]
            
            if clean_name not in channels:
                channels[clean_name] = []
            
            # 保存线路信息，包含原始名称和URL
            channels[clean_name].append({
                'name': name,
                'url': url
            })
        
        self.log(f"按电视台合并完成，共 {len(channels)} 个电视台")
        
        # ===== 构建选集和线路 =====
        from_list = []  # 选集：电视台名称列表
        url_list = []   # 线路：每个电视台的线路串
        
        for channel_name, links in channels.items():
            if not links:
                continue
                
            # 选集：添加电视台名称
            from_list.append(channel_name)
            
            # 线路：构建该电视台的所有线路
            if len(links) > 1:
                # 多个线路：线路1$url1#线路2$url2#线路3$url3
                link_parts = []
                for i, link in enumerate(links, 1):
                    link_parts.append(f"线路{i}${link['url']}")
                channel_playlist = '#'.join(link_parts)
                self.log(f"📺 添加多线路电视台 [{channel_name}] 共 {len(links)} 条线路")
            else:
                # 单个线路：电视台名$url
                channel_playlist = f"{channel_name}${links[0]['url']}"
                self.log(f"📺 添加单线路电视台 [{channel_name}]")
            
            url_list.append(channel_playlist)
        
        # 计算总电视台数和总线路数
        total_channels = len(channels)
        total_links = sum(len(links) for links in channels.values())
        
        # 构建 vod_play_from 和 vod_play_url
        # vod_play_from: 线路组名称，用$$$分隔（这里每个电视台作为一个线路组）
        # vod_play_url: 播放串，用$$$分隔每组，每组内用#分隔剧集，剧集名和URL用$分隔
        vod_play_from = "$$$".join(from_list)  # 每个电视台作为一个线路组
        vod_play_url = "$$$".join(url_list)    # 每个电视台的所有线路
        
        vod_obj = {
            'vod_id': self.LIVE_PREFIX + self.b64u_encode(source_id),
            'vod_name': source['name'],
            'vod_pic': icon_url,
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url,
            'vod_content': f"共 {total_channels} 个电视台，{total_links} 条线路\n最后更新: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        if 'playerType' in source:
            vod_obj['playerType'] = source['playerType']
        
        self.log(f"✅ 构建完成: {total_channels} 个电视台，{total_links} 条线路")
        self.log(f"📋 选集示例: {from_list[:3]}...")
        self.log(f"🔗 线路示例: {url_list[:3]}...")
        
        return {'list': [vod_obj]}
    
    # ==================== 工具函数 ====================
    
    def b64u_encode(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        encoded = base64.b64encode(data).decode('ascii')
        return encoded.replace('+', '-').replace('/', '_').rstrip('=')
    
    def b64u_decode(self, data):
        data = data.replace('-', '+').replace('_', '/')
        pad = len(data) % 4
        if pad:
            data += '=' * (4 - pad)
        try:
            return base64.b64decode(data).decode('utf-8')
        except:
            return ''
    
    def get_file_ext(self, filename):
        idx = filename.rfind('.')
        if idx == -1:
            return ''
        return filename[idx + 1:].lower()
    
    def is_media_file(self, ext):
        return ext in self.media_exts
    
    def is_audio_file(self, ext):
        return ext in self.audio_exts
    
    def is_image_file(self, ext):
        return ext in self.image_exts
    
    def is_list_file(self, ext):
        return ext in self.list_exts
    
    def is_lrc_file(self, ext):
        return ext in self.lrc_exts
    
    def is_db_file(self, ext):
        return ext in self.db_exts
    
    def is_magnet_file(self, ext):
        return ext in self.magnet_exts
    
    def scan_directory(self, dir_path):
        try:
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return []
            
            files = []
            for name in os.listdir(dir_path):
                if name.startswith('.') or name in ['.', '..']:
                    continue
                
                full_path = os.path.join(dir_path, name)
                is_dir = os.path.isdir(full_path)
                ext = self.get_file_ext(name)
                
                files.append({
                    'name': name,
                    'path': full_path,
                    'is_dir': is_dir,
                    'ext': ext,
                    'mtime': os.path.getmtime(full_path) if not is_dir else 0,
                })
            
            files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            return files
        except:
            return []
    
    def collect_videos_in_dir(self, dir_path):
        files = self.scan_directory(dir_path)
        videos = []
        for f in files:
            if not f['is_dir'] and self.is_media_file(f['ext']):
                videos.append(f)
        videos.sort(key=lambda x: x['name'].lower())
        return videos
    
    def collect_audios_in_dir(self, dir_path):
        files = self.scan_directory(dir_path)
        audios = []
        for f in files:
            if not f['is_dir'] and self.is_audio_file(f['ext']):
                audios.append(f)
        audios.sort(key=lambda x: x['name'].lower())
        return audios
    
    def collect_images_in_dir(self, dir_path):
        files = self.scan_directory(dir_path)
        images = []
        for f in files:
            if not f['is_dir'] and self.is_image_file(f['ext']):
                images.append(f)
        images.sort(key=lambda x: x['name'].lower())
        return images
    
    def collect_lrc_in_dir(self, dir_path):
        """收集目录内的所有歌词文件"""
        files = self.scan_directory(dir_path)
        lrcs = []
        for f in files:
            if not f['is_dir'] and self.is_lrc_file(f['ext']):
                lrcs.append(f)
        return lrcs
    
    def collect_dbs_in_dir(self, dir_path):
        files = self.scan_directory(dir_path)
        dbs = []
        for f in files:
            if not f['is_dir'] and self.is_db_file(f['ext']):
                dbs.append(f)
        dbs.sort(key=lambda x: x['name'].lower())
        return dbs
    
    def collect_magnets_in_dir(self, dir_path):
        files = self.scan_directory(dir_path)
        magnets = []
        for f in files:
            if not f['is_dir'] and self.is_magnet_file(f['ext']):
                magnets.append(f)
        magnets.sort(key=lambda x: x['name'].lower())
        return magnets
    
    # ==================== 列表文件解析 ====================
    
    def parse_m3u_file(self, file_path):
        items = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            current_title = ''
            idx = 1
            line_count = 0
            
            for line in lines:
                line_count += 1
                if line_count > 50000:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('#EXTINF:'):
                    title_match = re.search(r',(.+)$', line)
                    if title_match:
                        current_title = title_match.group(1).strip()
                    else:
                        tvg_match = re.search(r'tvg-name="([^"]+)"', line, re.I)
                        if tvg_match:
                            current_title = tvg_match.group(1).strip()
                        else:
                            current_title = f'线路{idx}'
                    continue
                
                if line.startswith('#'):
                    continue
                
                if self.is_playable_url(line):
                    items.append({
                        'name': current_title if current_title else f'线路{idx}',
                        'url': line
                    })
                    current_title = ''
                    idx += 1
        except Exception as e:
            print(f"解析M3U文件错误: {e}")
        return items
    
    def parse_txt_file(self, file_path):
        items = []
        
        PROTO_M = b'://'
        GENRE_M = b',#genre#'
        COMMA = b','
        BLACK_FINGERPRINTS = [b'serv00', b'termux', b'192.168.', b'static IP', b'aa.json']
        
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(2048)
                
                is_blacklisted = any(tag in sample for tag in BLACK_FINGERPRINTS)
                if is_blacklisted:
                    self.log(f"⛔ 文件包含黑名单关键词，已过滤: {os.path.basename(file_path)}")
                    return []
                
                has_proto = (PROTO_M in sample and COMMA in sample)
                has_genre = GENRE_M in sample
                
                if not (has_proto or has_genre):
                    f.seek(0)
                    more_sample = f.read(1024 * 10)
                    has_proto = (PROTO_M in more_sample and COMMA in more_sample)
                    has_genre = GENRE_M in more_sample
                    
                    if not (has_proto or has_genre):
                        self.log(f"⚠️ 文件不符合直播源格式，跳过: {os.path.basename(file_path)}")
                        return []
            
            encodings_to_try = ['utf-8', 'gb18030', 'gbk', 'gb2312', 'big5', 'utf-16']
            detected_encoding = 'utf-8'
            
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)
                for enc in encodings_to_try:
                    try:
                        raw_data.decode(enc)
                        detected_encoding = enc
                        self.log(f"✅ 检测到文件编码: {enc}")
                        break
                    except:
                        continue
            
            with open(file_path, 'r', encoding=detected_encoding, errors='ignore') as f:
                max_lines = 50000
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        self.log(f"⚠️ 文件过大，只读取前{max_lines}行: {os.path.basename(file_path)}")
                        break
                    lines.append(line)
            
            has_genre = any(",#genre#" in line for line in lines)
            
            if has_genre:
                self.log(f"📑 检测到#genre#格式: {os.path.basename(file_path)}")
                current_cat = None
                current_lines = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if ",#genre#" in line:
                        if current_cat is not None and current_lines:
                            for item_line in current_lines:
                                if ',' in item_line:
                                    parts = item_line.split(',', 1)
                                    if len(parts) == 2:
                                        name, url = parts[0].strip(), parts[1].strip()
                                        if url and self.is_playable_url(url):
                                            items.append({
                                                'name': f"[{current_cat}] {name}",
                                                'url': url
                                            })
                        current_cat = line.split(",", 1)[0].strip()
                        current_lines = []
                    elif current_cat is not None and line and ',' in line:
                        current_lines.append(line)
                
                if current_cat is not None and current_lines:
                    for item_line in current_lines:
                        if ',' in item_line:
                            parts = item_line.split(',', 1)
                            if len(parts) == 2:
                                name, url = parts[0].strip(), parts[1].strip()
                                if url and self.is_playable_url(url):
                                    items.append({
                                        'name': f"[{current_cat}] {name}",
                                        'url': url
                                    })
            else:
                self.log(f"📄 检测到普通TXT格式: {os.path.basename(file_path)}")
                valid_count = 0
                
                for line in lines:
                    line = line.strip()
                    
                    if not line or line.startswith('#') or '#genre#' in line.lower():
                        continue
                    
                    name = ''
                    url = ''
                    
                    if ',' in line:
                        pos = line.find(',')
                        name = line[:pos].strip()
                        url = line[pos+1:].strip()
                    else:
                        url = line
                        name = f"频道{valid_count+1}"
                    
                    if url and self.is_playable_url(url):
                        items.append({
                            'name': name if name else f"频道{valid_count+1}",
                            'url': url
                        })
                        valid_count += 1
                    
                    if valid_count >= 5000:
                        self.log(f"⚠️ 达到最大解析条数限制(5000)，停止解析")
                        break
            
            seen_urls = set()
            unique_items = []
            for item in items:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_items.append(item)
            
            self.log(f"✅ TXT文件解析完成: {os.path.basename(file_path)}, 共 {len(unique_items)} 条有效记录")
            return unique_items
            
        except Exception as e:
            print(f"❌ 解析TXT文件错误: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def parse_json_file(self, file_path):
        items = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(30 * 1024 * 1024)
            
            data = json.loads(content)
            
            if isinstance(data, dict):
                possible_keys = ['list', 'vod', 'videos', 'data', 'items', 'results', 
                                'rows', 'datas', 'data_list', 'video_list', 'movie_list']
                
                item_list = []
                for key in possible_keys:
                    if key in data and isinstance(data[key], list):
                        item_list = data[key]
                        self.log(f"找到顶层键: {key}, 项目数: {len(item_list)}")
                        break
                
                if not item_list and all(isinstance(v, dict) for v in data.values()):
                    item_list = list(data.values())
                    self.log(f"使用字典值作为列表，项目数: {len(item_list)}")
                elif not item_list:
                    item_list = [data]
                    self.log("将整个字典作为单个项目处理")
            elif isinstance(data, list):
                item_list = data
                self.log(f"直接使用数组，项目数: {len(item_list)}")
            else:
                return items
            
            for item in item_list:
                if not isinstance(item, dict):
                    if isinstance(item, str) and self.is_playable_url(item):
                        items.append({
                            'name': f'链接{len(items)+1}',
                            'url': item
                        })
                    continue
                
                name = None
                name_fields = ['name', 'title', 'vod_name', 'video_name', 'show_name']
                for field in name_fields:
                    if field in item and item[field]:
                        name = str(item[field]).strip()
                        break
                
                if not name:
                    continue
                
                url = ''
                play_url = ''
                
                if 'play_url' in item and item['play_url']:
                    play_url = str(item['play_url']).strip()
                elif 'vod_play_url' in item and item['vod_play_url']:
                    play_url = str(item['vod_play_url']).strip()
                
                if not play_url:
                    url_fields = ['url', 'link', 'video_url', 'vod_url', 'src']
                    for field in url_fields:
                        if field in item and item[field]:
                            url = str(item[field]).strip()
                            break
                
                if not play_url and not url:
                    continue
                
                final_url = play_url if play_url else url
                
                pic = ''
                pic_fields = ['pic', 'cover', 'image', 'thumbnail', 'poster', 'vod_pic', 'img']
                for field in pic_fields:
                    if field in item and item[field]:
                        pic = str(item[field])
                        if isinstance(item[field], dict):
                            if 'url' in item[field]:
                                pic = str(item[field]['url'])
                            elif 'large' in item[field]:
                                pic = str(item[field]['large'])
                        break
                
                remarks = ''
                remark_fields = ['remarks', 'remark', 'note', 'vod_remarks', 'type', 'category', 'class', 'desc']
                for field in remark_fields:
                    if field in item and item[field]:
                        remarks = str(item[field])
                        break
                
                items.append({
                    'name': name,
                    'url': final_url,
                    'pic': pic,
                    'remarks': remarks
                })
            
        except Exception as e:
            print(f"解析JSON文件错误: {e}")
            import traceback
            traceback.print_exc()
        
        self.log(f"JSON文件解析完成: {os.path.basename(file_path)}, 共 {len(items)} 条记录")
        return items
    
    def parse_db_file(self, file_path):
        return self.db_reader.read_sqlite(file_path, MAX_DB_RESULTS)
    
    def parse_magnet_file(self, file_path):
        items = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            line_count = 0
            magnet_pattern = re.compile(r'(magnet:\?[^\s\'"<>]+)', re.I)
            
            for line in lines:
                line_count += 1
                if line_count > 50000:
                    break
                
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ',' in line:
                    parts = line.split(',', 1)
                    name = parts[0].strip()
                    url_part = parts[1].strip()
                    
                    magnet_match = magnet_pattern.search(url_part)
                    if magnet_match:
                        url = magnet_match.group(1)
                        if not name:
                            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', url)
                            if hash_match:
                                name = f"磁力 {hash_match.group(1)[:8]}..."
                            else:
                                name = f"磁力链接{len(items)+1}"
                        items.append({
                            'name': name,
                            'url': url,
                            'remarks': '磁力链接'
                        })
                        continue
                
                if ' ' in line:
                    magnet_match = magnet_pattern.search(line)
                    if magnet_match:
                        url = magnet_match.group(1)
                        name_part = line[:magnet_match.start()].strip()
                        if name_part and not name_part.startswith('magnet:'):
                            name = name_part
                        else:
                            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', url)
                            if hash_match:
                                name = f"磁力 {hash_match.group(1)[:8]}..."
                            else:
                                name = f"磁力链接{len(items)+1}"
                        
                        items.append({
                            'name': name,
                            'url': url,
                            'remarks': '磁力链接'
                        })
                        continue
                
                magnet_match = magnet_pattern.search(line)
                if magnet_match:
                    url = magnet_match.group(1)
                    hash_match = re.search(r'btih:([a-fA-F0-9]{40})', url)
                    if hash_match:
                        name = f"磁力 {hash_match.group(1)[:8]}..."
                    else:
                        name = f"磁力链接{len(items)+1}"
                    
                    items.append({
                        'name': name,
                        'url': url,
                        'remarks': '磁力链接'
                    })
                    continue
                
                if line.startswith('magnet:'):
                    items.append({
                        'name': f"磁力链接{len(items)+1}",
                        'url': line,
                        'remarks': '磁力链接'
                    })
                    continue
            
            seen_urls = set()
            unique_items = []
            for item in items:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_items.append(item)
            
            print(f"✅ 磁力链接文件解析完成: {os.path.basename(file_path)}, 共 {len(unique_items)} 条有效链接")
            return unique_items
            
        except Exception as e:
            print(f"解析磁力链接文件错误: {e}")
            return []
    
    def is_playable_url(self, url):
        u = str(url).lower().strip()
        if not u:
            return False
        
        protocols = [
            'http://', 'https://', 'rtmp://', 'rtsp://', 'udp://', 'rtp://', 
            'file://', 'pics://', 'magnet:', 'ed2k://', 'thunder://', 'ftp://',
            'vod://', 'bilibili://', 'youtube://',
            'rtmps://', 'rtmpt://', 'hls://', 'http-live://', 'https-live://',
            'tvbus://', 'tvbox://', 'live://'
        ]
        for p in protocols:
            if u.startswith(p):
                return True
        
        exts = [
            '.mp4', '.mkv', '.avi', '.rmvb', '.mov', '.wmv', '.flv', 
            '.m3u8', '.ts', '.mp3', '.m4a', '.aac', '.flac', '.wav', 
            '.webm', '.ogg', '.m4v', '.f4v', '.3gp', '.mpg', '.mpeg',
            '.m3u', '.pls', '.asf', '.asx', '.wmx'
        ]
        for e in exts:
            if e in u:
                return True
        
        patterns = [
            'youtu.be/', 'youtube.com/', 'bilibili.com/', 'iqiyi.com/', 
            'v.qq.com/', 'youku.com/', 'tudou.com/', 'mgtv.com/',
            'sohu.com/', 'acfun.cn/', 'douyin.com/', 'kuaishou.com/',
            'huya.com/', 'douyu.com/', 'twitch.tv/', 'live.'
        ]
        for p in patterns:
            if p in u:
                return True
        
        return False
    
    def count_vod_episodes(self, play_url_raw):
        """统计剧集数量"""
        raw = str(play_url_raw).strip()
        if not raw:
            return 0
        
        groups = [g.strip() for g in raw.split('$$$') if g.strip()]
        if not groups:
            groups = [raw]
        
        total = 0
        for group in groups:
            episodes = [e.strip() for e in group.split('#') if e.strip()]
            total += len(episodes)
        
        return max(1, total)
    
    def get_file_icon(self, ext, is_dir=False):
        if is_dir:
            return '📁'
        if ext in self.media_exts:
            return '🎬'
        if ext in self.audio_exts:
            return '🎵'
        if ext in self.image_exts:
            return '📷'
        if ext in self.list_exts:
            return '📋'
        if ext in self.lrc_exts:
            return '📝'
        if ext in self.db_exts:
            return '🗄️'
        if ext in self.magnet_exts:
            return '🧲'
        return '📄'
    
    # ==================== 精确歌词解码（增强版）====================
    
    def _is_valid_lyrics(self, text):
        """简单验证是否为有效歌词"""
        if not text or len(text) < 20:  # 太短的不可能是歌词
            return False
        
        # 检查是否包含常见歌词标记
        lyrics_markers = ['[ti:', '[ar:', '[al:', '[by:', '[00:', '[01:', '[02:', 
                         '作词', '作曲', '编曲', '演唱', '歌词']
        
        for marker in lyrics_markers:
            if marker in text:
                return True
        
        # 检查是否包含常见时间标签格式 [mm:ss.xx]
        if re.search(r'\[\d{2}:\d{2}\.\d{2,}\]', text):
            return True
        
        # 如果包含较多中文且有一定长度，也可能是歌词
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if chinese_count > 10 and len(text) > 100:
            return True
        
        return False
    
    def decode_lyrics_data(self, data):
        """专门解码歌词数据 - 增强版：确保不阻断流程"""
        if not data:
            return None
        
        # 重新排序编码优先级（UTF-8优先）
        encodings = [
            ('utf-8', '尝试 UTF-8'),
            ('gbk', '尝试 GBK'),
            ('gb18030', '尝试 GB18030'),
            ('gb2312', '尝试 GB2312'),
            ('big5', '尝试 Big5'),
            ('utf-16', '尝试 UTF-16'),
            ('utf-16le', '尝试 UTF-16LE'),
            ('utf-16be', '尝试 UTF-16BE'),
        ]
        
        # 记录尝试过的编码和结果
        all_attempts = []
        
        for enc, desc in encodings:
            try:
                decoded = data.decode(enc)
                # 验证解码结果是否合理（包含常见歌词字符）
                if self._is_valid_lyrics(decoded):
                    print(f"✅ 使用 {desc} 解码成功")
                    return decoded
                else:
                    # 虽然解码成功但内容可能不是有效歌词，记录下来备用
                    all_attempts.append((enc, decoded))
                    print(f"⚠️ {desc} 解码成功但内容异常，长度: {len(decoded)}")
            except Exception as e:
                continue
        
        # 如果所有编码都失败，但至少有一个解码成功（即使内容可能异常）
        if all_attempts:
            # 选择解码结果最长的（通常歌词内容较长）
            best_attempt = max(all_attempts, key=lambda x: len(x[1]))
            print(f"⚠️ 使用备选解码 {best_attempt[0]}，内容可能不完整")
            return best_attempt[1]
        
        # 实在不行，尝试强制解码（忽略错误）
        try:
            forced = data.decode('utf-8', errors='ignore')
            if len(forced) > 50:  # 至少有一定长度
                print(f"⚠️ 使用强制 UTF-8 解码（忽略错误）")
                return forced
        except:
            pass
        
        return None
    
    def extract_mp3_lyrics(self, file_path):
        """提取 MP3 文件的歌词"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
                
                # 查找 USLT 帧
                uslt_pos = data.find(b'USLT')
                if uslt_pos < 0:
                    return None
                
                pos = uslt_pos + 4
                if pos + 6 > len(data):
                    return None
                
                # 读取帧大小
                size = int.from_bytes(data[pos:pos+4], 'big')
                pos += 6  # 跳过大小和标志
                
                if pos >= len(data):
                    return None
                
                # 读取编码（1字节）
                encoding = data[pos]
                pos += 1
                
                # 跳过语言（3字节）
                pos += 3
                
                # 跳过内容描述符
                while pos < len(data) and data[pos] != 0:
                    pos += 1
                pos += 1  # 跳过空字节
                
                # 读取歌词内容
                if pos + size - 10 > len(data):
                    return None
                
                lyric_data = data[pos:pos+size-10]
                
                # 根据编码标志尝试解码
                if encoding == 1:  # UTF-16
                    return self.decode_lyrics_data(lyric_data)
                elif encoding == 2:  # UTF-16BE
                    return self.decode_lyrics_data(lyric_data)
                elif encoding == 3:  # UTF-8
                    return self.decode_lyrics_data(lyric_data)
                else:
                    # 未知编码，尝试所有可能
                    return self.decode_lyrics_data(lyric_data)
                    
        except Exception as e:
            self.log(f"MP3提取失败: {e}")
        return None
    
    def extract_flac_lyrics(self, file_path):
        """提取 FLAC 文件的歌词"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
                
                # 查找 LYRICS 字段
                lyrics_pos = data.find(b'LYRICS')
                if lyrics_pos < 0:
                    lyrics_pos = data.find(b'DESCRIPTION')
                
                if lyrics_pos < 0:
                    return None
                
                # 提取歌词数据
                pos = lyrics_pos
                while pos < len(data) and data[pos] != 0:
                    pos += 1
                pos += 1
                
                # 找下一个字段或文件结尾
                end = pos
                while end < len(data):
                    if data[end] == 0 and end + 4 < len(data):
                        # 检查是否是新字段开始
                        next_bytes = data[end+1:end+5]
                        if next_bytes in [b'LYRI', b'DESC', b'COMM', b'TITL']:
                            break
                    end += 1
                
                if pos < end:
                    lyric_data = data[pos:end]
                    return self.decode_lyrics_data(lyric_data)
                
        except Exception as e:
            self.log(f"FLAC提取失败: {e}")
        return None
    
    def find_local_lrc(self, audio_path):
        """查找同文件夹内的同名歌词文件"""
        audio_dir = os.path.dirname(audio_path)
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # 收集目录内所有歌词文件
        lrc_files = self.collect_lrc_in_dir(audio_dir)
        
        # 匹配规则
        for lrc in lrc_files:
            lrc_name = os.path.splitext(lrc['name'])[0]
            
            # 规则1: 完全匹配
            if lrc_name == audio_name:
                print(f"✅ 找到同名歌词: {lrc['path']}")
                return lrc['path']
            
            # 规则2: 忽略大小写匹配
            if lrc_name.lower() == audio_name.lower():
                print(f"✅ 找到忽略大小写匹配歌词: {lrc['path']}")
                return lrc['path']
        
        return None
    
    def read_lrc_file(self, lrc_path):
        """读取歌词文件"""
        try:
            with open(lrc_path, 'rb') as f:
                data = f.read()
            
            return self.decode_lyrics_data(data)
                
        except Exception as e:
            print(f"读取歌词文件失败: {e}")
        return None
    
    def clean_filename(self, filename):
        """清理文件名，移除常见干扰字符"""
        name = os.path.splitext(filename)[0]
        
        patterns = [
            r'【.*?】', r'\[.*?\]', r'\(.*?\)', r'\{.*?\}', r'（.*?）',
            r'\-? ?\d{3,4}kbps', r'\-? ?\d{3,4}Kbps', r'\-? ?\d{3,4}K',
            r'\-? ?\d{3,4}MB', r'\-? ?\d{3,4}Mb', r'\-? ?HQ', r'\-? ?SQ',
            r'\-? ?无损', r'\-? ?高品质', r'\-? ?高音质',
            r'\-? ?320k', r'\-? ?128k', r'\-? ?192k',
            r'\-? ?歌词版', r'\-? ?伴奏版', r'\-? ?纯音乐',
            r'\-? ?Live', r'\-? ?现场版', r'\-? ?演唱会',
        ]
        
        for pattern in patterns:
            name = re.sub(pattern, '', name)
        
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    def extract_song_info(self, filename):
        """从文件名提取歌手和歌曲名"""
        name = self.clean_filename(filename)
        
        artist = ""
        song = name
        
        separators = [
            r'\s+-\s+', r'-\s+', r'\s+-', r'·', r'•', r'–', r'—', r'：', r':', r'、', r'／', r'/'
        ]
        
        for sep in separators:
            parts = re.split(sep, name, maxsplit=1)
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip()
                
                left_is_artist = len(left) < 30 and len(left) > 1
                right_is_artist = len(right) < 30 and len(right) > 1
                
                if left_is_artist and not right_is_artist:
                    artist = left
                    song = right
                elif right_is_artist and not left_is_artist:
                    artist = right
                    song = left
                elif left_is_artist and right_is_artist:
                    if len(left) < len(right):
                        artist = left
                        song = right
                    else:
                        artist = right
                        song = left
                else:
                    artist = left
                    song = right
                break
        
        song = re.sub(r'[《》〈〉『』〔〕]', '', song).strip()
        
        return artist, song
    
    def get_lrc_for_audio(self, file_path):
        """为音频文件获取歌词 - 增强调试版 + 更多歌词源"""
        filename = os.path.basename(file_path)
        ext = self.get_file_ext(file_path).lower()
        
        print(f"\n{'='*60}")
        print(f"🎵 [歌词获取] 开始处理: {filename}")
        print(f"{'='*60}")
        
        cache_key = hashlib.md5(f"audio_{file_path}".encode()).hexdigest()
        
        if cache_key in self.lrc_cache:
            print(f"📦 [缓存命中] 使用缓存的歌词: {filename}")
            return self.lrc_cache[cache_key]
        
        # 从文件名提取歌手和歌曲名（用于网络搜索）
        artist, song = self.extract_song_info(filename)
        print(f"📝 [文件名解析] 歌手='{artist}', 歌曲='{song}'")
        
        # ===== 第一步：网络搜索（最优先）=====
        if artist or song:  # 只要有歌手或歌曲名就尝试搜索
            net_cache_key = hashlib.md5(f"{artist}_{song}".encode()).hexdigest()
            
            if net_cache_key in self.lrc_cache:
                print(f"📦 [网络缓存命中] {artist} - {song}")
                self.lrc_cache[cache_key] = self.lrc_cache[net_cache_key]
                return self.lrc_cache[net_cache_key]
            
            print(f"\n🌐 [网络搜索] 开始搜索歌词...")
            print(f"   ├─ 歌手: {artist}")
            print(f"   └─ 歌曲: {song}")
            
            # 尝试多个歌词源
            lrc_content = None
            
            # 源1: 网易云音乐
            print(f"\n   [源1] 尝试网易云音乐...")
            lrc_content = self._netease_search(artist, song)
            if lrc_content:
                print(f"   ✅ 网易云音乐成功!")
                self.lrc_cache[net_cache_key] = lrc_content
                self.lrc_cache[cache_key] = lrc_content
                return lrc_content
            
            # 源2: QQ音乐
            print(f"\n   [源2] 尝试QQ音乐...")
            lrc_content = self._qq_search(artist, song)
            if lrc_content:
                print(f"   ✅ QQ音乐成功!")
                self.lrc_cache[net_cache_key] = lrc_content
                self.lrc_cache[cache_key] = lrc_content
                return lrc_content
            
            # 源3: 尝试只用歌曲名搜索网易云
            if artist:
                print(f"\n   [源3] 尝试只用歌曲名搜索网易云: {song}")
                lrc_content = self._netease_search("", song)
                if lrc_content:
                    print(f"   ✅ 网易云成功 (仅歌曲名)!")
                    self.lrc_cache[net_cache_key] = lrc_content
                    self.lrc_cache[cache_key] = lrc_content
                    return lrc_content
            
            # 源4: 尝试只用歌曲名搜索QQ音乐
            if artist:
                print(f"\n   [源4] 尝试只用歌曲名搜索QQ音乐: {song}")
                lrc_content = self._qq_search("", song)
                if lrc_content:
                    print(f"   ✅ QQ音乐成功 (仅歌曲名)!")
                    self.lrc_cache[net_cache_key] = lrc_content
                    self.lrc_cache[cache_key] = lrc_content
                    return lrc_content
            
            print(f"\n   ❌ 所有网络源都失败了")
        
        # ===== 第二步：查找本地.lrc文件 =====
        print(f"\n📁 [本地搜索] 查找本地歌词文件...")
        
        # 查找同名的.lrc文件
        lrc_path = os.path.splitext(file_path)[0] + '.lrc'
        if os.path.exists(lrc_path):
            print(f"   ├─ 找到同名歌词: {lrc_path}")
            lrc_content = self.read_lrc_file(lrc_path)
            if lrc_content:
                print(f"   ✅ 读取成功! 长度: {len(lrc_content)} 字符")
                self.lrc_cache[cache_key] = lrc_content
                return lrc_content
            else:
                print(f"   ⚠️ 读取失败")
        
        # 查找同文件夹内的其他歌词文件
        local_lrc_path = self.find_local_lrc(file_path)
        if local_lrc_path:
            print(f"   ├─ 找到本地歌词: {local_lrc_path}")
            lrc_content = self.read_lrc_file(local_lrc_path)
            if lrc_content:
                print(f"   ✅ 读取成功! 长度: {len(lrc_content)} 字符")
                self.lrc_cache[cache_key] = lrc_content
                return lrc_content
        
        print(f"   ❌ 未找到本地歌词文件")
        
        # ===== 第三步：尝试从文件内容提取内嵌歌词（最后）=====
        print(f"\n💾 [内置歌词] 尝试提取内嵌歌词...")
        embedded_lyrics = None
        
        if ext == 'mp3':
            print(f"   ├─ 文件格式: MP3")
            embedded_lyrics = self.extract_mp3_lyrics(file_path)
        elif ext == 'flac':
            print(f"   ├─ 文件格式: FLAC")
            embedded_lyrics = self.extract_flac_lyrics(file_path)
        else:
            print(f"   ├─ 文件格式: {ext} (不支持内置歌词)")
        
        if embedded_lyrics:
            print(f"   ✅ 内置歌词提取成功! 长度: {len(embedded_lyrics)} 字符")
            self.lrc_cache[cache_key] = embedded_lyrics
            return embedded_lyrics
        else:
            print(f"   ❌ 未找到内置歌词或提取失败")
        
        print(f"\n❌ [最终结果] 未找到任何歌词: {filename}")
        print(f"{'='*60}\n")
        return None
    
    def _netease_search(self, artist, song):
        """增强版网易云音乐搜索"""
        keyword = f"{artist} {song}".strip()
        if not keyword:
            return None
        
        print(f"      ├─ 搜索关键词: {keyword}")
        
        try:
            # 第一步：搜索歌曲
            url = "https://music.163.com/api/search/get/web"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.163.com/",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "s": keyword,
                "type": 1,
                "offset": 0,
                "limit": 5  # 增加返回数量
            }
            
            import urllib.parse
            data_str = urllib.parse.urlencode(data)
            
            resp = self.session.post(url, data=data_str, headers=headers, timeout=8)
            print(f"      ├─ 搜索状态码: {resp.status_code}")
            
            if resp.status_code == 200:
                result = resp.json()
                if result['code'] == 200 and result['result']['songCount'] > 0:
                    songs = result['result']['songs']
                    print(f"      ├─ 找到 {len(songs)} 首歌曲")
                    
                    for idx, song in enumerate(songs[:3]):  # 尝试前3首
                        song_name = song['name']
                        song_id = song['id']
                        artists = [a['name'] for a in song['artists']]
                        print(f"      ├─ 候选{idx+1}: {song_name} - {', '.join(artists)}")
                        
                        # 第二步：获取歌词
                        lrc_url = "https://music.163.com/api/song/lyric"
                        params = {
                            "id": song_id,
                            "lv": 1,
                            "kv": 1
                        }
                        
                        lrc_resp = self.session.get(lrc_url, params=params, headers=headers, timeout=5)
                        if lrc_resp.status_code == 200:
                            lrc_data = lrc_resp.json()
                            if 'lrc' in lrc_data and lrc_data['lrc']['lyric']:
                                lrc = lrc_data['lrc']['lyric']
                                if len(lrc) > 50:  # 至少有一定长度
                                    print(f"      ├─ 歌词获取成功! 长度: {len(lrc)}")
                                    return lrc
                                else:
                                    print(f"      ├─ 歌词太短: {len(lrc)}字符")
                        else:
                            print(f"      ├─ 歌词请求失败: {lrc_resp.status_code}")
                else:
                    print(f"      ├─ 未找到歌曲, code={result['code']}")
            else:
                print(f"      ├─ 请求失败: {resp.status_code}")
                
        except Exception as e:
            print(f"      ├─ 异常: {e}")
        
        return None
    
    def _qq_search(self, artist, song):
        """增强版QQ音乐搜索"""
        keyword = f"{artist} {song}".strip()
        if not keyword:
            return None
        
        print(f"      ├─ 搜索关键词: {keyword}")
        
        try:
            # 第一步：搜索歌曲
            search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            params = {
                "w": keyword,
                "format": "json",
                "p": 1,
                "n": 5,  # 增加返回数量
                "platform": "h5",
                "needNewCode": 1
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://y.qq.com/",
                "Origin": "https://y.qq.com"
            }
            
            resp = self.session.get(search_url, params=params, headers=headers, timeout=8)
            print(f"      ├─ 搜索状态码: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                if data['code'] == 0 and data['data']['song']['list']:
                    songs = data['data']['song']['list']
                    print(f"      ├─ 找到 {len(songs)} 首歌曲")
                    
                    for idx, song in enumerate(songs[:3]):  # 尝试前3首
                        song_name = song['songname']
                        song_mid = song['songmid']
                        singers = [s['name'] for s in song['singer']]
                        print(f"      ├─ 候选{idx+1}: {song_name} - {', '.join(singers)}")
                        
                        # 第二步：获取歌词
                        lrc_url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
                        params = {
                            "songmid": song_mid,
                            "format": "json",
                            "platform": "yqq",
                            "needNewCode": 0
                        }
                        
                        # QQ音乐需要特定的Referer
                        lrc_headers = headers.copy()
                        lrc_headers["Referer"] = "https://y.qq.com/portal/player.html"
                        
                        lrc_resp = self.session.get(lrc_url, params=params, headers=lrc_headers, timeout=5)
                        if lrc_resp.status_code == 200:
                            text = lrc_resp.text
                            # QQ音乐返回的是JSONP格式，需要提取JSON
                            match = re.search(r'({.*})', text)
                            if match:
                                lrc_data = json.loads(match.group(1))
                                if 'lyric' in lrc_data and lrc_data['lyric']:
                                    lrc = base64.b64decode(lrc_data['lyric']).decode('utf-8')
                                    if len(lrc) > 50:
                                        print(f"      ├─ 歌词获取成功! 长度: {len(lrc)}")
                                        return lrc
                                    else:
                                        print(f"      ├─ 歌词太短: {len(lrc)}字符")
                        else:
                            print(f"      ├─ 歌词请求失败: {lrc_resp.status_code}")
                else:
                    print(f"      ├─ 未找到歌曲, code={data['code']}")
            else:
                print(f"      ├─ 请求失败: {resp.status_code}")
                
        except Exception as e:
            print(f"      ├─ 异常: {e}")
        
        return None
    
    # ==================== 新增：获取歌曲海报 ====================
    
    def _get_song_poster(self, artist, song):
        """获取歌曲海报"""
        cache_key = hashlib.md5(f"{artist}_{song}".encode()).hexdigest()
        
        # 检查缓存
        if cache_key in self.poster_cache:
            self.log(f"📦 使用缓存海报: {artist} - {song}")
            return self.poster_cache[cache_key]
        
        # 如果没有歌手信息，尝试只用歌曲名
        if not artist:
            return self._search_poster("", song)
        
        # 优先尝试网易云音乐
        poster = self._netease_poster(artist, song)
        if poster:
            self.poster_cache[cache_key] = poster
            return poster
        
        # 尝试QQ音乐
        poster = self._qq_poster(artist, song)
        if poster:
            self.poster_cache[cache_key] = poster
            return poster
        
        # 最后尝试只用歌曲名
        poster = self._search_poster("", song)
        if poster:
            self.poster_cache[cache_key] = poster
            return poster
        
        return None
    
    def _search_poster(self, artist, song):
        """通用海报搜索"""
        # 尝试网易云
        poster = self._netease_poster(artist, song)
        if poster:
            return poster
        
        # 尝试QQ音乐
        poster = self._qq_poster(artist, song)
        if poster:
            return poster
        
        return None
    
    def _netease_poster(self, artist, song):
        """网易云音乐获取海报"""
        try:
            keyword = f"{artist} {song}".strip()
            if not keyword:
                return None
            
            url = "https://music.163.com/api/search/get/web"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.163.com/"
            }
            data = {
                "s": keyword,
                "type": 1,
                "offset": 0,
                "limit": 3
            }
            
            resp = self.session.post(url, data=data, headers=headers, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                if result['code'] == 200 and result['result']['songs']:
                    song_data = result['result']['songs'][0]
                    
                    # 获取专辑图片
                    if 'album' in song_data and 'picUrl' in song_data['album']:
                        pic_url = song_data['album']['picUrl']
                        self.log(f"✅ 网易云获取海报成功: {pic_url}")
                        return pic_url
                    
                    # 尝试获取艺术家图片
                    if 'artists' in song_data and song_data['artists']:
                        artist_data = song_data['artists'][0]
                        if 'picUrl' in artist_data and artist_data['picUrl']:
                            return artist_data['picUrl']
        except Exception as e:
            self.log(f"网易云海报获取异常: {e}")
        return None
    
    def _qq_poster(self, artist, song):
        """QQ音乐获取海报"""
        try:
            keyword = f"{artist} {song}".strip()
            if not keyword:
                return None
            
            # 搜索歌曲
            search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            params = {
                "w": keyword,
                "format": "json",
                "p": 1,
                "n": 3
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://y.qq.com/"
            }
            
            resp = self.session.get(search_url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data['code'] == 0 and data['data']['song']['list']:
                    song_data = data['data']['song']['list'][0]
                    
                    # 获取专辑图片（QQ音乐使用albummid）
                    if 'albummid' in song_data:
                        album_mid = song_data['albummid']
                        # QQ音乐图片规格：300x300
                        pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg"
                        self.log(f"✅ QQ音乐获取海报成功: {pic_url}")
                        return pic_url
                    
                    # 备用方案：使用专辑ID
                    if 'albumid' in song_data:
                        album_id = song_data['albumid']
                        pic_url = f"https://imgcache.qq.com/music/photo/album/{album_id}/albumpic_{album_id}_0.jpg"
                        return pic_url
        except Exception as e:
            self.log(f"QQ音乐海报获取异常: {e}")
        return None
    
    # ==================== 首页分类 ====================
    
    def homeContent(self, filter):
        classes = []
        
        for i, path in enumerate(self.root_paths):
            if os.path.exists(path):
                name = self.path_to_chinese.get(path, os.path.basename(path.rstrip('/')) or f'目录{i}')
                classes.append({
                    "type_id": f"root_{i}",
                    "type_name": name
                })
        
        classes.append({"type_id": "recent", "type_name": "最近添加"})
        classes.append({
            "type_id": self.live_category_id,
            "type_name": self.live_category_name
        })
        
        return {'class': classes}
    
    # ==================== 分类内容 ====================
    
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg)
        
        if tid == self.live_category_id:
            return self._live_category_content(pg)
        
        if tid == 'recent':
            return self._recent_content(pg)
        
        path = tid
        if tid.startswith('root_'):
            idx = int(tid[5:])
            if idx >= len(self.root_paths):
                return {'list': [], 'page': pg, 'pagecount': 1}
            path = self.root_paths[idx]
        elif tid.startswith(self.FOLDER_PREFIX):
            path = self.b64u_decode(tid[len(self.FOLDER_PREFIX):])
        else:
            return {'list': [], 'page': pg, 'pagecount': 1}
        
        if not os.path.exists(path) or not os.path.isdir(path):
            return {'list': [], 'page': pg, 'pagecount': 1}
        
        files = self.scan_directory(path)
        total = len(files)
        
        per_page = 50
        start = (pg - 1) * per_page
        end = min(start + per_page, total)
        page_files = files[start:end]
        
        vlist = []
        
        # 返回上一级
        parent = os.path.dirname(path)
        is_root = False
        for root in self.root_paths:
            root_norm = os.path.normpath(root.rstrip('/'))
            path_norm = os.path.normpath(path)
            if path_norm == root_norm:
                is_root = True
                break
        
        if not is_root and parent and parent != path:
            parent_is_root = False
            root_index = -1
            for i, root in enumerate(self.root_paths):
                root_norm = os.path.normpath(root.rstrip('/'))
                parent_norm = os.path.normpath(parent)
                if parent_norm == root_norm:
                    parent_is_root = True
                    root_index = i
                    break
            
            if parent_is_root and root_index >= 0:
                parent_id = f"root_{root_index}"
                parent_name = self.path_to_chinese.get(self.root_paths[root_index], os.path.basename(parent))
            else:
                parent_id = self.FOLDER_PREFIX + self.b64u_encode(parent)
                parent_name = os.path.basename(parent)
            
            vlist.append({
                'vod_id': parent_id,
                'vod_name': f'⬅️ 返回 {parent_name}',
                'vod_pic': self.file_icons['folder'],
                'vod_remarks': '',
                'vod_tag': 'folder',
                'style': {'type': 'list'}
            })
        
        # 第一页添加连播
        if pg == 1:
            videos = self.collect_videos_in_dir(path)
            if videos:
                vlist.append({
                    'vod_id': self.V_ALL_PREFIX + self.b64u_encode(path),
                    'vod_name': f'视频连播 ({len(videos)}个视频)',
                    'vod_pic': self.file_icons['video_playlist'],
                    'vod_remarks': '顺序播放',
                    'vod_tag': 'video_playlist',
                    'style': {'type': 'list'}
                })
            
            audios = self.collect_audios_in_dir(path)
            if audios:
                vlist.append({
                    'vod_id': self.A_ALL_PREFIX + self.b64u_encode(path),
                    'vod_name': f'音频连播 ({len(audios)}首歌曲)',
                    'vod_pic': self.file_icons['audio_playlist'],
                    'vod_remarks': '顺序播放',
                    'vod_tag': 'audio_playlist',
                    'style': {'type': 'list'}
                })
            
            images = self.collect_images_in_dir(path)
            if images:
                vlist.append({
                    'vod_id': self.PICS_PREFIX + 'slideshow/' + self.b64u_encode(path),
                    'vod_name': f'图片连播 ({len(images)}张照片)',
                    'vod_pic': self.file_icons['image_playlist'],
                    'vod_remarks': '点击浏览全部照片',
                    'vod_tag': 'image_playlist',
                    'style': {'type': 'list'}
                })
        
        # 文件列表
        for f in page_files:
            icon = self.get_file_icon(f['ext'], f['is_dir'])
            
            if f['is_dir']:
                vod_id = self.FOLDER_PREFIX + self.b64u_encode(f['path'])
                remarks = '文件夹'
                vod_tag = 'folder'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['folder'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            elif self.is_audio_file(f['ext']):
                vod_id = f['path']
                remarks = '音频'
                vod_tag = 'audio'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['audio'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            elif self.is_media_file(f['ext']):
                vod_id = f['path']
                remarks = '视频'
                vod_tag = 'video'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['video'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            elif self.is_image_file(f['ext']):
                pics_id = self.URL_B64U_PREFIX + self.b64u_encode(f"{self.PICS_PREFIX}file://{f['path']}")
                vod_id = pics_id
                remarks = '照片'
                vod_tag = 'image'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': f"file://{f['path']}",
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'grid', 'ratio': 1}
                }
            elif self.is_list_file(f['ext']):
                vod_id = self.LIST_PREFIX + self.b64u_encode(f['path'])
                remarks = '播放列表'
                vod_tag = 'list'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['list'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            elif self.is_lrc_file(f['ext']):
                vod_id = f['path']
                remarks = '歌词'
                vod_tag = 'lrc'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['lrc'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            elif self.is_db_file(f['ext']):
                vod_id = self.LIST_PREFIX + self.b64u_encode(f['path'])
                remarks = '数据库'
                vod_tag = 'database'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['database'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            elif self.is_magnet_file(f['ext']):
                vod_id = self.MAGNET_PREFIX + self.b64u_encode(f['path'])
                remarks = '磁力链接'
                vod_tag = 'magnet'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['magnet'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            else:
                vod_id = f['path']
                remarks = '文件'
                vod_tag = 'file'
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons['file'],
                    'vod_remarks': remarks,
                    'vod_tag': vod_tag,
                    'style': {'type': 'list'}
                }
            
            vlist.append(item)
        
        return {
            'list': vlist,
            'page': pg,
            'pagecount': (total + per_page - 1) // per_page,
            'limit': per_page,
            'total': total
        }
    
    def _recent_content(self, pg):
        pg = int(pg)
        all_files = []
        
        camera_path = '/storage/emulated/0/DCIM/Camera/'
        scan_paths = list(self.root_paths)
        if camera_path not in scan_paths and os.path.exists(camera_path):
            scan_paths.append(camera_path)
        
        for path in scan_paths:
            if not os.path.exists(path):
                continue
            self._scan_files_recursive(path, all_files, max_depth=2)
        
        all_files.sort(key=lambda x: x['mtime'], reverse=True)
        all_files = all_files[:100]
        
        per_page = 50
        start = (pg - 1) * per_page
        end = min(start + per_page, len(all_files))
        page_files = all_files[start:end]
        
        import time
        vlist = []
        for f in page_files:
            if self.is_media_file(f['ext']):
                icon = '🎬'
                type_name = '视频'
                icon_type = 'video'
            elif self.is_audio_file(f['ext']):
                icon = '🎵'
                type_name = '音频'
                icon_type = 'audio'
            elif self.is_image_file(f['ext']):
                icon = '📷'
                type_name = '照片'
                icon_type = 'image'
            elif self.is_list_file(f['ext']):
                icon = '📋'
                type_name = '列表'
                icon_type = 'list'
            elif self.is_db_file(f['ext']):
                icon = '🗄️'
                type_name = '数据库'
                icon_type = 'database'
            elif self.is_magnet_file(f['ext']):
                icon = '🧲'
                type_name = '磁力'
                icon_type = 'magnet'
            elif self.is_lrc_file(f['ext']):
                icon = '📝'
                type_name = '歌词'
                icon_type = 'lrc'
            else:
                icon = '📄'
                type_name = '文件'
                icon_type = 'file'
            
            mtime = f['mtime']
            now = time.time()
            diff = now - mtime
            
            if diff < 3600:
                minutes = int(diff / 60)
                remarks = f"{minutes}分钟前"
            elif diff < 86400:
                hours = int(diff / 3600)
                remarks = f"{hours}小时前"
            else:
                remarks = time.strftime('%m-%d %H:%M', time.localtime(mtime))
            
            vod_id = f['path']
            
            if self.is_image_file(f['ext']):
                vod_id = self.URL_B64U_PREFIX + self.b64u_encode(f"{self.PICS_PREFIX}file://{f['path']}")
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': f"file://{f['path']}",
                    'vod_remarks': remarks,
                    'vod_tag': 'file',
                    'style': {'type': 'grid', 'ratio': 1}
                }
            else:
                if self.is_db_file(f['ext']):
                    vod_id = self.LIST_PREFIX + self.b64u_encode(f['path'])
                elif self.is_magnet_file(f['ext']):
                    vod_id = self.MAGNET_PREFIX + self.b64u_encode(f['path'])
                
                item = {
                    'vod_id': vod_id,
                    'vod_name': f"{icon} {f['name']}",
                    'vod_pic': self.file_icons[icon_type],
                    'vod_remarks': remarks,
                    'vod_tag': 'file',
                    'style': {'type': 'grid', 'ratio': 1}
                }
            
            vlist.append(item)
        
        return {
            'list': vlist,
            'page': pg,
            'pagecount': (len(all_files) + per_page - 1) // per_page,
            'limit': per_page,
            'total': len(all_files)
        }
    
    def _scan_files_recursive(self, path, file_list, max_depth=2, current_depth=0):
        if current_depth > max_depth:
            return
        
        try:
            if not os.path.exists(path):
                return
            
            for name in os.listdir(path):
                if name.startswith('.'):
                    continue
                
                full_path = os.path.join(path, name)
                
                if os.path.isdir(full_path):
                    self._scan_files_recursive(full_path, file_list, max_depth, current_depth + 1)
                else:
                    ext = self.get_file_ext(name)
                    if (self.is_media_file(ext) or self.is_audio_file(ext) or 
                        self.is_list_file(ext) or self.is_image_file(ext) or
                        self.is_db_file(ext) or self.is_magnet_file(ext)):
                        
                        mtime = os.path.getmtime(full_path)
                        if time.time() - mtime < 7 * 24 * 3600:
                            file_list.append({
                                'name': name,
                                'path': full_path,
                                'ext': ext,
                                'mtime': mtime,
                            })
        except Exception as e:
            print(f"扫描错误 {path}: {e}")
    
    def _scan_files_recursive_for_search(self, path, file_list, max_depth=3, current_depth=0):
        if current_depth > max_depth:
            return
        
        try:
            if not os.path.exists(path):
                return
            
            for name in os.listdir(path):
                if name.startswith('.'):
                    continue
                
                full_path = os.path.join(path, name)
                
                if os.path.isdir(full_path):
                    self._scan_files_recursive_for_search(full_path, file_list, max_depth, current_depth + 1)
                else:
                    ext = self.get_file_ext(name)
                    file_list.append({
                        'name': name,
                        'path': full_path,
                        'ext': ext,
                        'mtime': os.path.getmtime(full_path),
                    })
        except Exception as e:
            print(f"搜索扫描错误 {path}: {e}")
    
    # ==================== 详情页 ====================
    
    def detailContent(self, ids):
        id_val = ids[0]
        self.log(f"详情页请求: {id_val}")
        
        if id_val.startswith(self.LIVE_PREFIX):
            encoded_data = id_val[len(self.LIVE_PREFIX):]
            source_id = self.b64u_decode(encoded_data)
            return self._live_source_detail(source_id)
        
        if id_val.startswith(self.FOLDER_PREFIX):
            folder_path = self.b64u_decode(id_val[len(self.FOLDER_PREFIX):])
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                return self.categoryContent(folder_path, 1, None, None)
            else:
                return {'list': []}
        
        if id_val.startswith(self.PICS_PREFIX + 'slideshow/'):
            encoded = id_val[len(self.PICS_PREFIX + 'slideshow/'):]
            dir_path = self.b64u_decode(encoded)
            
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {'list': []}
            
            images = self.collect_images_in_dir(dir_path)
            
            if not images:
                return {'list': []}
            
            play_urls = []
            for img in images:
                url = f"file://{img['path']}"
                name = os.path.splitext(img['name'])[0]
                play_urls.append(f"{name}${url}")
            
            return {'list': [{
                'vod_id': id_val,
                'vod_name': f"📷 图片连播 - {os.path.basename(dir_path)} ({len(images)}张)",
                'vod_pic': self.file_icons['image_playlist'],
                'vod_play_from': '图片浏览',
                'vod_play_url': '#'.join(play_urls),
                'style': {'type': 'list'}
            }]}
        
        if id_val.startswith(self.URL_B64U_PREFIX):
            decoded = self.b64u_decode(id_val[len(self.URL_B64U_PREFIX):])
            if decoded and decoded.startswith(self.PICS_PREFIX):
                pics_data = decoded[len(self.PICS_PREFIX):]
                
                if '&&' in pics_data:
                    pic_urls = pics_data.split('&&')
                    play_urls = []
                    
                    for url in pic_urls:
                        if url.startswith('file://'):
                            file_path = url[7:]
                            file_name = os.path.basename(file_path)
                            play_urls.append(f"{file_name}${url}")
                        else:
                            file_name = os.path.basename(url.split('?')[0]) or "图片"
                            play_urls.append(f"{file_name}${url}")
                    
                    return {'list': [{
                        'vod_id': id_val,
                        'vod_name': f'图片相册 ({len(pic_urls)}张)',
                        'vod_pic': pic_urls[0],
                        'vod_play_from': '图片查看',
                        'vod_play_url': '#'.join(play_urls),
                        'style': {'type': 'list'}
                    }]}
                else:
                    file_name = os.path.basename(pics_data.split('?')[0])
                    if pics_data.startswith('file://'):
                        file_name = os.path.basename(pics_data[7:])
                    
                    return {'list': [{
                        'vod_id': id_val,
                        'vod_name': file_name,
                        'vod_pic': pics_data,
                        'vod_play_from': '图片查看',
                        'vod_play_url': f"查看${pics_data}",
                        'style': {'type': 'list'}
                    }]}
        
        if id_val.startswith(self.CAMERA_ALL_PREFIX):
            encoded = id_val[len(self.CAMERA_ALL_PREFIX):]
            dir_path = self.b64u_decode(encoded)
            
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return {'list': []}
            
            images = self.collect_images_in_dir(dir_path)
            
            if not images:
                return {'list': []}
            
            play_urls = []
            for img in images:
                url = f"file://{img['path']}"
                name = os.path.splitext(img['name'])[0]
                play_urls.append(f"{name}${url}")
            
            return {'list': [{
                'vod_id': id_val,
                'vod_name': f"📷 相机照片 ({len(images)}张)",
                'vod_pic': self.file_icons['image_playlist'],
                'vod_play_from': '照片查看',
                'vod_play_url': '#'.join(play_urls),
                'style': {'type': 'list'}
            }]}
        
        if id_val.startswith(self.MAGNET_PREFIX):
            encoded = id_val[len(self.MAGNET_PREFIX):]
            file_path = self.b64u_decode(encoded)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {'list': []}
            
            items = self.parse_magnet_file(file_path)
            
            if not items:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().strip()
                        magnet_match = re.search(r'(magnet:\?[^\s\'"<>]+)', content)
                        if magnet_match:
                            magnet_url = magnet_match.group(1)
                            return {'list': [{
                                'vod_id': id_val,
                                'vod_name': os.path.basename(file_path),
                                'vod_pic': self.file_icons['magnet'],
                                'vod_play_from': '磁力链接',
                                'vod_play_url': f"{os.path.splitext(os.path.basename(file_path))[0]}${magnet_url}",
                                'style': {'type': 'list'}
                            }]}
                except:
                    pass
                
                return {'list': [{
                    'vod_id': id_val,
                    'vod_name': os.path.basename(file_path),
                    'vod_pic': self.file_icons['magnet'],
                    'vod_play_from': '磁力链接',
                    'vod_play_url': f"打开文件$file://{file_path}",
                    'style': {'type': 'list'}
                }]}
            
            play_urls = []
            for idx, item in enumerate(items):
                name = item.get('name', f'链接{idx+1}')
                url = item.get('url', '').strip()
                
                if url and url.startswith('magnet:'):
                    play_urls.append(f"{name}${url}")
                    self.log(f"添加磁力链接: {name}")
            
            if not play_urls:
                return {'list': [{
                    'vod_id': id_val,
                    'vod_name': os.path.basename(file_path),
                    'vod_pic': self.file_icons['magnet'],
                    'vod_play_from': '磁力链接',
                    'vod_play_url': f"打开文件$file://{file_path}",
                    'style': {'type': 'list'}
                }]}
            
            play_url_str = '#'.join(play_urls)
            self.log(f"磁力链接播放串: {play_url_str[:200]}...")
            
            return {'list': [{
                'vod_id': id_val,
                'vod_name': os.path.basename(file_path),
                'vod_pic': self.file_icons['magnet'],
                'vod_play_from': '磁力链接列表',
                'vod_play_url': play_url_str,
                'style': {'type': 'list'}
            }]}
        
        if id_val.startswith(self.LIST_PREFIX):
            encoded = id_val[len(self.LIST_PREFIX):]
            file_path = self.b64u_decode(encoded)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {'list': []}
            
            ext = self.get_file_ext(file_path)
            self.log(f"处理列表文件: {file_path}, 类型: {ext}")
            
            if ext in self.db_exts:
                items = self.parse_db_file(file_path)
                self.log(f"数据库解析到 {len(items)} 条记录")
                
                if not items:
                    return {'list': [{
                        'vod_id': id_val,
                        'vod_name': os.path.basename(file_path),
                        'vod_pic': self.file_icons['database'],
                        'vod_play_from': '数据库',
                        'vod_play_url': f"播放$file://{file_path}",
                        'style': {'type': 'list'}
                    }]}
                
                play_urls = self._build_play_urls(items)
                
                if not play_urls:
                    return {'list': [{
                        'vod_id': id_val,
                        'vod_name': os.path.basename(file_path),
                        'vod_pic': self.file_icons['database'],
                        'vod_play_from': '数据库',
                        'vod_play_url': f"播放$file://{file_path}",
                        'style': {'type': 'list'}
                    }]}
                
                play_url_str = '#'.join(play_urls)
                self.log(f"数据库播放串预览: {play_url_str[:200]}...")
                
                return {'list': [{
                    'vod_id': id_val,
                    'vod_name': os.path.basename(file_path),
                    'vod_pic': items[0].get('pic', '') if items else self.file_icons['database'],
                    'vod_play_from': '数据库播放列表',
                    'vod_play_url': play_url_str,
                    'style': {'type': 'list'}
                }]}
            
            items = []
            if ext in ['m3u', 'm3u8']:
                items = self.parse_m3u_file(file_path)
                self.log(f"M3U解析到 {len(items)} 条记录")
            elif ext == 'txt':
                items = self.parse_txt_file(file_path)
                self.log(f"TXT解析到 {len(items)} 条记录")
            elif ext == 'json':
                items = self.parse_json_file(file_path)
                self.log(f"JSON解析到 {len(items)} 条记录")
            
            if not items:
                url = f"file://{file_path}"
                name = os.path.splitext(os.path.basename(file_path))[0]
                return {'list': [{
                    'vod_id': id_val,
                    'vod_name': os.path.basename(file_path),
                    'vod_pic': self.file_icons['list'],
                    'vod_play_from': '播放列表',
                    'vod_play_url': f"{name}${url}",
                    'style': {'type': 'list'}
                }]}
            
            play_urls = self._build_play_urls(items)
            
            if not play_urls:
                return {'list': []}
            
            play_url_str = '#'.join(play_urls)
            self.log(f"播放串预览: {play_url_str[:200]}...")
            
            return {'list': [{
                'vod_id': id_val,
                'vod_name': os.path.basename(file_path),
                'vod_pic': items[0].get('pic', '') if items else self.file_icons['list'],
                'vod_play_from': '播放列表',
                'vod_play_url': play_url_str,
                'style': {'type': 'list'}
            }]}
        
        if id_val.startswith(self.A_ALL_PREFIX):
            encoded = id_val[len(self.A_ALL_PREFIX):]
            dir_path = self.b64u_decode(encoded)
            audios = self.collect_audios_in_dir(dir_path)
            
            if not audios:
                return {'list': []}
            
            play_urls = []
            for a in audios:
                url = f"file://{a['path']}"
                name = os.path.splitext(a['name'])[0]
                play_urls.append(f"{name}${url}")
            
            # ===== 新增：尝试获取第一首歌曲的海报作为封面 =====
            poster = None
            if audios:
                filename = os.path.basename(audios[0]['path'])
                artist, song = self.extract_song_info(filename)
                self.log(f"🎵 获取连播封面: 歌手='{artist}', 歌曲='{song}'")
                poster = self._get_song_poster(artist, song)
            
            return {'list': [{
                'vod_id': id_val,
                'vod_name': f"音频连播 - {os.path.basename(dir_path)} ({len(audios)}首)",
                'vod_pic': poster if poster else self.file_icons['audio_playlist'],  # 优先使用获取到的海报
                'vod_play_from': '本地音乐',
                'vod_play_url': '#'.join(play_urls),
                'style': {'type': 'list'}
            }]}
        
        if id_val.startswith(self.V_ALL_PREFIX):
            encoded = id_val[len(self.V_ALL_PREFIX):]
            dir_path = self.b64u_decode(encoded)
            videos = self.collect_videos_in_dir(dir_path)
            
            if not videos:
                return {'list': []}
            
            play_urls = []
            for v in videos:
                url = f"file://{v['path']}"
                name = os.path.splitext(v['name'])[0]
                play_urls.append(f"{name}${url}")
            
            # ===== 新增：尝试获取第一个视频的缩略图（如果有的话）=====
            # 视频暂时无法获取海报，保持原有图标
            
            return {'list': [{
                'vod_id': id_val,
                'vod_name': f"视频连播 - {os.path.basename(dir_path)} ({len(videos)}集)",
                'vod_pic': self.file_icons['video_playlist'],
                'vod_play_from': '本地视频',
                'vod_play_url': '#'.join(play_urls),
                'style': {'type': 'list'}
            }]}
        
        if not os.path.exists(id_val):
            self.log(f"路径不存在: {id_val}")
            return {'list': []}
        
        if os.path.isdir(id_val):
            return self.categoryContent(id_val, 1, None, None)
        
        name = os.path.basename(id_val)
        ext = self.get_file_ext(name)
        self.log(f"处理文件: {name}, 类型: {ext}")
        
        vod = {
            'vod_id': id_val,
            'vod_name': name,
            'vod_play_from': '本地播放',
            'vod_play_url': '',
            'style': {'type': 'list'}
        }
        
        if self.is_image_file(ext):
            pics_id = self.URL_B64U_PREFIX + self.b64u_encode(f"{self.PICS_PREFIX}file://{id_val}")
            vod['vod_id'] = pics_id
            vod['vod_play_url'] = f"查看${pics_id}"
            vod['vod_pic'] = f"file://{id_val}"
            vod['vod_name'] = f"🖼️ {name}"
        elif self.is_audio_file(ext):
            url = f"file://{id_val}"
            display_name = os.path.splitext(name)[0]
            vod['vod_play_url'] = f"{display_name}${url}"
            vod['vod_name'] = f"🎵 {name}"
            
            # ===== 新增：为单个音频文件获取海报 =====
            artist, song = self.extract_song_info(name)
            poster = self._get_song_poster(artist, song)
            if poster:
                vod['vod_pic'] = poster
                self.log(f"✅ 详情页添加海报: {poster}")
            else:
                vod['vod_pic'] = self.file_icons['audio']
        elif self.is_media_file(ext):
            url = f"file://{id_val}"
            display_name = os.path.splitext(name)[0]
            vod['vod_play_url'] = f"{display_name}${url}"
            vod['vod_pic'] = self.file_icons['video']
        elif self.is_list_file(ext) or self.is_db_file(ext) or self.is_magnet_file(ext):
            if self.is_magnet_file(ext):
                vod_id = self.MAGNET_PREFIX + self.b64u_encode(id_val)
            else:
                vod_id = self.LIST_PREFIX + self.b64u_encode(id_val)
            self.log(f"列表文件，重新解析: {vod_id}")
            return self.detailContent([vod_id])
        
        return {'list': [vod]}
    
    def _build_play_urls(self, items):
        play_urls = []
        for item in items:
            name = item.get('name', '未命名')
            url = item.get('url') or item.get('play_url', '')
            if not url:
                continue
            play_urls.append(f"{name}${url}")
        return play_urls
    
    def _extract_real_m3u8_url(self, page_url):
        if page_url in self.m3u8_cache:
            cached = self.m3u8_cache[page_url]
            if cached:
                self.log(f"✅ 使用缓存的m3u8地址: {cached}")
            else:
                self.log(f"⚠️ 缓存中无有效地址: {page_url}")
            return cached
        
        try:
            self.log(f"🔍 尝试从页面提取真实m3u8地址: {page_url}")
            
            from urllib.parse import urlparse
            parsed = urlparse(page_url)
            domain = parsed.netloc
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            self.log(f"域名: {domain}, 基础URL: {base_url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": base_url + "/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            
            response = self.session.get(page_url, headers=headers, timeout=10)
            if response.status_code != 200:
                self.log(f"❌ 获取页面失败: {response.status_code}")
                return None
            
            html = response.text
            self.log(f"✅ 页面获取成功，内容长度: {len(html)}")
            
            m3u8_patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'(//[^\s"\']+\.m3u8[^\s"\']*)',
                r'url["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    url = matches[0]
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = base_url + url
                    self.log(f"✅ 找到m3u8地址: {url}")
                    self.m3u8_cache[page_url] = url
                    return url
            
            self.log(f"❌ 未能提取到真实m3u8地址")
            self.m3u8_cache[page_url] = None
            return None
            
        except Exception as e:
            self.log(f"❌ 提取真实地址失败: {e}")
            self.m3u8_cache[page_url] = None
            return None
    
    # ==================== 播放页 ====================
    
    def playerContent(self, flag, id, vipFlags):
        self.log(f"播放请求: flag={flag}, id={id}")
        
        original_id = id
        
        if '$' in id:
            parts = id.split('$', 1)
            if len(parts) == 2:
                id = parts[1]
                self.log(f"从 {original_id} 提取真实URL: {id}")
        
        url = id
        
        if url.startswith(('http://', 'https://', 'file://')):
            self.log(f"URL已经是直接地址: {url[:50]}...")
        else:
            try:
                decoded = base64.b64decode(id).decode('utf-8')
                if decoded.startswith(('http://', 'https://', 'file://')):
                    url = decoded
                    self.log(f"标准base64解码成功: {url[:50]}...")
            except:
                pass
            
            if url == id and id.startswith(self.URL_B64U_PREFIX):
                try:
                    decoded = self.b64u_decode(id[len(self.URL_B64U_PREFIX):])
                    if decoded:
                        url = decoded
                        self.log(f"b64u解码成功: {url[:50]}...")
                except:
                    pass
        
        if 'dytt-' in url and '/share/' in url and not url.endswith('.m3u8'):
            self.log(f"检测到dytt分享链接，尝试提取真实地址")
            real_url = self._extract_real_m3u8_url(url)
            if real_url:
                url = real_url
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }
        
        result = {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": headers
        }
        
        if flag == 'migu_live' or 'miguvideo.com' in domain:
            headers = {
                "User-Agent": "com.android.chrome/3.7.0 (Linux;Android 15)",
                "Accept": "*/*",
                "Referer": "https://www.miguvideo.com/"
            }
            self.log(f"使用咪咕视频专用请求头")
            result["playerType"] = 2
        elif flag == 'gongdian_live' or 'gongdian.top' in domain:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Referer": "https://gongdian.top/"
            }
            self.log(f"使用宫殿直播专用请求头")
            result["playerType"] = 2
        elif flag == 'simple_live':
            pass
        elif 't.061899.xyz' in domain:
            headers = {
                "User-Agent": "okhttp/3.12.11",
                "Referer": "http://t.061899.xyz/",
                "Accept": "*/*"
            }
            self.log(f"使用 t.061899.xyz 专用请求头")
        elif 'rihou.cc' in domain:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://rihou.cc:555/",
                "Accept": "*/*"
            }
            self.log(f"使用 rihou.cc 专用请求头")
        elif domain:
            headers["Referer"] = f"https://{domain}/"
        
        if '.m3u8' in url or '.ts' in url:
            if "Range" in headers:
                del headers["Range"]
        
        result["header"] = headers
        
        # ===== 音频文件处理：获取歌词和海报 =====
        if url.startswith('file://'):
            file_path = url[7:]
            if os.path.exists(file_path) and self.is_audio_file(self.get_file_ext(file_path)):
                self.log(f"🔍 正在为音频文件获取信息: {os.path.basename(file_path)}")
                
                # 获取歌词（使用新的优先网络逻辑）
                lrc = self.get_lrc_for_audio(file_path)
                if lrc:
                    if isinstance(lrc, (list, tuple)):
                        lrc = '\n'.join(lrc)
                    result["lrc"] = lrc
                    self.log(f"✅ 歌词已添加")
                else:
                    self.log(f"⚠️ 未找到歌词")
                
                # 新增：获取歌曲海报
                filename = os.path.basename(file_path)
                artist, song = self.extract_song_info(filename)
                self.log(f"🎵 尝试获取海报: 歌手='{artist}', 歌曲='{song}'")
                
                poster = self._get_song_poster(artist, song)
                if poster:
                    result["poster"] = poster
                    self.log(f"✅ 海报已添加: {poster}")
                else:
                    self.log(f"⚠️ 未找到海报")
        
        self.log(f"播放器返回: {result}")
        return result
    
    # ==================== 搜索 ====================
    
    def searchContent(self, key, quick, pg=1):
        pg = int(pg)
        results = []
        
        clean_key = key.lower()
        icon_pattern = r'^[📁📂🎬🎵📷📋📝🗄️🧲📄🖼️🎞️⬅️\s]+'
        clean_key = re.sub(icon_pattern, '', clean_key)
        
        if not clean_key:
            clean_key = key.lower()
        
        for path in self.root_paths:
            if not os.path.exists(path):
                continue
            
            all_files = []
            self._scan_files_recursive_for_search(path, all_files, max_depth=3)
            
            for f in all_files:
                if clean_key in f['name'].lower():
                    if self.is_audio_file(f['ext']):
                        icon = '🎵'
                        icon_type = 'audio'
                    elif self.is_media_file(f['ext']):
                        icon = '🎬'
                        icon_type = 'video'
                    elif self.is_image_file(f['ext']):
                        icon = '📷'
                        icon_type = 'image'
                    elif self.is_list_file(f['ext']):
                        icon = '📋'
                        icon_type = 'list'
                    elif self.is_db_file(f['ext']):
                        icon = '🗄️'
                        icon_type = 'database'
                    elif self.is_magnet_file(f['ext']):
                        icon = '🧲'
                        icon_type = 'magnet'
                    elif self.is_lrc_file(f['ext']):
                        icon = '📝'
                        icon_type = 'lrc'
                    else:
                        icon = '📄'
                        icon_type = 'file'
                    
                    if self.is_image_file(f['ext']):
                        vod_id = self.URL_B64U_PREFIX + self.b64u_encode(f"{self.PICS_PREFIX}file://{f['path']}")
                        results.append({
                            'vod_id': vod_id,
                            'vod_name': f"{icon} {f['name']}",
                            'vod_pic': f"file://{f['path']}",
                            'vod_remarks': '',
                            'style': {'type': 'grid', 'ratio': 1}
                        })
                    else:
                        vod_id = f['path']
                        if self.is_db_file(f['ext']):
                            vod_id = self.LIST_PREFIX + self.b64u_encode(f['path'])
                        elif self.is_magnet_file(f['ext']):
                            vod_id = self.MAGNET_PREFIX + self.b64u_encode(f['path'])
                        
                        results.append({
                            'vod_id': vod_id,
                            'vod_name': f"{icon} {f['name']}",
                            'vod_pic': self.file_icons[icon_type],
                            'vod_remarks': '',
                            'style': {'type': 'list'}
                        })
        
        results.sort(key=lambda x: (clean_key not in x['vod_name'].lower(), x['vod_name']))
        
        per_page = 50
        start = (pg - 1) * per_page
        end = min(start + per_page, len(results))
        page_results = results[start:end]
        
        return {
            'list': page_results,
            'page': pg,
            'pagecount': (len(results) + per_page - 1) // per_page,
            'limit': per_page,
            'total': len(results)
        }