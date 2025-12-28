# modules/queue_manager.py
# 播放队列管理模块

import asyncio

class QueueManager:
    def __init__(self, maxsize=5):
        self.maxsize = maxsize
        self.song_queue = asyncio.Queue(maxsize=maxsize)
        self.history = []  # 播放历史
        self.max_history = 50
    
    async def add_song(self, song_item):
        """添加歌曲到队列，对网易云音乐进行ID查重"""
        # 检查是否为网易云音乐项目（3元组格式：sid, name, artist）
        if isinstance(song_item, tuple) and len(song_item) == 3:
            sid, name, artist = song_item
            # 对网易云音乐进行查重
            if self._is_song_duplicate(sid):
                return False, f"歌曲 '{name}' 已在队列中，无法重复添加"
        
        if self.song_queue.full():
            return False, "点歌队列已满，无法加入"
        
        await self.song_queue.put(song_item)
        return True, "入队成功"
    
    def _is_song_duplicate(self, song_id):
        """检查网易云音乐ID是否已在队列中"""
        # 创建一个临时队列来复制内容并检查
        temp_queue = asyncio.Queue()
        is_duplicate = False
        
        # 将原队列内容复制到临时队列并检查
        while not self.song_queue.empty():
            item = self.song_queue.get_nowait()
            # 检查是否为网易云音乐项目且ID相同
            if isinstance(item, tuple) and len(item) == 3:
                existing_sid, existing_name, existing_artist = item
                if existing_sid == song_id:
                    is_duplicate = True
                    break
            temp_queue.put_nowait(item)
        
        # 将临时队列内容复制回原队列
        while not temp_queue.empty():
            item = temp_queue.get_nowait()
            self.song_queue.put_nowait(item)
        
        return is_duplicate

    async def get_next_song(self):
        """获取下一首歌曲"""
        if self.song_queue.empty():
            return None
        return await self.song_queue.get()
    
    def is_empty(self):
        """检查队列是否为空"""
        return self.song_queue.empty()
    
    def is_full(self):
        """检查队列是否已满"""
        return self.song_queue.full()
    
    def size(self):
        """获取队列大小"""
        return self.song_queue.qsize()
    
    def get_queue_list(self):
        """获取队列中的所有项目（非阻塞）"""
        # 创建一个临时队列来复制内容
        temp_queue = asyncio.Queue()
        queue_list = []
        
        # 将原队列内容复制到临时队列
        while not self.song_queue.empty():
            item = self.song_queue.get_nowait()
            queue_list.append(item)
            temp_queue.put_nowait(item)
        
        # 将临时队列内容复制回原队列
        while not temp_queue.empty():
            item = temp_queue.get_nowait()
            self.song_queue.put_nowait(item)
        
        return queue_list
    
    async def remove_song_at_index(self, index):
        """删除指定位置的歌曲"""
        if index < 0 or index >= self.song_queue.qsize():
            return False, "索引超出队列范围"
        
        # 获取队列中的所有项目
        queue_list = self.get_queue_list()
        
        if index >= len(queue_list):
            return False, "索引超出队列范围"
        
        # 删除指定索引的项目
        removed_item = queue_list.pop(index)
        
        # 清空原队列并重新添加剩余项目
        while not self.song_queue.empty():
            self.song_queue.get_nowait()
        
        for item in queue_list:
            self.song_queue.put_nowait(item)
        
        return True, removed_item
    
    async def clear_queue(self):
        """清空队列"""
        cleared_count = 0
        while not self.song_queue.empty():
            await self.song_queue.get()
            cleared_count += 1
        return cleared_count
    
    def add_to_history(self, song_info):
        """添加到播放历史"""
        self.history.append(song_info)
        if len(self.history) > self.max_history:
            self.history.pop(0)  # FIFO
    
    def get_history(self, num=5):
        """获取播放历史"""
        return self.history[-num:] if self.history else []
    
    def remove_user_songs(self, username, log_file="data/requests.log"):
        """移除指定用户在队列中的所有歌曲"""
        queue_list = self.get_queue_list()
        user_songs_indices = []
        
        # 找到该用户在队列中的歌曲
        for i, item in enumerate(queue_list):
            if isinstance(item, tuple) and len(item) == 3:
                # 这是一个音乐项
                sid, name, artist = item
                # 通过日志判断这首歌是否是该用户点的
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if f"[{username}]：" in line and name in line:
                                user_songs_indices.append(i)
                                break
                except:
                    pass
            else:
                # 这是一个视频项
                video_id = item
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if f"[{username}]：" in line and str(video_id) in line:
                                user_songs_indices.append(i)
                                break
                except:
                    pass
        
        # 从队列中删除该用户的所有歌曲
        if user_songs_indices:
            new_queue_items = []
            for i, item in enumerate(queue_list):
                if i not in user_songs_indices:
                    new_queue_items.append(item)
            
            # 清空原队列
            while not self.song_queue.empty():
                self.song_queue.get_nowait()
            
            # 重新放入非该用户的歌曲
            for item in new_queue_items:
                self.song_queue.put_nowait(item)
            
            return len(user_songs_indices)
        
        return 0