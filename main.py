import os
import time
import tqdm

from mr_subtitle.config import pickle_path
from mr_subtitle.models import Video, Session, Subtitle


# step 1
print('导入哔哩哔哩登录信息')
if os.path.exists(pickle_path):
    session = Session.load(pickle_path)
else:
    session = Session().login_by_selenium('Chrome').dump(pickle_path)

# step 2
print('下载视频音频（默认 1p，可以根据 video.number 进行迭代）')
video = Video('BV12J411p7S7')
filename = video.audio(p=1)

# step 3
print('转换视频到文字，并按照字幕文件的格式存储')
subtitle = Subtitle()
subtitle.from_['audio'](filename)
subtitle.to['srt'](filename.replace('.mp3', '.srt'))

# step 4
print('手动修改字幕文件并覆盖原先记录')
while input('请手动修改字幕文件（y）') != 'y':
    pass
subtitle.from_['srt'](filename.replace('.mp3', '.srt'))

# step 5
print('根据字幕发送哔哩哔哩弹幕')
for item in tqdm.tqdm(subtitle.data):
    response = video.danmaku(
        session.session, item['Text'], item['BeginTime'],
        p=1, mode=1, color=0xcc0273,
    )
    print(item['BeginTime']/1000, item['Text'], response)
    time.sleep((item['EndTime']-item['BeginTime'])/1000)
