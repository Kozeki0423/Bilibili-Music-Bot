# modules/logger.py
# 日志记录系统模块

import os
import json
from datetime import datetime

class Logger:
    def __init__(self, log_file="data/requests.log"):
        self.log_file = log_file
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """确保日志文件目录存在"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def log_request(self, username, song_name, artist):
        """记录点歌请求"""
        timestamp = datetime.now().strftime('%Y:%m:%d][%H:%M:%S')
        log_entry = f"[{timestamp}] [{username}]： {song_name} - {artist}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def log_video_request(self, username, video_id):
        """记录视频请求"""
        timestamp = datetime.now().strftime('%Y:%m:%d][%H:%M:%S')
        log_entry = f"[{timestamp}] [{username}]： 视频 - {video_id}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def get_user_requests(self, username, limit=5):
        """获取指定用户的历史请求"""
        records = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if f"[{username}]：" in line:
                        try:
                            song_info = line.split(']： ', 1)[1].strip()
                            records.append(song_info)
                        except:
                            continue
            return records[-limit:] if records else []
        except Exception as e:
            print(f"查询用户请求失败: {e}")
            return []
    
    def get_total_user_requests(self, username):
        """获取指定用户的总请求数"""
        count = 0
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if f"[{username}]：" in line:
                        count += 1
            return count
        except Exception as e:
            print(f"查询用户请求数失败: {e}")
            return 0
    
    def get_recent_requests(self, limit=10):
        """获取最近的请求记录"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return lines[-limit:] if lines else []
        except Exception as e:
            print(f"获取最近请求失败: {e}")
            return []
    
    def clear_log(self):
        """清空日志文件"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write('')
            return True
        except Exception as e:
            print(f"清空日志失败: {e}")
            return False
    
    def get_log_size(self):
        """获取日志文件大小"""
        try:
            return os.path.getsize(self.log_file)
        except:
            return 0

class HistoryManager:
    def __init__(self, max_history=50):
        self.max_history = max_history
        self.play_history = []  # [(sid, name, artist, timestamp), ...]
    
    def add_to_history(self, sid, name, artist):
        """添加播放记录到历史"""
        self.play_history.append((sid, name, artist, datetime.now().isoformat()))
        if len(self.play_history) > self.max_history:
            self.play_history.pop(0)  # FIFO
    
    def get_history(self, num=5):
        """获取播放历史"""
        return self.play_history[-num:] if self.play_history else []
    
    def clear_history(self):
        """清空播放历史"""
        self.play_history.clear()
    
    def get_history_count(self):
        """获取历史记录总数"""
        return len(self.play_history)