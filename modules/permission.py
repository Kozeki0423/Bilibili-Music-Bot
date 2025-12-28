# modules/permission.py
# 权限验证和白名单管理模块

import json
import os
import hashlib
from datetime import datetime
from watchdog.events import FileSystemEventHandler

class PermissionManager:
    def __init__(self, config, whitelist_file="config/whitelist.json", fused_keys_file="data/fused_keys.json"):
        self.config = config
        self.whitelist_file = whitelist_file
        self.fused_keys_file = fused_keys_file
        self.admin_password = config.get("env_admin_password", "mysecret")
        self.default_admins = set(config.get("env_default_admins", ["磕磕绊绊学语文", "琴吹炒面"]))
        self.default_allowed_users = set(config.get("env_default_allowed_users", ["琴吹炒面"]))
        self.admins = self.default_admins.copy()
        self.allowed_users = set()
        
        # 限时开放点歌时间
        self.grant_until_time = 0  # Unix timestamp
        
        # 临时点歌次数 - 每人最多N首相关变量
        self.global_temp_grant_per_user = 0  # 每人可领取的次数（由 !grant -c N 设置）
        self.user_already_granted = set()    # 记录已领取过配额的用户名
        self.temp_grant_counts = {}          # 当前每个用户的剩余次数
        
        # 加载白名单
        self.load_whitelist()
    
    def load_whitelist(self):
        """从文件加载白名单"""
        try:
            if os.path.exists(self.whitelist_file):
                with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.allowed_users = set(data.get('allowed_users', []))
                return True
            else:
                # 如果文件不存在，使用默认值
                self.allowed_users = self.default_allowed_users.copy()
                # 确保config目录存在
                os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
                self.save_whitelist()
                print(f"创建新的白名单文件，使用默认值")
                return True
        except Exception as e:
            print(f"加载白名单失败: {e}")
            self.allowed_users = self.default_allowed_users.copy()
            return False
    
    def save_whitelist(self):
        """保存白名单到文件"""
        try:
            data = {
                'allowed_users': list(self.allowed_users),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            # 确保config目录存在
            os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
            with open(self.whitelist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"白名单已保存到 {self.whitelist_file}")
            return True
        except Exception as e:
            print(f"保存白名单失败: {e}")
            return False
    
    def add_user_to_whitelist(self, username):
        """添加用户到白名单"""
        if username not in self.allowed_users:
            self.allowed_users.add(username)
            self.save_whitelist()
            print(f"添加用户到白名单: {username}")
            return True
        else:
            print(f"用户已在白名单中: {username}")
            return False
    
    def remove_user_from_whitelist(self, username):
        """从白名单移除用户"""
        if username in self.allowed_users:
            self.allowed_users.remove(username)
            self.save_whitelist()
            print(f"从白名单移除用户: {username}")
            return True
        else:
            print(f"用户不在白名单中: {username}")
            return False
    
    def list_whitelist_users(self):
        """列出所有白名单用户"""
        return sorted(list(self.allowed_users))
    
    def has_permission(self, username):
        """检查用户是否有权限点歌"""
        return username in self.allowed_users
    
    def is_admin(self, username):
        """检查用户是否是管理员"""
        return username in self.admins
    
    def clear_whitelist(self):
        """清空白名单（仅保留管理员）"""
        self.allowed_users = self.admins.copy()
        self.save_whitelist()
        return True
    
    def generate_daily_key(self):
        """生成每日密钥"""
        import time
        today_date = time.strftime('%y%m%d%H', time.localtime())
        key_input = today_date + self.admin_password
        sha256_hash = hashlib.sha256(key_input.encode('utf-8')).hexdigest()
        return sha256_hash[:10]
    
    def load_fused_keys(self):
        """加载已使用的密钥"""
        if os.path.exists(self.fused_keys_file):
            with open(self.fused_keys_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('fused_keys', []))
        return set()
    
    def save_fused_key(self, key):
        """保存已使用的密钥"""
        fused_keys = self.load_fused_keys()
        fused_keys.add(key)
        # 确保data目录存在
        os.makedirs(os.path.dirname(self.fused_keys_file), exist_ok=True)
        with open(self.fused_keys_file, 'w', encoding='utf-8') as f:
            json.dump({'fused_keys': list(fused_keys)}, f, ensure_ascii=False, indent=2)
    
    def extract_alphanumeric(self, text):
        """提取字母数字字符"""
        import re
        return re.sub(r'[^a-zA-Z0-9]', '', text)
    
    def is_valid_admin_key(self, content):
        """验证管理员密钥"""
        alphanumeric_content = self.extract_alphanumeric(content)
        
        daily_key = self.generate_daily_key()
        
        if alphanumeric_content == daily_key:
            fused_keys = self.load_fused_keys()
            if daily_key in fused_keys:
                return False, "密钥已被使用过"
            return True, daily_key
        
        return False, "密钥不匹配"
    
    def add_admin(self, username):
        """添加管理员"""
        self.admins.add(username)
    
    def remove_admin(self, username):
        """移除管理员"""
        if username in self.admins and username not in self.default_admins:
            self.admins.remove(username)
            return True
        return False
    
    def get_admins(self):
        """获取管理员列表"""
        return list(self.admins)
    
    def grant_temp_access(self, grant_type, value):
        """授予临时访问权限"""
        if grant_type == "time":
            import time
            self.grant_until_time = time.time() + max(0, value)
            self.global_temp_grant_per_user = 0
            self.temp_grant_counts.clear()
            self.user_already_granted.clear()
        elif grant_type == "count":
            self.global_temp_grant_per_user = value
            self.grant_until_time = 0  # 关闭时间模式
            self.temp_grant_counts.clear()
            self.user_already_granted.clear()  # 重置，让所有人可以重新领取
    
    def revoke_temp_access(self, grant_type):
        """撤销临时访问权限"""
        if grant_type == "time":
            self.grant_until_time = 0
        elif grant_type == "count":
            self.global_temp_grant_per_user = 0
            self.temp_grant_counts.clear()
            self.user_already_granted.clear()
        elif grant_type == "all":
            self.grant_until_time = 0
            self.global_temp_grant_per_user = 0
            self.temp_grant_counts.clear()
            self.user_already_granted.clear()
    
    def check_user_temp_grant(self, username):
        """检查用户临时权限"""
        import time
        
        # 检查用户权限
        has_perm = (
            self.has_permission(username) or
            time.time() < self.grant_until_time
        )
        
        # 如果没有直接权限，尝试使用"每人最多N首"临时配额
        if not has_perm and self.global_temp_grant_per_user > 0:
            if username not in self.user_already_granted:
                # 首次领取：分配 N 次
                self.temp_grant_counts[username] = self.global_temp_grant_per_user
                self.user_already_granted.add(username)
                print(f"为 {username} 分配 {self.global_temp_grant_per_user} 次点歌权限")
            
            # 检查当前剩余次数
            if self.temp_grant_counts.get(username, 0) > 0:
                has_perm = True
        
        return has_perm
    
    def use_temp_grant(self, username):
        """使用临时权限（扣减次数）"""
        import time
        if (not self.has_permission(username) and
            self.grant_until_time <= time.time() and
            username in self.temp_grant_counts):
            self.temp_grant_counts[username] -= 1

# 白名单热重载处理器
class WhitelistReloadHandler(FileSystemEventHandler):
    def __init__(self, permission_manager):
        super().__init__()
        self.permission_manager = permission_manager
        self.last_reload_time = 0
        self.reload_cooldown = 1.0
    
    def on_modified(self, event):
        if event.src_path.endswith(self.permission_manager.whitelist_file):
            import time
            current_time = time.time()
            # 检查是否在冷却时间内
            if current_time - self.last_reload_time < self.reload_cooldown:
                return
            
            print("[SYS] Reloaded")
            self.permission_manager.load_whitelist()
            print(f"[SYS] 白名单用户数: {len(self.permission_manager.allowed_users)}")
            self.last_reload_time = current_time