# coding: utf-8
import asyncio
import sys
import time
import random
import subprocess
import os 
import importlib
import html
import json
import re
import hashlib
from datetime import datetime
import threading
import platform
import tempfile

def check_and_install_requirements():
    """检查并安装所需的依赖包"""
    required_packages = {
        'aiohttp': 'aiohttp==3.8.5',
        'pyncm': 'pyncm==2.2.1',
        'qrcode': 'qrcode==7.4.2',
        'PIL': 'pillow==9.5.0',
        'watchdog': 'watchdog==3.0.0'  # 新增热重载依赖
    }
    
    # 为 Windows 平台添加 pywin32
    if platform.system() == "Windows":
        required_packages['win32file'] = 'pywin32>=306'
        required_packages['pywintypes'] = 'pywin32>=306'

    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        if import_name == 'tkinter':
            try:
                import tkinter
            except ImportError:
                print("警告: tkinter 未找到，GUI 功能可能不可用。")
        elif import_name in ['win32file', 'pywintypes']:
            try:
                importlib.import_module(import_name)
            except ImportError:
                if package_name and 'pywin32' in missing_packages:
                    continue
                elif package_name:
                    if 'pywin32' not in missing_packages:
                        missing_packages.append(package_name)
        else:
            try:
                importlib.import_module(import_name)
            except ImportError:
                if package_name:
                    missing_packages.append(package_name)
    
    # 去重并保留第一个 pywin32 相关项
    final_missing = []
    seen_pywin32 = False
    for pkg in missing_packages:
        if 'pywin32' in pkg:
            if not seen_pywin32:
                final_missing.append(pkg)
                seen_pywin32 = True
        else:
            final_missing.append(pkg)

    if final_missing:
        print(f"检测到缺失的依赖包: {', '.join(final_missing)}")
        print("自动安装依赖包...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + final_missing)
            print("依赖包安装完成")
        except subprocess.CalledProcessError as e:
            print(f"依赖包安装失败: {e}")
            print("请手动执行: pip install " + " ".join(final_missing))
            sys.exit(1)
    else:
        print("环境配置完成")

# 检查并安装依赖
check_and_install_requirements()

import aiohttp
import pyncm
from pyncm.apis import cloudsearch, track, playlist
import qrcode 
import tkinter as tk
from tkinter import scrolledtext
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def load_config():
    config_path = "config/config.json"
    default_config = {
        "env_roomid": 1896163590,
        "env_poll_interval": 5,
        "env_playlist": 9162892605,
        "env_mpv_path": "mpv",
        "env_session_file": "data/session.ncm",
        "env_whitelist_file": "config/whitelist.json",
        "env_default_allowed_users": ["琴吹炒面"],
        "env_default_admins": ["琴吹炒面"],
        "env_queue_maxsize": 5,
        "env_log_file": "data/requests.log",
        "env_admin_password": "mysecret",
        "env_alpha": 1.0  # 新增透明度配置
    }
    if not os.path.exists(config_path):
        # 创建config目录
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print(f"配置文件已创建: {config_path}")
        print("请修改配置文件后重新启动程序")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        print(f"{config_path} 已加载")
        return json.load(f)
        
config = load_config()

# ENV
ROOM_ID = config.get("env_roomid", 1896163590)
POLL_INTERVAL = config.get("env_poll_interval", 5)
FALLBACK_PLAYLIST_ID = config.get("env_playlist", 9162892605) 
SESSION_FILE = config.get("env_session_file", "data/session.ncm") # 登录信息
WHITELIST_FILE = config.get("env_whitelist_file", "config/whitelist.json") # 白名单文件
QUEUE_MAXSIZE = config.get("env_queue_maxsize", 5)
LOG_FILE = config.get("env_log_file", "data/requests.log") 
ADMIN_PASSWORD = config.get("env_admin_password", "Kozeki_Ui")

# root
ADMINS = set(config.get("env_default_admins", ["琴吹炒面"]))

# 初始用户白名单
DEFAULT_ALLOWED_USERS = set(config.get("env_default_allowed_users", ["琴吹炒面"]))

# 熔断状态文件
FUSED_KEYS_FILE = "data/fused_keys.json"

# 全局播放队列，最大长度为5
song_queue = asyncio.Queue(maxsize=5)

# 播放历史记录
MAX_HISTORY = 50
play_history = []  # [(sid, name, artist, timestamp), ...]

# 当前播放歌曲
current_playing = None  # (sid, name, artist)

# 限时开放点歌时间
grant_until_time = 0  # Unix timestamp

# 临时点歌次数 - 每人最多N首相关变量
global_temp_grant_per_user = 0  # 每人可领取的次数（由 !grant -c N 设置）
user_already_granted = set()    # 记录已领取过配额的用户名
temp_grant_counts = {}          # 当前每个用户的剩余次数

# 日志
def log_successful_request(username, song_name, artist):
    """记录成功的点歌请求到日志文件"""
    timestamp = datetime.now().strftime('%Y:%m:%d][%H:%M:%S')
    log_entry = f"[{timestamp}] [{username}]： {song_name} - {artist}\n"
    # 确保data目录存在
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# MPV路径获取
def get_mpv_path():
    """
    自动获取MPV路径，默认为代码所在根目录下的mpv
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检测操作系统类型
    if platform.system() == "Windows":
        # Windows平台，查找mpv.exe
        local_mpv_paths = [
            os.path.join(current_dir, "mpv", "mpv.exe"),  # 根目录/mpv/
            os.path.join(current_dir, "mpv.exe"),         # 根目录/
            os.path.join(current_dir, "player", "mpv.exe") # 根目录/player/
        ]
        for path in local_mpv_paths:
            if os.path.exists(path):
                print(f"找到本地MPV播放器: {path}")
                return path
    else:
        # Unix-like系统，查找mpv可执行文件
        local_mpv_paths = [
            os.path.join(current_dir, "mpv"),           # 根目录/mpv (Unix可执行文件)
            os.path.join(current_dir, "mpv", "mpv"),   # 根目录/mpv/mpv
            os.path.join(current_dir, "./mpv"),         # 根目录/./mpv
        ]
        for path in local_mpv_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                print(f"找到本地MPV播放器: {path}")
                return path
    
    # 如果没有找到本地MPV，则返回配置文件中的路径或默认路径
    config_mpv_path = config.get("env_mpv_path", "mpv")
    print(f"未找到本地MPV，使用配置路径: {config_mpv_path}")
    return config_mpv_path

# 获取MPV路径
MPV_PATH = get_mpv_path()
print(f"[DEBUG] MPV_PATH = {repr(MPV_PATH)}")
print(f"[DEBUG] Path exists? {os.path.exists(MPV_PATH) if MPV_PATH else False}")

# 白名单管理器
class WhitelistManager:
    def __init__(self, filename=WHITELIST_FILE):
        self.filename = filename
        self.allowed_users = set()
        self.load_whitelist()
    def load_whitelist(self):
        """从文件加载白名单"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.allowed_users = set(data.get('allowed_users', []))
                # print(f"从文件加载白名单成功，共 {len(self.allowed_users)} 个用户")
                return True
            else:
                # 如果文件不存在，使用默认值
                self.allowed_users = DEFAULT_ALLOWED_USERS.copy()
                # 确保config目录存在
                os.makedirs(os.path.dirname(self.filename), exist_ok=True)
                self.save_whitelist()
                print(f"创建新的白名单文件，使用默认值")
                return True
        except Exception as e:
            print(f"加载白名单失败: {e}")
            self.allowed_users = DEFAULT_ALLOWED_USERS.copy()
            return False
    def save_whitelist(self):
        """保存白名单到文件"""
        try:
            data = {
                'allowed_users': list(self.allowed_users),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            # 确保config目录存在
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"白名单已保存到 {self.filename}")
            return True
        except Exception as e:
            print(f"保存白名单失败: {e}")
            return False
    def add_user(self, username):
        """添加用户到白名单"""
        if username not in self.allowed_users:
            self.allowed_users.add(username)
            self.save_whitelist()
            print(f"添加用户到白名单: {username}")
            return True
        else:
            print(f"用户已在白名单中: {username}")
            return False
    def remove_user(self, username):
        """从白名单移除用户"""
        if username in self.allowed_users:
            self.allowed_users.remove(username)
            self.save_whitelist()
            print(f"从白名单移除用户: {username}")
            return True
        else:
            print(f"用户不在白名单中: {username}")
            return False
    def list_users(self):
        """列出所有白名单用户"""
        return sorted(list(self.allowed_users))
    def has_permission(self, username):
        """检查用户是否有权限点歌"""
        return username in self.allowed_users
    def clear_all(self):
        """清空白名单（仅保留管理员）"""
        self.allowed_users = ADMINS.copy()
        self.save_whitelist()
        return True

# 创建实例
whitelist_manager = WhitelistManager()

# 白名单热重载处理器
class WhitelistReloadHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_reload_time = 0
        self.reload_cooldown = 1.0
    
    def on_modified(self, event):
        if event.src_path.endswith(WHITELIST_FILE):
            current_time = time.time()
            # 检查是否在冷却时间内
            if current_time - self.last_reload_time < self.reload_cooldown:
                return
            
            print("[SYS] Reloaded")
            whitelist_manager.load_whitelist()
            print(f"[SYS] 白名单用户数: {len(whitelist_manager.allowed_users)}")
            self.last_reload_time = current_time

# 全局变量用于控制播放
current_mpv_process = None
mpv_ipc_path = None
current_volume = 100  # 默认音量

async def send_mpv_command(command):
    """向 MPV 发送 IPC 命令"""
    global mpv_ipc_path, current_mpv_process
    if not mpv_ipc_path or not current_mpv_process or current_mpv_process.returncode is not None:
        print(f"[{'SYS':>3}] MPV 未运行，无法发送命令")
        return False

    try:
        if platform.system() == "Windows":
            # Windows 使用命名管道
            import win32file, win32pipe, pywintypes
            try:
                handle = win32file.CreateFile(
                    mpv_ipc_path,
                    win32file.GENERIC_WRITE,
                    0, None,
                    win32file.OPEN_EXISTING,
                    0, None
                )
                win32file.WriteFile(handle, (command + '\n').encode('utf-8'))
                win32file.CloseHandle(handle)
                return True
            except pywintypes.error as e:
                print(f"[{'SYS':>3}] IPC 写入失败: {e}")
                return False
        else:
            # Unix-like 使用 Unix socket
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(mpv_ipc_path)
                sock.sendall((command + '\n').encode('utf-8'))
                sock.close()
                return True
            except Exception as e:
                print(f"[{'SYS':>3}] IPC 连接失败: {e}")
                return False
    except Exception as e:
        print(f"[{'SYS':>3}] 发送 MPV 命令出错: {e}")
        return False

# 播放器后台任务
async def player_worker():
    global current_mpv_process, mpv_ipc_path, current_volume, current_playing
    print(f"[{'SYS':>3}] 播放引擎就绪...")
    
    # 创建临时 IPC 路径
    if platform.system() == "Windows":
        mpv_ipc_path = r'\\.\pipe\mpv-kozeki'
    else:
        mpv_ipc_path = f"/tmp/mpv-kozeki-{os.getpid()}.sock"
        if os.path.exists(mpv_ipc_path):
            os.unlink(mpv_ipc_path)

    while True:
        try:
            if song_queue.empty():
                print(f"[{'SYS':>3}] 无请求，随机播放歌单...")
                song_item = music_bot.get_random_fallback_song()
                if not song_item or not song_item[0]:
                    print(f"[{'SYS':>3}] 获取失败，10秒后重试...")
                    await asyncio.sleep(10)
                    continue
            else:
                print(f"[{'SYS':>3}] 准备播放点歌 (剩余: {song_queue.qsize()})...")
                song_item = await song_queue.get()

            sid, name, artist = song_item
            current_playing = (sid, name, artist)  # 更新当前播放
            print(f"[{'SYS':>3}] 正在解析: {name} - {artist}")
            mp3_url = music_bot.get_song_url(sid)
            if not mp3_url:
                print(f"[{'SYS':>3}] 解析失败 跳过")
                current_playing = None
                continue

            print(f"[{'SYS':>3}] 启动 MPV: {name}")

            # 构建 MPV 参数
            mpv_args = [
                MPV_PATH,
                '--no-video',
                '--idle=no',
                f'--input-ipc-server={mpv_ipc_path}',
                f'--volume={current_volume}',  # 设置当前音量
                '--msg-level=all=no',  # 减少日志
                mp3_url
            ]

            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW

            current_mpv_process = await asyncio.create_subprocess_exec(
                *mpv_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags
            )

            await current_mpv_process.wait()
            print(f"[{'SYS':>3}] 播放结束: {name}")
            
            # 记录到历史
            play_history.append((sid, name, artist, datetime.now().isoformat()))
            if len(play_history) > MAX_HISTORY:
                play_history.pop(0)  # FIFO
            
            current_mpv_process = None
            current_playing = None

            await asyncio.sleep(1)
        except FileNotFoundError:
            print(f"[{'SYS':>3}] 找不到 MPV 播放器: {MPV_PATH}")
            print(f"[{'SYS':>3}] 请确保 MPV 播放器已正确安装或放置在程序根目录下的 'mpv' 文件夹中")
            await asyncio.sleep(10)
        except Exception as e:
            print(f"[{'SYS':>3}] 播放引擎错误: {e}")
            current_mpv_process = None
            current_playing = None
            await asyncio.sleep(5)

# B站 HTTP 轮询模块
class BilibiliHttpMonitor:
    def __init__(self, room_id, callback):
        self.room_id = room_id
        self.api_url = 'http://api.live.bilibili.com/ajax/msg'
        self.interval = POLL_INTERVAL
        self.callback = callback
        self.isRunning = False
        self.last_check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.msg_cache = set()
    async def start(self):
        self.isRunning = True
        print(f"[{'SYS':>3}] 监听直播间: {self.room_id}")
        async with aiohttp.ClientSession() as session:
            while self.isRunning:
                await self.fetch_barrage(session)
                await asyncio.sleep(self.interval)
    async def fetch_barrage(self, session):
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
                    msg_content = msg['text']
                    unique_key = f"{msg_time}-{msg_content}-{msg['nickname']}"
                    if unique_key not in self.msg_cache:
                        if msg_time > self.last_check_time:
                            new_msgs.append(msg)
                            self.msg_cache.add(unique_key)
                if new_msgs:
                    self.last_check_time = new_msgs[-1]['timeline']
                    if len(self.msg_cache) > 200: self.msg_cache.clear()
                    for m in new_msgs:
                        await self.callback(m)
        except Exception as e:
            print(f"[{'SYS':>3}] 轮询出错: {e}")

# 网易云音乐逻辑
class MusicBot:
    def __init__(self):
        self.login_netease()
    def login_netease(self):
        print(f"[{'SYS':>3}] 初始化网易云登录...")
        # 1. 尝试加载本地保存的 Session（废弃）
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
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
        
        # 2. 如果没有缓存或缓存失效，开始扫码
        try:
            # 确保data目录存在
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
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
                        with open(SESSION_FILE, 'w') as f:
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
        try:
            print(f"[{'SYS':>3}] 获取歌单 {FALLBACK_PLAYLIST_ID} ...")
            res = playlist.GetPlaylistInfo(FALLBACK_PLAYLIST_ID)
            if not res or res.get('code') != 200:
                print(f"[{'SYS':>3}] 获取歌单失败 Code: {res.get('code', 'Unknown')}")
                return None, None, None
            track_ids = [t['id'] for t in res['playlist']['trackIds']]
            if track_ids:
                random_id = random.choice(track_ids)
                return self.get_song_info(str(random_id))
            else:
                print(f"[{'SYS':>3}] 歌单为空")
        except Exception as e:
            print(f"[{'SYS':>3}] Err: {e}")
        return None, None, None

music_bot = MusicBot()

def generate_daily_key():
    today_date = datetime.now().strftime('%y%m%d%H')
    key_input = today_date + ADMIN_PASSWORD
    sha256_hash = hashlib.sha256(key_input.encode('utf-8')).hexdigest()
    return sha256_hash[:10]

def load_fused_keys():
    if os.path.exists(FUSED_KEYS_FILE):
        with open(FUSED_KEYS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('fused_keys', []))
    return set()

def save_fused_key(key):
    fused_keys = load_fused_keys()
    fused_keys.add(key)
    # 确保data目录存在
    os.makedirs(os.path.dirname(FUSED_KEYS_FILE), exist_ok=True)
    with open(FUSED_KEYS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'fused_keys': list(fused_keys)}, f, ensure_ascii=False, indent=2)

def extract_alphanumeric(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text)

def is_valid_admin_key(content):
    alphanumeric_content = extract_alphanumeric(content)
    
    daily_key = generate_daily_key()
    
    if alphanumeric_content == daily_key:
        fused_keys = load_fused_keys()
        if daily_key in fused_keys:
            return False, "密钥已被使用过"
        return True, daily_key
    
    return False, "密钥不匹配"

# 输出格式化函数
def format_output(prefix, user_name, content):
    """格式化输出，使前缀对齐"""
    return f"[{prefix:>3}] {user_name}: {content}"

def format_system_output(content):
    """格式化系统输出"""
    return f"[{'SYS':>3}] {content}"

def format_admin_output(user_name, content):
    """格式化管理员输出"""
    return f"[{'ADM':>3}] {user_name}: {content}"

def format_group_output(user_name, content):
    """格式化白名单用户输出"""
    return f"[{'GRP':>3}] {user_name}: {content}"

def format_user_output(user_name, content):
    """格式化普通用户输出"""
    return f"[{'USR':>3}] {user_name}: {content}"

def format_denied_output(user_name, content):
    """格式化权限拒绝输出"""
    return f"[{'DNY':>3}] {user_name}: {content}"

# 命令处理器
class CommandHandler:
    @staticmethod
    def is_admin(user_name):
        """检查用户是否是管理员"""
        return user_name in ADMINS
    
    @staticmethod
    async def handle_command(user_name, command_text):
        """处理命令"""
        if not command_text.startswith('!'):
            return None
        # 检查是否是管理员
        if not CommandHandler.is_admin(user_name):
            print(format_denied_output(user_name, f"{command_text}"))
            return None
        # 解析命令
        parts = command_text.split()
        cmd = parts[0].lower()
        global current_volume, grant_until_time, global_temp_grant_per_user, user_already_granted, temp_grant_counts  # 引用全局音量变量
        try:
            if cmd == '!touch' and len(parts) >= 2:
                username = parts[1]
                if whitelist_manager.add_user(username):
                    return f"已添加 '{username}' 到白名单"
                else:
                    return f" '{username}' 已在白名单中"
            elif cmd == '!rm' and len(parts) >= 2:
                username = parts[1]
                if whitelist_manager.remove_user(username):
                    return f"已从白名单移除  '{username}'"
                else:
                    return f" '{username}' 不在白名单中"
            elif cmd == '!cat': 
                users = whitelist_manager.list_users()
                if users:
                    user_list = ", ".join(users[:10]) 
                    if len(users) > 10:
                        user_list += f" ... 等{len(users)}个用户"
                    return f"白名单用户 ({len(users)}人): {user_list}"
                else:
                    return "白名单为空"
            elif cmd == '!clr':
                whitelist_manager.clear_all()
                return "白名单已清空，仅保留管理员"
            elif cmd == '!time':
                # !time 命令实现
                if len(parts) == 1:
                    # !time 无参数，输出时间部分
                    current_time = datetime.now().strftime('%y%m%d%H')
                    return f"{current_time}"
                elif len(parts) == 2 and parts[1] == '-h':
                    # !time -h 输出人类可读形式
                    current_time_readable = datetime.now().strftime('%Y/%m/%d %H时')
                    return f"当前时间: {current_time_readable}"
                else:
                    return "无效的time命令参数，使用 !help 查看帮助"
            elif cmd == '!help':
                help_text = """
~
┌──────────────────────
│ [音乐播放控制]
├──────────────────────
│ !pause         - 暂停播放
│ !resume        - 恢复播放
│ !skip          - 跳过当前歌曲
│ !vol <0-100>   - 设置音量
│ !vol           - 查询当前音量
│ !now           - 显示当前播放
│ !history {num} - 显示最近播放

┌──────────────────────
│ [播放队列管理]
├──────────────────────
│ !queue         - 显示当前队列
│ !queue ls      - 显示当前队列
│ !queue add ... - 添加歌曲
│ !queue del N   - 删除第N首
│ !queue clr     - 清除队列

┌──────────────────────
│ [白名单管理]
├──────────────────────
│ !touch user    - 加入白名单
│ !rm user       - 移出白名单
│ !cat           - 查看白名单
│ !clr           - 清空白名单

┌──────────────────────
│ [点歌权限控制]
├──────────────────────
│ !grant         - 开放所有人点歌权限
│ !grant -t SEC  - 开放SEC秒权限
│ !grant -c NUM  - 开放NUM次权限
│ !revoke -c     - 收回次数权限
│ !revoke -t     - 收回时间权限
│ !revoke        - 收回所有权限

┌──────────────────────
│ [用户数据查询]
├──────────────────────
│ !stats user    - 查询点歌记录

┌──────────────────────
│ [时间查询]
├──────────────────────
│ !time          - 获取当前时间
│ !time -h       - 获取当前时间

┌──────────────────────
│ [其他]
├──────────────────────
│ !help          - 显示本帮助

 点歌：song name / id  - 点播歌曲
                """
                return help_text.strip()
            elif cmd == '!pause':
                await send_mpv_command('set pause yes')
                return "已暂停播放"
            elif cmd == '!resume':
                await send_mpv_command('set pause no')
                return "已恢复播放"
            elif cmd == '!skip':
                if current_mpv_process and current_mpv_process.returncode is None:
                    await send_mpv_command('quit')
                    return "已跳过当前歌曲"
                else:
                    return "当前无播放中的歌曲"
            elif cmd == '!vol':
                if len(parts) < 2:
                    # 查询当前音量
                    return f"当前音量: {current_volume}"
                else:
                    # 设置音量
                    try:
                        vol = int(parts[1])
                        if 0 <= vol <= 100:
                            current_volume = vol  # 更新全局音量
                            if current_mpv_process and current_mpv_process.returncode is None:
                                # 如果当前有播放进程，发送命令更新音量
                                await send_mpv_command(f'set volume {vol}')
                            return f"音量已设为 {vol}"
                        else:
                            return "音量范围必须是 0-100"
                    except ValueError:
                        return "音量必须是整数"
            elif cmd == '!queue':
                # 检查是否有子命令
                if len(parts) < 2:
                    # !queue 或 !queue ls
                    return await CommandHandler._get_queue_status()
                else:
                    sub_cmd = parts[1].lower()
                    if sub_cmd == 'ls':
                        # !queue ls
                        return await CommandHandler._get_queue_status()
                    elif sub_cmd == 'add' and len(parts) >= 3:
                        # !queue add 歌名或id
                        query = ' '.join(parts[2:])
                        return await CommandHandler._queue_add(query)
                    elif sub_cmd == 'del' and len(parts) == 3:
                        # !queue del <1-5>
                        try:
                            index = int(parts[2])
                            return await CommandHandler._queue_del(index)
                        except ValueError:
                            return f"无效的歌曲序号，请输入1-{QUEUE_MAXSIZE}之间的数字"
                    elif sub_cmd == 'clr':
                        # !queue clr
                        return await CommandHandler._queue_clr()
                    else:
                        return f"未知的 queue 子命令: {' '.join(parts[1:])}，使用 !help 查看帮助"
            elif cmd == '!history':
                try:
                    # 修改这里：当没有传入参数时，默认为5
                    num = int(parts[1]) if len(parts) > 1 else 5
                    num = min(max(num, 1), len(play_history))
                    lines = ["最近播放:"]
                    for sid, name, artist, ts in reversed(play_history[-num:]):
                        lines.append(f"{name} - {artist}")
                    return "\n".join(lines)
                except (ValueError, IndexError):
                    return "!history [数量]"
            elif cmd == '!now':
                if current_playing:
                    _, name, artist = current_playing
                    return f"正在播放: {name} - {artist}"
                else:
                    return "当前无播放"
            elif cmd == '!grant' and len(parts) == 1:
                # !grant 无参数，允许所有人点歌
                grant_until_time = float('inf')
                global_temp_grant_per_user = 0
                temp_grant_counts.clear()
                user_already_granted.clear()
                return "Temporarily Grant Access"
            elif cmd == '!grant' and len(parts) >= 3:
                if parts[1] == '-t':
                    try:
                        sec = int(parts[2])
                        grant_until_time = time.time() + max(0, sec)
                        global_temp_grant_per_user = 0
                        temp_grant_counts.clear()
                        user_already_granted.clear()
                        return f"Grant Access for {sec} s"
                    except ValueError:
                        return "时间必须为整数"
                elif parts[1] == '-c':
                    try:
                        count = int(parts[2])
                        if 0 <= count <= 100:
                            global_temp_grant_per_user = count
                            grant_until_time = 0  # 关闭时间模式
                            temp_grant_counts.clear()
                            user_already_granted.clear()  # 重置，让所有人可以重新领取
                            return f"counts.add = {count}"
                        else:
                            return "次数范围 0-100"
                    except ValueError:
                        return "次数必须为整数"
            elif cmd == '!revoke':
                if len(parts) > 1:
                    sub_cmd = parts[1].lower()
                    if sub_cmd == '-c':
                        global_temp_grant_per_user = 0
                        temp_grant_counts.clear()
                        user_already_granted.clear()
                        return "Revoke Permission C"
                    elif sub_cmd == '-t':
                        grant_until_time = 0
                        return "Revoke Permission"
                    elif sub_cmd in ['-ct', '-tc']:
                        grant_until_time = 0
                        global_temp_grant_per_user = 0
                        temp_grant_counts.clear()
                        user_already_granted.clear()
                        return "Revoke Permission"
                else:
                    # !revoke 无参数，等同于 -ct
                    grant_until_time = 0
                    global_temp_grant_per_user = 0
                    temp_grant_counts.clear()
                    user_already_granted.clear()
                    return "Revoke Permission"
            elif cmd == '!stats' and len(parts) >= 2:
                target = parts[1]
                records = []
                try:
                    with open(LOG_FILE, 'r', encoding='utf-8') as f:
                        for line in f:
                            if f"[{target}]：" in line:
                                try:
                                    song_info = line.split(']： ', 1)[1].strip()
                                    records.append(song_info)
                                except:
                                    continue
                    if records:
                        recent = records[-5:]  # 最近5条
                        return f"{target} 点过 {len(records)} 首歌\n最近5首:\n" + "\n".join(recent)
                    else:
                        return f"{target} 没有点过歌"
                except Exception as e:
                    return f"查询失败: {e}"
            else:
                return f"unknown command: {cmd}，使用 !help 查看帮助"
        except Exception as e:
            print(format_system_output(f"命令执行出错: {str(e)}"))
            return f"命令执行出错: {str(e)}"

    @staticmethod
    async def _get_queue_status():
        """获取队列状态"""
        if song_queue.empty():
            return "当前队列为空"
        else:
            # 复制队列并显示歌曲详情
            queue_copy = []
            temp_queue = asyncio.Queue()
            
            # 复制队列内容
            while not song_queue.empty():
                item = await song_queue.get()
                queue_copy.append(item)
                await temp_queue.put(item)
            
            # 恢复原始队列
            while not temp_queue.empty():
                item = await temp_queue.get()
                await song_queue.put(item)
            
            # 生成队列详情字符串
            queue_details = [f"当前队列中有 {len(queue_copy)} 首歌曲:"]
            for i, (sid, name, artist) in enumerate(queue_copy, 1):
                queue_details.append(f"{i}. {name} - {artist}")
            
            return "\n".join(queue_details)

    @staticmethod
    async def _queue_add(query):
        """队列增加歌曲"""
        print(format_admin_output("ADMIN", f"收到队列添加请求: {query}"))
        sid, name, artist = music_bot.get_song_info(query)
        if sid:
            if song_queue.qsize() >= QUEUE_MAXSIZE:
                return "点歌队列已满，无法加入"
            await song_queue.put((sid, name, artist))
            return f"入队成功: {name} (添加者: ADMIN)"
        else:
            return "未找到歌曲"

    @staticmethod
    async def _queue_del(index):
        """删除队列指定位置的歌曲"""
        if index < 1 or index > QUEUE_MAXSIZE:
            return f"歌曲序号必须在1-{QUEUE_MAXSIZE}之间"
        
        if song_queue.empty():
            return "当前队列为空，无法删除"
        
        # 获取当前队列内容
        queue_copy = []
        temp_queue = asyncio.Queue()
        
        # 复制队列内容
        while not song_queue.empty():
            item = await song_queue.get()
            queue_copy.append(item)
            await temp_queue.put(item)
        
        # 恢复原始队列
        while not temp_queue.empty():
            item = await temp_queue.get()
            await song_queue.put(item)
        
        if index > len(queue_copy):
            return f"队列中只有 {len(queue_copy)} 首歌曲，无法删除第 {index} 首"
        
        # 删除指定索引的歌曲 (index - 1 是列表中的实际索引)
        deleted_song = queue_copy.pop(index - 1)
        
        # 重建队列，排除被删除的歌曲
        new_items = queue_copy[:]
        # 清空原队列
        while not song_queue.empty():
            await song_queue.get()
        # 重新放入剩余项目
        for item in new_items:
            await song_queue.put(item)
        
        return f"已删除第 {index} 首歌曲: {deleted_song[1]} - {deleted_song[2]}"

    @staticmethod
    async def _queue_clr():
        """清除队列"""
        cleared_count = 0
        while not song_queue.empty():
            await song_queue.get()
            cleared_count += 1
        
        return f"已清空队列，共删除 {cleared_count} 首歌曲"

# 配置热重载处理器
class ConfigReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("config/config.json"):
            global config, gui_log
            config = load_config()
            print(format_system_output("配置已热重载"))
            # 更新GUI透明度
            if hasattr(gui_log, 'root'):
                alpha = config.get("env_alpha", 1.0)
                gui_log.root.attributes("-alpha", alpha)
            # 更新管理员列表
            global ADMINS
            ADMINS = set(config.get("env_default_admins", ["琴吹炒面"]))

# GUI 日志显示窗口
class LogWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kozeki_GUI")
        self.root.geometry("400x200")
        self.root.attributes("-topmost", True)  # 窗口置顶
        self.alpha = config.get("env_alpha", 1.0)  # 从配置读取透明度
        self.root.attributes("-alpha", self.alpha)
        # 移除窗口边框和标题栏（如果需要完全无边框，取消下面这行注释）
        # self.root.overrideredirect(True) 
        self.log_area = scrolledtext.ScrolledText(
            self.root, 
            wrap=tk.WORD, 
            height=2,  
            state='disabled',
            font=("Consolas", 12),
            bg="#000000",
            fg="#CCCCCC")
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    def log(self, message):
        def update():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END) 
            self.log_area.config(state='disabled')
        # 在主线程安全更新 GUI
        self.root.after(0, update)
    def run(self):
        self.root.mainloop()

# 重定向 print 到 GUI
class PrintToGUI:
    def __init__(self, log_window):
        self.log_window = log_window
    def write(self, message):
        if message.strip():
          self.log_window.log(message.strip())
    def flush(self):
        pass

# 消息回调
async def handle_message(msg_data):
    raw_content = msg_data.get('text', '')
    content = html.unescape(raw_content).strip()
    user_name = msg_data.get('nickname', '未知')
    
    # 确定用户类型
    if user_name in ADMINS:
        user_prefix = "ADM"
        print(format_admin_output(user_name, content))
    elif whitelist_manager.has_permission(user_name):
        user_prefix = "GRP"
        print(format_group_output(user_name, content))
    else:
        user_prefix = "USR"
        print(format_user_output(user_name, content))
    
    is_valid, result = is_valid_admin_key(content)
    if is_valid:
        admin_key = result
        if user_name not in ADMINS:
            ADMINS.add(user_name)
            print(format_system_output(f"{user_name} 成为管理员"))
            save_fused_key(admin_key)
            print(format_system_output(f"{admin_key} 熔断"))
        else:
            print(format_system_output(f"{user_name} 已经是管理员"))
        return  
    
    # 检查是否是命令
    if content.startswith('!'):
        result = await CommandHandler.handle_command(user_name, content)
        if result:
            print(format_system_output(result))
        return
    
    # 检查是否是点歌指令
    if content.startswith(("点歌：", "点歌:")):
        query = content.replace("点歌：", "").replace("点歌:", "").strip()
        if not query: 
            return
        print(format_system_output(f"收到点歌请求: {query} (来自: {user_name})"))
        
        # 检查用户权限
        has_perm = (
            whitelist_manager.has_permission(user_name) or
            time.time() < grant_until_time
        )
        
        # 如果没有直接权限，尝试使用"每人最多N首"临时配额
        if not has_perm and global_temp_grant_per_user > 0:
            if user_name not in user_already_granted:
                # 首次领取：分配 N 次
                temp_grant_counts[user_name] = global_temp_grant_per_user
                user_already_granted.add(user_name)
                print(format_system_output(f"为 {user_name} 分配 {global_temp_grant_per_user} 次点歌权限"))
            
            # 检查当前剩余次数
            if temp_grant_counts.get(user_name, 0) > 0:
                has_perm = True
            else:
                print(format_system_output(f"{user_name} 's request aborted: Permission denied (配额已用尽)"))
                return
        
        if not has_perm:
            print(format_system_output(f"{user_name} 's request aborted: Permission denied"))
            return
            
        sid, name, artist = music_bot.get_song_info(query)
        if sid:
            if song_queue.qsize() >= 5:
                print(format_system_output("点歌队列已满，无法加入"))
                return
            await song_queue.put((sid, name, artist))
            print(format_system_output(f"入队成功: {name} (点歌者: {user_name})"))
            # 记录成功的点歌请求
            log_successful_request(user_name, name, artist)
            # 扣减临时次数（仅对非白名单、非时间许可用户）
            if (not whitelist_manager.has_permission(user_name) and
                time.time() >= grant_until_time and
                user_name in temp_grant_counts):
                temp_grant_counts[user_name] -= 1
                # 不删除 key，保持"已领取"状态，防止重复领
        else:
            print(format_system_output("未找到歌曲"))
            
async def main():
    asyncio.create_task(player_worker())
    monitor = BilibiliHttpMonitor(ROOM_ID, handle_message)
    await monitor.start()
    
if __name__ == '__main__':
    # 尝试导入 win32file（仅 Windows 需要）
    if platform.system() == "Windows":
        try:
            import win32file
        except ImportError:
            print(format_system_output("警告：未安装 pywin32，MPV 控制可能不可用。请运行: pip install pywin32"))
    
    # 启动配置热重载监听
    observer = Observer()
    observer.schedule(ConfigReloadHandler(), path=".", recursive=False)
    # 启动白名单热重载监听
    observer.schedule(WhitelistReloadHandler(), path=".", recursive=False)
    observer.start()
    
    gui_log = LogWindow()
    sys.stdout = PrintToGUI(gui_log)
    sys.stderr = PrintToGUI(gui_log)
    # 异步主程序
    def start_bot():
        asyncio.run(main())
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    gui_log.run()
    observer.stop()
    observer.join()
