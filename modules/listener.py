# modules/listener.py
# B站直播间监听模块

import aiohttp
from datetime import datetime
import asyncio
import html

class BilibiliListener:
    def __init__(self, room_id, callback, poll_interval=5):
        self.room_id = room_id
        self.api_url = 'http://api.live.bilibili.com/ajax/msg'
        self.interval = poll_interval
        self.callback = callback
        self.isRunning = False
        self.last_check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.msg_cache = set()
    
    async def start(self):
        """开始监听B站直播间"""
        self.isRunning = True
        print(f"[{'SYS':>3}] 监听直播间: {self.room_id}")
        async with aiohttp.ClientSession() as session:
            while self.isRunning:
                await self.fetch_barrage(session)
                await asyncio.sleep(self.interval)
    
    async def fetch_barrage(self, session):
        """获取直播间弹幕"""
        try:
            params = {'roomid': self.room_id}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            async with session.get(self.api_url, params=params, headers=headers) as resp:
                if resp.status != 200: return
                data = await resp.json()
                if data['code'] != 0: return
                room_msgs = data.get('data', {}).get('room', [])
                new_msgs = []
                for msg in room_msgs:
                    msg_time = msg['timeline']
                    msg_content = html.unescape(msg['text']).strip()
                    unique_key = f"{msg_time}-{msg_content}-{msg['nickname']}"
                    if unique_key not in self.msg_cache:
                        if msg_time > self.last_check_time:
                            new_msgs.append({
                                'text': msg_content,
                                'nickname': msg['nickname'],
                                'timeline': msg_time
                            })
                            self.msg_cache.add(unique_key)
                if new_msgs:
                    self.last_check_time = new_msgs[-1]['timeline']
                    if len(self.msg_cache) > 200: self.msg_cache.clear()
                    for m in new_msgs:
                        await self.callback(m)
        except Exception as e:
            print(f"[{'SYS':>3}] 轮询出错: {e}")