import sys,json,requests,base64
from urllib.parse import urlparse,quote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self,extend=""):
        redirect_url_encoded="aHR0cDovL3lveW8udnZ2di5lZS9qay95b3lveXRqeC5waHA="
        redirect_url=base64.b64decode(redirect_url_encoded).decode('utf-8')
        headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8','Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8','Connection':'keep-alive','Upgrade-Insecure-Requests':'1'}
        try:
            session=requests.Session()
            response=session.get(redirect_url,timeout=15,allow_redirects=True,headers=headers)
            if response.status_code==200:
                self.parse_api_url=response.url
                print(f"Redirect URL: {self.parse_api_url}")
            else:
                self.parse_api_url=redirect_url
                print(f"Redirect failed, status: {response.status_code}, using original URL: {redirect_url}")
        except Exception as e:
            self.parse_api_url=redirect_url
            print(f"Exception getting redirect URL: {str(e)}, using original URL: {redirect_url}")
        try:
            response=requests.get(self.parse_api_url,params={'action':'get_host'},timeout=15,headers=headers)
            if response.status_code==200:
                data=response.json()
                if data.get('code')==200 and 'host_encoded' in data:
                    self.host_encoded=data['host_encoded']
                    print("Host config obtained")
                else:
                    raise Exception(f"PHP error: {data.get('msg','Unknown error')}")
            else:
                raise Exception(f"PHP request failed: HTTP {response.status_code}")
        except Exception as e:
            raise Exception(f"Failed to get host config: {str(e)}")
        try:
            response=requests.get(self.parse_api_url,params={'action':'get_line_replacements'},timeout=15,headers=headers)
            if response.status_code==200:
                data=response.json()
                if data.get('code')==200 and 'replacements' in data:
                    self.line_replacements=data['replacements']
                    print("Line replacements obtained")
                else:
                    self.line_replacements=[]
                    print("Failed to get line replacements, using empty list")
            else:
                self.line_replacements=[]
                print(f"HTTP error getting line replacements: {response.status_code}, using empty list")
        except Exception as e:
            self.line_replacements=[]
            print(f"Exception getting line replacements: {str(e)}, using empty list")
        
        self.block_lines = False
        self.blocked_keywords = ['爱','优','腾','芒','BL']
        
        self._host_decoded=None
        
    @property
    def host(self):
        if self._host_decoded is None:
            self._host_decoded=base64.b64decode(self.host_encoded).decode('utf-8')
        return self._host_decoded
    
    def getName(self):pass
    def isVideoFormat(self,url):pass
    def manualVideoCheck(self):pass
    def destroy(self):pass

    headers={'User-Agent':'okhttp/4.12.0'}
    headerx={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    def homeContent(self,filter):
        data=self.fetch(f"{self.host}//api.php/app/nav?token=",headers=self.headers).json()
        keys=["class","area","lang","year","letter","by","sort"]
        filters={}
        classes=[]
        for item in data['list']:
            has_non_empty_field=False
            jsontype_extend=item["type_extend"]
            classes.append({"type_name":item["type_name"],"type_id":item["type_id"]})
            for key in keys:
                if key in jsontype_extend and jsontype_extend[key].strip()!="":
                    has_non_empty_field=True
                    break
            if has_non_empty_field:
                filters[str(item["type_id"])]=[]
            for dkey in jsontype_extend:
                if dkey in keys and jsontype_extend[dkey].strip()!="":
                    values=jsontype_extend[dkey].split(",")
                    value_array=[{"n":value.strip(),"v":value.strip()} for value in values if value.strip()!=""]
                    filters[str(item["type_id"])].append({"key":dkey,"name":dkey,"value":value_array})
        result={}
        result["class"]=classes
        result["filters"]=filters
        return result

    def homeVideoContent(self):
        data=self.fetch(f"{self.host}/api.php/app/index_video?token=",headers=self.headers).json()
        videos=[]
        for item in data['list']:videos.extend(item['vlist'])
        return {'list':videos}

    def categoryContent(self,tid,pg,filter,extend):
        params={'tid':tid,'class':extend.get('class',''),'area':extend.get('area',''),'lang':extend.get('lang',''),'year':extend.get('year',''),'limit':'18','pg':pg}
        data=self.fetch(f"{self.host}/api.php/app/video",params=params,headers=self.headers).json()
        return data

    def detailContent(self,ids):
        data=self.fetch(f"{self.host}/api.php/app/video_detail?id={ids[0]}",headers=self.headers).json()
        if 'data' in data and 'vod_url_with_player' in data['data']:
            play_from=[]
            play_url=[]
            
            for item in data['data']['vod_url_with_player']:
                name=item.get('name') or item.get('code') or 'Unknown'
                for replacement in self.line_replacements:
                    if replacement['old'] in name:
                        name=name.replace(replacement['old'],replacement['new'])
                        break
                
                if self.block_lines and any(keyword in name for keyword in self.blocked_keywords):
                    print(f"屏蔽线路: {name}")
                    continue
                
                play_from.append(name)
                play_url.append(item['url'])
                
            data['data']['vod_play_from']='$$$'.join(play_from)
            data['data']['vod_play_url']='$$$'.join(play_url)
        return {'list':[data['data']]}

    def searchContent(self,key,quick,pg="1"):
        data=self.fetch(f"{self.host}/api.php/app/search?text={key}&pg={pg}",headers=self.headers).json()
        videos=data['list']
        for item in data['list']:item.pop('type',None)
        return {'list':videos,'page':pg}

    def playerContent(self,flag,id,vipFlags):
        headert={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        try:
            is_blocked_line = any(keyword in flag for keyword in self.blocked_keywords)
            
            if is_blocked_line:
                print(f"检测到屏蔽线路 [{flag}]，强制使用外部解析")
                params={'action':'process_play_url','url':id,'flag':flag}
                response=requests.get(self.parse_api_url,params=params,timeout=15,headers=headert)
                if response.status_code==200:
                    data=response.json()
                    if data.get('code')==200 and 'url' in data:
                        return {'jx':1,'parse':1,'url':data.get('url'),'header':headert}
            
            params={'action':'process_play_url','url':id,'flag':flag}
            response=requests.get(self.parse_api_url,params=params,timeout=15,headers=headert)
            if response.status_code==200:
                data=response.json()
                if data.get('code')==200 and 'url' in data:
                    return {'jx':data.get('jx',0),'parse':data.get('parse',0),'url':data.get('url'),'header':headert}
            return {'jx':0,'parse':0,'url':id,'header':headert}
        except Exception as e:
            print(f"PlayerContent error: {str(e)}")
            return {'jx':0,'parse':0,'url':id,'header':headert}

    def localProxy(self,param):pass
