import keyboard
import json
import os
import time
import threading
import asyncio
from pynput import mouse

class HotkeyManager:
    def __init__(self, player, queue_manager):
        self.player = player
        self.queue_manager = queue_manager
        self.config_path = "config/hotkeys.json"
        self.config = self.load_config()
        self.is_paused = False  # 播放暂停状态
        self.is_running = True  # 程序运行状态
        
    def load_config(self):
        """加载配置文件，如果不存在则自动生成"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                print(f"[KEY] 快捷键配置已加载: {self.config_path}")
                return json.load(f)
        else:
            # 创建config目录
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            # 默认配置
            default_config = {
                "hotkey_skip": "alt+right",
                # "hotkey_prev": "alt+left", 
                "hotkey_play_pause": "alt+p",
                "hotkey_volume_up": "alt+up",
                "hotkey_volume_down": "alt+down"
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"[KEY] 快捷键配置文件已创建: {self.config_path}")
            print("[KEY] 请修改配置文件后重新启动程序")
            return default_config
    
    def skip_track(self):
        """跳过当前歌曲"""
        print("[KEY] 跳过当前歌曲")
        if self.player:
            # 在新线程中运行异步函数
            thread = threading.Thread(target=self._run_async_skip)
            thread.daemon = True
            thread.start()
    
    def _run_async_skip(self):
        """在新线程中运行跳过操作"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.player.skip())
        finally:
            loop.close()
    
    def prev_track(self):
        """切换上一首（从历史中恢复）"""
        print("[KEY] 切换上一首")
        if self.queue_manager:
            history = self.queue_manager.get_history(1)
            if history:
                # 获取历史中的第一首歌（最近播放的）
                prev_song = history[0]
                # 将当前播放的歌曲加入历史
                current_playing = self.player.get_current_playing()
                if current_playing:
                    self.queue_manager.add_to_history(current_playing)
                
                # 将上一首歌曲重新加入队列
                self.queue_manager.song_queue.put_nowait(prev_song)
                # 从历史中移除该歌曲
                if self.queue_manager.history:
                    self.queue_manager.history.pop()  # 移除最后一个元素
                
                print(f"[KEY] 已将 '{prev_song[1]}' 重新加入播放队列")
            else:
                print("[KEY] 没有历史记录可以退回")
    
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        # print(f"[KEY] 切换播放/暂停状态 (当前状态: {'暂停' if self.is_paused else '播放'})")
        if self.player:
            # 在新线程中运行异步函数
            if self.is_paused:
                thread = threading.Thread(target=self._run_async_resume)
                thread.daemon = True
                thread.start()
            else:
                thread = threading.Thread(target=self._run_async_pause)
                thread.daemon = True
                thread.start()
            self.is_paused = not self.is_paused
    
    def _run_async_pause(self):
        """在新线程中运行暂停操作"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.player.pause())
            print("[KEY] 暂停播放")
        finally:
            loop.close()
    
    def _run_async_resume(self):
        """在新线程中运行恢复操作"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.player.resume())
            print("[KEY] 恢复播放")
        finally:
            loop.close()
    
    def adjust_volume(self, delta):
        """调整音量"""
        if self.player:
            current_volume = self.player.get_volume()
            new_volume = max(0, min(100, current_volume + delta))
            # 在新线程中运行异步函数
            thread = threading.Thread(target=self._run_async_set_volume, args=(new_volume,))
            thread.daemon = True
            thread.start()
            print(f"[KEY] 音量调整: {current_volume} -> {new_volume}")
    
    def _run_async_set_volume(self, volume):
        """在新线程中运行设置音量操作"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.player.set_volume_async(volume))
        finally:
            loop.close()
    
    def setup_hotkeys(self):
        """设置快捷键"""
        # 读取配置中的快捷键设置
        skip_key = self.config.get("hotkey_skip", "alt+right")
        # prev_key = self.config.get("hotkey_prev", "alt+left")
        play_pause_key = self.config.get("hotkey_play_pause", "alt+p")
        volume_up_key = self.config.get("hotkey_volume_up", "alt+up")
        volume_down_key = self.config.get("hotkey_volume_down", "alt+down")
        
        # 注册快捷键
        keyboard.add_hotkey(skip_key, self.skip_track)
        # keyboard.add_hotkey(prev_key, self.prev_track)
        keyboard.add_hotkey(play_pause_key, self.toggle_play_pause)
        keyboard.add_hotkey(volume_up_key, lambda: self.adjust_volume(5))
        keyboard.add_hotkey(volume_down_key, lambda: self.adjust_volume(-5))
        
        print(f"[KEY] 已注册快捷键:")
        print(f"  - {skip_key}: 跳过当前歌曲")
        # print(f"  - {prev_key}: 切换上一首")
        print(f"  - {play_pause_key}: 播放/暂停")
        print(f"  - {volume_up_key}: 音量增加")
        print(f"  - {volume_down_key}: 音量减少")
    
    def start_listening(self):
        """开始监听快捷键"""
        print("[KEY] 开始监听快捷键...")
        self.setup_hotkeys()
        
        # 保持程序运行
        try:
            keyboard.wait('ctrl+shift+q')  # 按Ctrl+Shift+Q退出
        except KeyboardInterrupt:
            print("[KEY] 监听已停止")
    
    def stop_listening(self):
        """停止监听"""
        self.is_running = False
        keyboard.unhook_all()
        print("[KEY] 快捷键监听已停止")

# 如果直接运行此文件，启动测试
if __name__ == "__main__":
    print("快捷键监听器测试模式")
    print("注意：需要在main.py环境中运行才能与播放器通信")
    print("按 Ctrl+Shift+Q 退出")
    
    # 创建一个空的快捷键管理器用于测试
    hotkey_manager = HotkeyManager(None, None)
    hotkey_manager.start_listening()