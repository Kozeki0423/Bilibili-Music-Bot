# modules/utils.py
# 通用工具函数模块

import re
import hashlib
from datetime import datetime
import platform
import subprocess
import os
import sys

def generate_daily_key(admin_password):
    """生成每日密钥"""
    today_date = datetime.now().strftime('%y%m%d%H')
    key_input = today_date + admin_password
    sha256_hash = hashlib.sha256(key_input.encode('utf-8')).hexdigest()
    return sha256_hash[:10]

def extract_alphanumeric(text):
    """提取字母数字字符"""
    return re.sub(r'[^a-zA-Z0-9]', '', text)

def is_valid_bilibili_id(video_id):
    """检查B站视频ID格式 (av号或BV号)"""
    # 检查av号格式 (如 av123456789)
    if video_id.lower().startswith('av'):
        av_num = video_id[2:]
        return av_num.isdigit()
    
    # 检查BV号格式 (如 BV1xx411c7mu)
    if video_id.startswith('BV'):
        # BV号应为12位字符，包含字母和数字
        return len(video_id) == 12 and re.match(r'^[a-zA-Z0-9]+$', video_id)
    
    return False

def parse_bilibili_id(video_id):
    """
    解析B站视频ID，支持BV号_pN格式
    返回 (bv号, 分p数) 元组，如果不符合格式则返回 (原ID, None)
    """
    # 检查是否是BV号_pN格式
    match = re.match(r'^(BV[A-Za-z0-9]{10})_p(\d+)$', video_id)
    if match:
        bv_id = match.group(1)
        p_number = int(match.group(2))
        return bv_id, p_number
    
    # 检查是否是BV号?p=N格式
    match = re.match(r'^(BV[A-Za-z0-9]{10}).*?\?p=(\d+)$', video_id)
    if match:
        bv_id = match.group(1)
        p_number = int(match.group(2))
        return bv_id, p_number
    
    # 如果不是特殊格式，返回原ID
    return video_id, None

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

def check_and_install_requirements():
    """检查并安装所需的依赖包"""
    import importlib
    import subprocess
    
    required_packages = {
        'aiohttp': 'aiohttp==3.8.5',
        'pyncm': 'pyncm==2.2.1',
        'qrcode': 'qrcode==7.4.2',
        'PIL': 'pillow==9.5.0',
        'watchdog': 'watchdog==3.0.0',  # 新增热重载依赖
        # 'yt-dlp': 'yt-dlp'  # 新增用于获取视频信息
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

def get_mpv_path(config_mpv_path="mpv"):
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
    print(f"未找到本地MPV，使用配置路径: {config_mpv_path}")
    return config_mpv_path

def load_fused_keys(fused_keys_file="data/fused_keys.json"):
    """加载已使用的密钥"""
    import json
    import os
    if os.path.exists(fused_keys_file):
        with open(fused_keys_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('fused_keys', []))
    return set()

def save_fused_key(key, fused_keys_file="data/fused_keys.json"):
    """保存已使用的密钥"""
    import json
    import os
    fused_keys = load_fused_keys(fused_keys_file)
    fused_keys.add(key)
    # 确保data目录存在
    os.makedirs(os.path.dirname(fused_keys_file), exist_ok=True)
    with open(fused_keys_file, 'w', encoding='utf-8') as f:
        json.dump({'fused_keys': list(fused_keys)}, f, ensure_ascii=False, indent=2)

def parse_gui_resize_params(params_str):
    """
    解析GUI resize命令的参数
    支持格式: "w,h", "~,h", "w,~", "full,h", "w,full"
    返回: (width, height) 元组，其中None表示使用当前值，'full'表示使用全屏尺寸
    """
    params = params_str.split(',')
    if len(params) != 2:
        raise ValueError("参数格式错误，应为 'w,h' 或 '~,h' 或 'w,~' 或 'full,h' 或 'w,full'")
    
    w_str = params[0].strip()
    h_str = params[1].strip()
    
    # 解析宽度
    if w_str.lower() == 'full':
        w = 'full'
    elif w_str == '~':
        w = None
    else:
        w = int(w_str)
    
    # 解析高度
    if h_str.lower() == 'full':
        h = 'full'
    elif h_str == '~':
        h = None
    else:
        h = int(h_str)
    
    return w, h

def parse_gui_origin_params(params_str):
    """
    解析GUI origin命令的参数
    格式: "x,y"
    返回: (x, y) 坐标元组
    """
    params = params_str.split(',')
    if len(params) != 2:
        raise ValueError("参数格式错误，应为 'x,y'")
    
    x = int(params[0].strip())
    y = int(params[1].strip())
    
    return x, y

def parse_gui_sign_params(params_str):
    """
    解析GUI sign命令的参数
    格式: "w,h,x,y,alpha,ignore"
    返回: (w, h, x, y, alpha, ignore) 元组
    """
    params = params_str.split(',')
    if len(params) != 6:
        raise ValueError("参数格式错误，应为 'w,h,x,y,alpha,ignore'")
    
    w_str = params[0].strip()
    h_str = params[1].strip()
    x = int(params[2].strip())
    y = int(params[3].strip())
    alpha = float(params[4].strip())
    ignore_str = params[5].strip()
    
    # 验证alpha值
    if alpha < 0 or alpha > 1:
        raise ValueError("透明度必须在0-1之间")
    
    # 解析ignore值
    if ignore_str.lower() in ['true', '1', 'yes', 'on', 't', 'y']:
        ignore = True
    elif ignore_str.lower() in ['false', '0', 'no', 'off', 'f', 'n']:
        ignore = False
    else:
        raise ValueError("穿透状态必须为布尔值(0/1或true/false)")
    
    return w_str, h_str, x, y, alpha, ignore