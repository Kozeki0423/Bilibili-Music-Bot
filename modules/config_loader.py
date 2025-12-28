# modules/config_loader.py
# 配置文件管理模块

import json
import os
from watchdog.events import FileSystemEventHandler

class ConfigLoader:
    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.default_config = {
            "env_roomid": 1896163590,
            "env_poll_interval": 5,
            "env_playlist": 9162892605,
            "env_mpv_path": "mpv",
            "env_session_file": "data/session.ncm",
            "env_whitelist_file": "config/whitelist.json",
            "env_default_allowed_users": ["琴吹炒面"],
            "env_default_admins": ["磕磕绊绊学语文", "琴吹炒面"],
            "env_queue_maxsize": 5,
            "env_log_file": "data/requests.log",
            "env_admin_password": "mysecret",
            "env_alpha": 1.0,  # 保留原始键名，但对外显示为ALPHA
            "enable_video_playback": True,  
            "env_video_timeout_buffer": 3,  
            "enable_fallback_playlist": True,
            "env_unorthodox": False  # 新增：启用非正统音乐源功能
        }
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            # 创建config目录
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.default_config, f, indent=4, ensure_ascii=False)
            print(f"[SYS] 配置文件已创建: {self.config_path}")
            print("[SYS] 请修改配置文件后重新启动程序")
            return self.default_config
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            print(f"[SYS] {self.config_path} 已加载")
            return json.load(f)
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config[key] = value
    
    def save_config(self):
        """保存配置到文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def update_config(self, updates):
        """批量更新配置"""
        self.config.update(updates)
        self.save_config()

# 配置热重载处理器
class ConfigReloadHandler(FileSystemEventHandler):
    def __init__(self, config_loader, callback=None):
        super().__init__()
        self.config_loader = config_loader
        self.callback = callback
        self.last_reload_time = 0
        self.reload_cooldown = 1.0
    
    def on_modified(self, event):
        if event.src_path.endswith(self.config_loader.config_path):
            import time
            current_time = time.time()
            # 检查是否在冷却时间内
            if current_time - self.last_reload_time < self.reload_cooldown:
                return
            
            # 重新加载配置
            try:
                with open(self.config_loader.config_path, 'r', encoding='utf-8') as f:
                    new_config = json.load(f)
                self.config_loader.config = new_config
            except Exception as e:
                print(f"[SYS] 重新加载配置失败: {e}")
                return
            
            if self.callback:
                self.callback(self.config_loader.config)
            
            print("[SYS] 配置已热重载")
            self.last_reload_time = current_time

def load_preset_config(preset_path="config/preset.json"):
    """加载预设配置文件"""
    if not os.path.exists(preset_path):
        # 创建预设配置文件的默认内容
        os.makedirs(os.path.dirname(preset_path), exist_ok=True)
        default_presets = {}
        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(default_presets, f, indent=2, ensure_ascii=False)
        print(f"[SYS] 预设配置文件已创建: {preset_path}")
        return default_presets
    
    with open(preset_path, 'r', encoding='utf-8') as f:
        print(f"[SYS] {preset_path} 已加载")
        return json.load(f)

def save_preset_config(presets, preset_path="config/preset.json"):
    """保存预设配置到文件"""
    os.makedirs(os.path.dirname(preset_path), exist_ok=True)
    with open(preset_path, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)
    print(f"[SYS] 预设配置已保存到 {preset_path}")