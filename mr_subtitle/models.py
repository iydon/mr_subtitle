import json
import os
import pathlib
import pickle
import pydub
import re
import requests
import time

from selenium import webdriver

import oss2
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from . import config
from .utils import av2bv, bv2av, md5


class OSS:
    '''对象存储 OSS

    Example:
        >>> with OSS('target.mp3') as oss:
        >>>     print(oss.url)
    '''
    _bucket = oss2.Bucket(
        oss2.Auth(config.access_key['id'], config.access_key['secret']),
        config.oss['endpoint'], config.oss['bucket_name']
    )

    def __init__(self, path):
        self._path = pathlib.Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f'No such file: "{path}"')
        self._name = md5(str(self._path)) + self._path.suffix

    def __enter__(self):
        self._bucket.put_object_from_file(self._name, str(self._path))
        return self

    def __exit__(self, type, value, traceback):
        self._bucket.delete_object(self._name)

    @property
    def url(self):
        return f'https://{config.oss["bucket_domain"]}/{self._name}'


class Subtitle:
    '''
    Example:
        >>> s = Subtitle('cache')
        >>> s.from_audio('target.mp3')
        >>> s.to_srt('target.srt)
    '''
    def __init__(self, dirname=config.cache_dir):
        self._dirname = pathlib.Path(dirname)
        self._dirname.mkdir(exist_ok=True)
        self._data = None
        self._client = None

    @property
    def data(self):
        return self._data

    @property
    def from_(self):
        return {
            'audio': self.from_audio,
            'json': self.from_json,
            'srt': self.from_srt,
        }

    @property
    def to(self):
        return {
            'json': self.to_json,
            'srt': self.to_srt,
        }

    def from_audio(self, filename, delay=10, **kwargs):
        # https://help.aliyun.com/document_detail/90727.html
        path = self._dirname / filename
        with OSS(str(path)) as oss:
            task_id = self._trans(oss.url, **kwargs)
            response = self._polling(task_id, delay=delay)
            self._data = response['Result']['Sentences']

    def from_json(self, filename):
        self._data = json.loads((self._dirname/filename).read_text())

    def from_srt(self, filename, channel_id=0):
        def f(pattern):
            (h, m, s), (ms, ) = (map(int, p.split(':')) for p in pattern.split(','))
            return 1000*(60*(60*h+m)+s)+ms
        def g(part):
            _, times, text = part.splitlines()
            begin, end = map(f, times.split(' --> '))
            return dict(BeginTime=begin, EndTime=end, Text=text, ChannelId=channel_id)
        self._data = list(
            g(p) for p in (self._dirname/filename).read_text().split('\n\n') if p
        )

    def to_json(self, filename):
        (self._dirname/filename).write_text(json.dumps(self._data, ensure_ascii=False))

    def to_srt(self, filename, channel_id=0):
        path = self._dirname / filename
        data = filter(lambda x: x['ChannelId']==channel_id, self._data)
        pattern = '{h:02}:{m:02}:{s:02},{ms:03}'
        with open(str(path), 'w') as f:
            for ith, item in enumerate(sorted(data, key=lambda x: x['BeginTime'])):
                start, end = (self._time(item[k], pattern) for k in ('BeginTime', 'EndTime'))
                f.write(f'{ith}\n{start} --> {end}\n{item["Text"]}\n\n')

    def _trans(self, url, **kwargs):
        # 创建 AcsClient 实例
        self._client = AcsClient(
            config.access_key['id'], config.access_key['secret'], 'cn-shanghai',
        )
        # 提交录音文件识别请求
        request = self._request(get_or_post=False)
        task = dict(
            appkey=config.clound['app_key'], file_link=url, version='4.0',
            enable_words=True, enable_sample_rate_adaptive=True,
        )
        task.update(kwargs)
        request.add_body_params('Task', json.dumps(task))
        try:
            response = json.loads(self._client.do_action_with_exception(request))
            if response['StatusText'] == 'SUCCESS':
                return response['TaskId']
        except (ServerException, ClientException):
            pass

    def _polling(self, task_id, delay=10):
        # 创建 CommonRequest，设置任务 ID
        request = self._request(get_or_post=True)
        request.add_query_param('TaskId', task_id)
        # 提交录音文件识别结果查询请求
        while True:
            try:
                response = json.loads(self._client.do_action_with_exception(request))
                if response['StatusText'] not in ('RUNNING', 'QUEUEING'):
                    return response
                time.sleep(delay)
            except (ServerException, ClientException):
                pass

    def _request(self, get_or_post=True):
        # 'get' if get_or_post else 'post'
        request = CommonRequest()
        request.set_domain('filetrans.cn-shanghai.aliyuncs.com')
        request.set_version('2018-08-17')
        request.set_product('nls-filetrans')
        request.set_action_name('GetTaskResult' if get_or_post else 'SubmitTask')
        request.set_method('GET' if get_or_post else 'POST')
        return request

    def _time(self, microsecond, pattern='{h:02}:{m:02}:{s:02},{ms:03}'):
        def f(microsecond):
            for c in (1000, 60, 60, 60):
                yield microsecond % c
                microsecond //= c
        ms, s, m, h = f(microsecond)
        return pattern.format(ms=ms, s=s, m=m, h=h)


class Video:
    '''Bilibili video by (av or bv)
    '''
    def __init__(self, id, dirname=config.cache_dir):
        self._id = self._av_or_bv(id)
        self._dirname = pathlib.Path(dirname)
        self._dirname.mkdir(exist_ok=True)
        self._pages = self._get(state=True)['videoData']['pages']

    @property
    def id(self):
        return self._id

    @property
    def number(self):
        return len(self._pages)

    def audio(self, p=1, sr=0):
        '''
        Argument:
            - p: int
            - sr: int, sample rate
        '''
        old_path = self._dirname / f'{self._id}-{p}.m4s'
        new_path = self._dirname / f'{self._id}-{p}.mp3'
        if not new_path.exists():
            url = f'https://www.bilibili.com/video/av{self._id}?p={p}'
            base_url = self._get(playinfo=True, p=p)['data']['dash']['audio'][0]['base_url']
            old_path.write_bytes(
                requests.get(base_url, headers=self._headers(referer=url)).content
            )
            audio = pydub.AudioSegment.from_file(str(old_path))
            (audio.set_frame_rate(sr) if sr else audio).export(str(new_path), format='mp3')
            os.remove(str(old_path))
        return new_path.name

    def danmaku(self, session, text, microsecond, p=1, mode=1, color=0xffffff, fontsize=25):
        '''
        Argument:
            - session: requests.sessions.Session
            - text: str
            - microsecond: int
            - p: int
            - mode: int, {1: 滚动, 4: 底部, 5: 顶部}
            - color: int, 0xRRGGBB
            - fontsize: int, (18, 25)
        '''
        data = {
            'type': 1, 'pool': 0, 'plat': 1,
            'oid': next(page for page in self._pages if page['page']==p)['cid'],
            'msg': text, 'progress': microsecond, 'mode': mode, 'color': color,
            'fontsize': fontsize, 'bvid': av2bv(self._id),
            'rnd': int(1e6*time.time()), 'csrf': session.cookies.get('bili_jct', ''),
        }
        return session.post('https://api.bilibili.com/x/v2/dm/post', data=data).json()

    def _get(self, state=False, playinfo=False, p=1):
        url = f'https://www.bilibili.com/video/av{self._id}?p={p}'
        if state:
            pattern = r'__INITIAL_STATE__=(.*?);\(function'
        elif playinfo:
            pattern = r'__playinfo__=(.*?)</script><script>'
        else:
            raise Exception
        return json.loads(re.findall(pattern, requests.get(url).text)[0])

    def _av_or_bv(self, value):
        value = str(value)
        if value.isdigit():
            return int(value)
        elif value.startswith('BV'):
            return int(bv2av(value)[2:])
        elif value[:2] in ('av', 'AV'):
            return int(value[2:])
        else:
            raise Exception(f'Unknown pattern: "{value}"')

    def _headers(self, referer=None, cookie=None):
        # a reasonable UA
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 ' \
            '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
        headers = {'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'User-Agent': ua}
        if isinstance(referer, str):
            headers['Referer'] = referer
        if isinstance(cookie, str):
            headers['Cookie'] = cookie
        return headers


class Session:
    '''Bilibili Session model
    '''
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'host': 'api.bilibili.com',
            'referer': 'https://www.bilibili.com',
        })
        self.browser = None
        self._login = False

    @property
    def is_login(self):
        return self._login

    @classmethod
    def load(cls, path=config.pickle_path):
        data = pickle.loads(pathlib.Path(path).read_bytes())
        self = cls()
        self._login = data['login']
        self.session.headers = data['headers']
        self.session.cookies = data['cookies']
        return self

    def dump(self, path=config.pickle_path):
        data = dict(
            headers=self.session.headers,
            cookies=self.session.cookies,
            login=self._login,
        )
        pathlib.Path(path).write_bytes(pickle.dumps(data))
        return self

    def set_cookies(self, cookies):
        '''
        Argument:
            - cookies: dict
        '''
        self.session.cookies.update(cookies)

    def login_by_selenium(self, name='Firefox'):
        '''
        Argument:
            - name: str, selenium.webdriver.`name`
        '''
        if not self._login:
            self.browser = getattr(webdriver, name)()
            self.browser.get('https://passport.bilibili.com/login')
            input('Please login in >>> ')
            
            self.set_cookies({
                item['name']: item['value']
                for item in self.browser.get_cookies()
            })
            self._login = True
        return self
