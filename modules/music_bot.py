# modules/music_bot.py
# 网易云音乐API集成模块

import pyncm
from pyncm.apis import cloudsearch, track, playlist
import qrcode
import os
import time
import sys
from datetime import datetime

class MusicBot:
    def __init__(self, session_file="data/session.ncm", fallback_playlist_id=9162892605):
        self.session_file = session_file
        self.fallback_playlist_id = fallback_playlist_id
        self.login_netease()
    
    def login_netease(self):
        """登录网易云音乐"""
        print(f"[{'SYS':>3}] 初始化网易云登录...")
        
        # 尝试加载本地保存的 Session
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    pyncm.LoadSessionFromString(f.read())
                # 验证 Session 是否有效
                nickname = pyncm.GetCurrentSession().nickname
                if nickname != 'Guest':
                    print(f"[{'SYS':>3}] 自动登录成功! 欢迎回来: {nickname}")
                    return
                else:
                    print(f"[{'SYS':>3}] 本地缓存已失效，需要重新扫码。")
            except Exception as e:
                print(f"[{'SYS':>3}] 加载缓存失败: {e}")
        
        # 如果没有缓存或缓存失效，开始扫码
        try:
            # 确保data目录存在
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            uuid = pyncm.apis.login.LoginQrcodeUnikey()['unikey']
            login_url = f"https://music.163.com/login?codekey={uuid}"
            qr = qrcode.QRCode(border=1)
            qr.add_data(login_url)
            qr.print_ascii(invert=True)
            print(f"[{'SYS':>3}] 网易云APP扫码")
            while True:
                result = pyncm.apis.login.LoginQrcodeCheck(uuid)
                if result['code'] == 803:
                    # 确保 session 已绑定用户信息
                    try:
                        account = pyncm.apis.user.GetUserAccount()
                        nickname = account['profile']['nickname']
                    except Exception:
                        nickname = pyncm.GetCurrentSession().nickname or "未知用户"
                    try:
                        with open(self.session_file, 'w') as f:
                            f.write(pyncm.DumpSessionAsString(pyncm.GetCurrentSession()))
                        print(f"[{'SYS':>3}] 登录信息已保存到本地。")
                    except Exception as e:
                        print(f"[{'SYS':>3}] 保存登录信息失败(不影响本次运行): {e}")
                    break
                elif result['code'] == 800:
                    print(f"[{'SYS':>3}] 二维码过期，请重启程序")
                    sys.exit()
                time.sleep(2)
        except Exception as e:
            print(f"[{'SYS':>3}] 登录流程严重错误: {e}")
            sys.exit()
    
    def get_song_info(self, keyword_or_id):
        """获取歌曲信息"""
        try:
            if keyword_or_id.isdigit():
                res = track.GetTrackDetail(song_ids=[int(keyword_or_id)])
                if res.get('songs'):
                    s = res['songs'][0]
                    return s['id'], s['name'], s['ar'][0]['name']
            else:
                res = cloudsearch.GetSearchResult(keyword_or_id, limit=1)
                if res.get('result') and res['result'].get('songs'):
                    s = res['result']['songs'][0]
                    return s['id'], s['name'], s['ar'][0]['name']
        except Exception as e:
            print(f"[{'SYS':>3}] 搜索失败: {e}")
        return None, None, None
    
    def get_song_url(self, song_id):
        """获取歌曲播放链接"""
        try:
            res = track.GetTrackAudio(song_ids=[song_id], bitrate=320000)
            if res.get('data') and res['data'][0]['url']:
                return res['data'][0]['url']
            else:
                print(f"[{'SYS':>3}] ID:{song_id} 无播放链接 (版权/VIP)")
        except Exception as e:
            print(f"[{'SYS':>3}] 获取链接出错: {e}")
        return None
    
    def get_random_fallback_song(self):
        """获取随机播放歌单中的歌曲"""
        try:
            print(f"[{'SYS':>3}] 获取歌单 {self.fallback_playlist_id} ...")
            res = playlist.GetPlaylistInfo(self.fallback_playlist_id)
            if not res or res.get('code') != 200:
                print(f"[{'SYS':>3}] 获取歌单失败 Code: {res.get('code', 'Unknown')}")
                return None, None, None
            track_ids = [t['id'] for t in res['playlist']['trackIds']]
            if track_ids:
                import random
                random_id = random.choice(track_ids)
                return self.get_song_info(str(random_id))
            else:
                print(f"[{'SYS':>3}] 歌单为空")
        except Exception as e:
            print(f"[{'SYS':>3}] Err: {e}")
        return None, None, None