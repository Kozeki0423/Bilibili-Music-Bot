# modules/command_handler.py
# 命令处理逻辑模块

import re
from datetime import datetime

class CommandHandler:
    def __init__(self, player, queue_manager, permission_manager, music_bot, config, gui_log=None):
        self.player = player
        self.queue_manager = queue_manager
        self.permission_manager = permission_manager
        self.music_bot = music_bot
        self.config = config
        self.log_file = config.get("env_log_file", "data/requests.log")
        self.fallback_playlist_id = config.get("env_playlist", 9162892605)
        self.enable_video_playback = config.get("enable_video_playback", True)
        self.video_timeout_buffer = config.get("env_video_timeout_buffer", 3)
        self.enable_fallback_playlist = config.get("enable_fallback_playlist", True)
        self.queue_maxsize = config.get("env_queue_maxsize", 5)
        self.gui_log = gui_log  # 添加GUI引用
        
        # 从配置加载词典映射
        self.dict_map = self.load_dict_map()
        
        # GUI相关状态变量
        self.gui_hide_state = 0  # 0为未隐藏，1为隐藏
        self.gui_ignore_state = 0  # 0为不穿透，1为穿透
        self.gui_direct_state = 0  # 0为有边框，1为无边框

        # 引入unorthodox功能
        self.unorthodox_enabled = config.get("env_unorthodox", False)

    def load_dict_map(self):
        """加载词典映射文件"""
        import json
        import os
        
        dict_path = "./config/dict.json"
        default_dict = {
            "lll": "473403182"
        }
        
        if not os.path.exists(dict_path):
            # 创建config目录
            os.makedirs(os.path.dirname(dict_path), exist_ok=True)
            with open(dict_path, 'w', encoding='utf-8') as f:
                json.dump(default_dict, f, indent=4, ensure_ascii=False)
            print(f"[SYS] 词典映射文件已创建: {dict_path}")
            return default_dict
        
        with open(dict_path, 'r', encoding='utf-8') as f:
            print(f"[SYS] {dict_path} 已加载")
            return json.load(f)
    
    def save_dict_map(self):
        """保存词典映射到文件"""
        import json
        import os
        
        dict_path = "./config/dict.json"
        # 确保config目录存在
        os.makedirs(os.path.dirname(dict_path), exist_ok=True)
        with open(dict_path, 'w', encoding='utf-8') as f:
            json.dump(self.dict_map, f, ensure_ascii=False, indent=2)
        print(f"词典映射已保存到 {dict_path}")
    
    def is_valid_bilibili_id(self, video_id):
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

    def parse_bilibili_id(self, video_id):
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
    
    def log_video_request(self, username, video_id):
        """记录成功的视频请求到日志文件"""
        import os
        timestamp = datetime.now().strftime('%Y:%m:%d][%H:%M:%S')
        log_entry = f"[{timestamp}] [{username}]： 视频 - {video_id}\n"
        # 确保data目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def log_successful_request(self, username, song_name, artist):
        """记录成功的点歌请求到日志文件"""
        import os
        timestamp = datetime.now().strftime('%Y:%m:%d][%H:%M:%S')
        log_entry = f"[{timestamp}] [{username}]： {song_name} - {artist}\n"
        # 确保data目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    async def handle_command(self, user_name, command_text):
        """处理命令"""
        if not command_text.startswith('!'):
            return None
        # 检查是否是管理员
        if not self.permission_manager.is_admin(user_name):
            print(f"[DNY] {user_name}: {command_text}")
            return None
        # 解析命令
        parts = command_text.split()
        cmd = parts[0].lower()
        
        try:
            if cmd == '!touch' and len(parts) >= 2:
                username = parts[1]
                if self.permission_manager.add_user_to_whitelist(username):
                    return f"已添加 '{username}' 到白名单"
                else:
                    return f" '{username}' 已在白名单中"
            elif cmd == '!rm' and len(parts) >= 2:
                username = parts[1]
                if self.permission_manager.remove_user_from_whitelist(username):
                    return f"已从白名单移除  '{username}'"
                else:
                    return f" '{username}' 不在白名单中"
            elif cmd == '!cat': 
                users = self.permission_manager.list_whitelist_users()
                if users:
                    user_list = ", ".join(users[:10]) 
                    if len(users) > 10:
                        user_list += f" ... 等{len(users)}个用户"
                    return f"白名单用户 ({len(users)}人): {user_list}"
                else:
                    return "白名单为空"
            elif cmd == '!clr':
                self.permission_manager.clear_whitelist()
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
│ !queue uadd ...- 使用备用源点歌
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
│ [视频播放控制]
├──────────────────────
│ !clock               - 查询计时器超时参数
│ !clock {num}         - 设置计时器超时参数
│ !service video start - 启用视频播放功能
│ !service video stop  - 禁用视频播放功能

┌──────────────────────
│ [词典管理]
├──────────────────────
│ !dict            - 查看词典映射
│ !dict add key value - 添加词典映射
│ !dict rm key     - 删除词典映射

┌──────────────────────
│ [GUI窗口控制]
├──────────────────────
│ !gui info        - 显示窗口信息
│ !gui hide        - 切换隐藏/显示状态
│ !gui hide <bool> - 设置隐藏状态
│ !gui ignore      - 切换穿透/非穿透状态
│ !gui ignore <bool> - 设置穿透状态
│ !gui direct      - 切换边框/无边框状态
│ !gui direct <bool> - 设置边框状态
│ !gui resize <w>,<h> - 调整窗口大小
│ !gui origin <x>,<y> - 设置窗口坐标
│ !gui origin      - 查询窗口坐标
│ !gui alpha <float> - 设置透明度
│ !gui set <int>   - 应用预设窗口样式
│ !gui sign "<w>,<h>,<x>,<y>,<alpha>,<ignore>" - 注册新预设


┌──────────────────────
│ [环境变量控制]
├──────────────────────
│ !env               - 查看所有环境变量
│ !env {env}         - 查询环境变量值
│ !env {env} {value} - 设置环境变量值

┌──────────────────────
│ [其他]
├──────────────────────
│ !service           - 检查功能服务
│ !reload            - 重新加载配置
│ !help              - 显示本帮助

 点歌：song name / id  - 点播歌曲
                """
                return help_text.strip()
            elif cmd == '!pause':
                await self.player.pause()
                return "已暂停播放"
            elif cmd == '!resume':
                await self.player.resume()
                return "已恢复播放"
            elif cmd == '!skip':
                if self.player.current_mpv_process and self.player.current_mpv_process.returncode is None:
                    # 取消计时器任务
                    if self.player.current_timer_task and not self.player.current_timer_task.done():
                        self.player.current_timer_task.cancel()
                        try:
                            await self.player.current_timer_task
                        except asyncio.CancelledError:
                            pass
                    # 修复：检查skip方法是否是协程，如果不是则直接调用
                    skip_result = self.player.skip()
                    if skip_result and hasattr(skip_result, '__await__'):
                        await skip_result
                    else:
                        # 如果skip方法不是协程，直接调用
                        pass
                    return "已跳过当前歌曲"
                else:
                    return "当前无播放中的歌曲"
            elif cmd == '!vol':
                if len(parts) < 2:
                    # 查询当前音量
                    return f"当前音量: {self.player.get_volume()}"
                else:
                    # 设置音量
                    try:
                        vol = int(parts[1])
                        if 0 <= vol <= 100:
                            self.player.set_volume(vol)
                            return f"音量已设为 {vol}"
                        else:
                            return "音量范围必须是 0-100"
                    except ValueError:
                        return "音量必须是整数"
            elif cmd == '!queue':
                # 检查是否有子命令
                if len(parts) < 2:
                    # !queue 或 !queue ls
                    return await self._get_queue_status()
                else:
                    sub_cmd = parts[1].lower()
                    if sub_cmd == 'ls':
                        # !queue ls
                        return await self._get_queue_status()
                    elif sub_cmd == 'add' and len(parts) >= 3:
                        # !queue add 歌名或id
                        query = ' '.join(parts[2:])
                        return await self._queue_add(query)
                    elif sub_cmd == 'del' and len(parts) == 3:
                        # !queue del <1-5>
                        try:
                            index = int(parts[2])
                            return await self._queue_del(index)
                        except ValueError:
                            return f"无效的歌曲序号，请输入1-{self.queue_maxsize}之间的数字"
                    elif sub_cmd == 'clr':
                        # !queue clr
                        return await self._queue_clr()
                    elif sub_cmd == 'uadd' and len(parts) >= 3:
                        # !queue uadd 歌名或id (使用非正统音乐源)
                        query = ' '.join(parts[2:])
                        return await self._queue_unorthodox_add(query)
                    else:
                        return f"未知的 queue 子命令: {' '.join(parts[1:])}，使用 !help 查看帮助"
            elif cmd == '!history':
                try:
                    # 修改这里：当没有传入参数时，默认为5
                    num = int(parts[1]) if len(parts) > 1 else 5
                    # 使用queue_manager的get_history_stack方法
                    if self.queue_manager:
                        history_items = self.queue_manager.get_history_stack(num)
                    else:
                        history_items = self.player.get_play_history(num)
                    lines = ["最近播放:"]
                    for item in reversed(history_items):
                        if isinstance(item, tuple) and len(item) >= 3:
                            sid, name, artist = item
                            lines.append(f"{name} - {artist}")
                        else:
                            lines.append(f"{item}")
                    return "\n".join(lines)
                except (ValueError, IndexError):
                    return "!history [数量]"
            elif cmd == '!now':
                current_playing = self.player.get_current_playing()
                if current_playing:
                    _, name, artist = current_playing
                    return f"正在播放: {name} - {artist}"
                else:
                    return "当前无播放"
            elif cmd == '!grant' and len(parts) == 1:
                # !grant 无参数，允许所有人点歌
                self.permission_manager.grant_temp_access("time", float('inf'))
                return "Temporarily Grant Access"
            elif cmd == '!grant' and len(parts) >= 3:
                if parts[1] == '-t':
                    try:
                        sec = int(parts[2])
                        self.permission_manager.grant_temp_access("time", sec)
                        return f"Grant Access for {sec} s"
                    except ValueError:
                        return "时间必须为整数"
                elif parts[1] == '-c':
                    try:
                        count = int(parts[2])
                        if 0 <= count <= 100:
                            self.permission_manager.grant_temp_access("count", count)
                            return f"counts.add = {count}"
                        else:
                            return "次数范围 0-100"
                    except ValueError:
                        return "次数必须为整数"
            elif cmd == '!revoke':
                if len(parts) > 1:
                    sub_cmd = parts[1].lower()
                    if sub_cmd == '-c':
                        self.permission_manager.revoke_temp_access("count")
                        return "Revoke Permission C"
                    elif sub_cmd == '-t':
                        self.permission_manager.revoke_temp_access("time")
                        return "Revoke Permission"
                    elif sub_cmd in ['-ct', '-tc']:
                        self.permission_manager.revoke_temp_access("all")
                        return "Revoke Permission"
                else:
                    # !revoke 无参数，等同于 -ct
                    self.permission_manager.revoke_temp_access("all")
                    return "Revoke Permission"
            elif cmd == '!stats' and len(parts) >= 2:
                target = parts[1]
                records = []
                try:
                    with open(self.log_file, 'r', encoding='utf-8') as f:
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
            elif cmd == '!clock':
                # !clock 命令实现
                if len(parts) == 1:
                    # 查看当前 VIDEO_TIMEOUT_BUFFER
                    return f"VIDEO_TIMEOUT_BUFFER: {self.video_timeout_buffer}"
                elif len(parts) == 2:
                    # 设置（已有逻辑）
                    try:
                        num = int(parts[1])
                        if num < 0:
                            return "Undefined Behavior"
                        if num > 300:  # 限制最大值为300秒（5分钟）
                            return "Undefined Behavior"
                        
                        # 更新全局变量
                        self.video_timeout_buffer = num
                        # 更新配置文件
                        self.config["env_video_timeout_buffer"] = self.video_timeout_buffer
                        import json
                        with open("config/config.json", "w", encoding="utf-8") as f:
                            json.dump(self.config, f, indent=4, ensure_ascii=False)
                        
                        return f"超时参数: {num} s"
                    except ValueError:
                        return "Invalid Literal"
            elif cmd == '!env':
                # !env 命令实现
                if len(parts) == 1:
                    # 查看所有环境变量
                    env_vars = {
                        "ROOM_ID": self.config.get("env_roomid", 1896163590),
                        "POLL_INTERVAL": self.config.get("env_poll_interval", 5),
                        "FALLBACK_PLAYLIST_ID": self.fallback_playlist_id,
                        "QUEUE_MAXSIZE": self.queue_maxsize,
                        "ENABLE_VIDEO_PLAYBACK": self.enable_video_playback,
                        "VIDEO_TIMEOUT_BUFFER": self.video_timeout_buffer,
                        "ENABLE_FALLBACK_PLAYLIST": self.enable_fallback_playlist,
                        "ALPHA": self.config.get("env_alpha", 1.0),
                        "UNORTHODOX": self.config.get("env_unorthodox", False)
                    }
                    result = []
                    for var_name, var_value in env_vars.items():
                        result.append(f"{var_name}: {var_value}")
                    return "\n"+"\n".join(result)
                elif len(parts) == 2:
                    # 查询单个环境变量
                    var_name = parts[1].upper()
                    if var_name == "ROOM_ID":
                        return f"ROOM_ID: {self.config.get('env_roomid', 1896163590)}"
                    elif var_name == "POLL_INTERVAL":
                        return f"POLL_INTERVAL: {self.config.get('env_poll_interval', 5)}"
                    elif var_name == "FALLBACK_PLAYLIST_ID":
                        return f"FALLBACK_PLAYLIST_ID: {self.fallback_playlist_id}"
                    elif var_name == "QUEUE_MAXSIZE":
                        return f"QUEUE_MAXSIZE: {self.queue_maxsize}"
                    elif var_name == "ENABLE_VIDEO_PLAYBACK":
                        return f"ENABLE_VIDEO_PLAYBACK: {self.enable_video_playback}"
                    elif var_name == "VIDEO_TIMEOUT_BUFFER":
                        return f"VIDEO_TIMEOUT_BUFFER: {self.video_timeout_buffer}"
                    elif var_name == "ENABLE_FALLBACK_PLAYLIST":
                        return f"ENABLE_FALLBACK_PLAYLIST: {self.enable_fallback_playlist}"
                    elif var_name == "ALPHA":
                        return f"ALPHA: {self.config.get('env_alpha', 1.0)}"  # 修改变量名为ALPHA
                    elif var_name == "UNORTHODOX":  # 新增UNORTHODOX变量
                        return f"UNORTHODOX: {self.config.get('env_unorthodox', False)}"
                    else:
                        return f"未知环境变量: {var_name}"
                elif len(parts) == 3:
                    # 设置环境变量
                    var_name = parts[1].upper()
                    var_value = parts[2]
                    try:
                        if var_name == "ROOM_ID":
                            new_value = int(var_value)
                            self.config["env_roomid"] = new_value
                        elif var_name == "POLL_INTERVAL":
                            new_value = int(var_value)
                            self.config["env_poll_interval"] = new_value
                        elif var_name == "FALLBACK_PLAYLIST_ID":
                            new_value = int(var_value)
                            self.config["env_playlist"] = new_value
                            self.fallback_playlist_id = new_value
                        elif var_name == "QUEUE_MAXSIZE":
                            new_value = int(var_value)
                            self.config["env_queue_maxsize"] = new_value
                            self.queue_maxsize = new_value
                        elif var_name == "ENABLE_VIDEO_PLAYBACK":
                            new_value = var_value.lower() in ('true', '1', 'yes', 'on')
                            self.config["enable_video_playback"] = new_value
                            self.enable_video_playback = new_value
                        elif var_name == "VIDEO_TIMEOUT_BUFFER":
                            new_value = int(var_value)
                            if new_value < 0 or new_value > 300:
                                return "Undefined Behavior"
                            self.config["env_video_timeout_buffer"] = new_value
                            self.video_timeout_buffer = new_value
                        elif var_name == "ENABLE_FALLBACK_PLAYLIST":
                            new_value = var_value.lower() in ('true', '1', 'yes', 'on')
                            self.config["enable_fallback_playlist"] = new_value
                            self.enable_fallback_playlist = new_value
                        elif var_name == "ALPHA":  # 修改变量名为ALPHA
                            new_value = float(var_value)
                            self.config["env_alpha"] = new_value  # 保留原始配置键名
                            
                            # 立即更新GUI透明度
                            if self.gui_log:
                                self.gui_log.set_alpha(new_value)
                        elif var_name == "UNORTHODOX":  # 新增UNORTHODOX变量
                            new_value = var_value.lower() in ('true', '1', 'yes', 'on', 't', 'y')
                            self.config["env_unorthodox"] = new_value
                            self.unorthodox_enabled = new_value
                            
                            # 保存配置到文件
                            import json
                            with open("config/config.json", "w", encoding="utf-8") as f:
                                json.dump(self.config, f, indent=4, ensure_ascii=False)
                            
                            status = "已启用" if new_value else "已禁用"
                            return f"UNORTHODOX {status}"
                        else:
                            return f"未知环境变量: {var_name}"
                        
                        # 保存配置到文件
                        import json
                        with open("config/config.json", "w", encoding="utf-8") as f:
                            json.dump(self.config, f, indent=4, ensure_ascii=False)
                        
                        return f"{var_name} 已设置为: {var_value}"
                    except ValueError:
                        return "无效的值类型"
                else:
                    return "无效的env命令参数，使用 !help 查看帮助"
            elif cmd == '!reload':
                # !reload 命令：重新加载配置
                try:
                    # 重新加载配置
                    from modules.config_loader import ConfigLoader
                    config_loader = ConfigLoader()
                    new_config = config_loader.load_config()
                    
                    # 更新当前配置
                    self.config.update(new_config)
                    
                    # 更新相关模块的配置
                    self.fallback_playlist_id = self.config.get("env_playlist", 9162892605)
                    self.enable_video_playback = self.config.get("enable_video_playback", True)
                    self.video_timeout_buffer = self.config.get("env_video_timeout_buffer", 3)
                    self.enable_fallback_playlist = self.config.get("enable_fallback_playlist", True)
                    self.queue_maxsize = self.config.get("env_queue_maxsize", 5)
                    self.unorthodox_enabled = self.config.get("env_unorthodox", False)  # 更新unorthodox状态
                    
                    # 通知权限管理器重新生成密钥（基于当前时间）
                    self.permission_manager.config = self.config
                    self.permission_manager.admin_password = self.config.get("env_admin_password", "mysecret")
                    
                    # 重新加载词典映射
                    self.dict_map = self.load_dict_map()
                    
                    # 更新GUI透明度
                    if self.gui_log:
                        alpha = self.config.get("env_alpha", 1.0)
                        self.gui_log.set_alpha(alpha)
                    
                    return "配置已重新加载"
                except Exception as e:
                    return f"重载配置失败: {str(e)}"
            elif cmd == '!service' and len(parts) >= 3:
                # 处理 !service video start/stop 命令
                if parts[1].lower() == 'video':
                    if parts[2].lower() == 'start':
                        return self._set_video_playback(True)
                    elif parts[2].lower() == 'stop':
                        return self._set_video_playback(False)
                    else:
                        return "无效的service命令参数，使用 !help 查看帮助"
                elif parts[1].lower() == 'unorthodox':  # 处理 !service unorthodox start/stop 命令
                    if parts[2].lower() == 'start':
                        return self._set_unorthodox(True)
                    elif parts[2].lower() == 'stop':
                        return self._set_unorthodox(False)
                    else:
                        return "无效的service命令参数，使用 !help 查看帮助"
                else:
                    return "无效的service命令参数，使用 !help 查看帮助"
            elif cmd == '!service' and len(parts) == 1:
                # 处理 !service 命令，检查当前启用的功能服务
                return self._get_service_status()
            elif cmd == '!dict' and len(parts) == 1:
                # !dict - 查看词典映射
                if self.dict_map:
                    dict_items = list(self.dict_map.items())[:10]  # 显示前10个
                    dict_list = [f"{key} -> {value}" for key, value in dict_items]
                    if len(self.dict_map) > 10:
                        dict_list.append(f"... 等{len(self.dict_map)}个映射")
                    return f"词典映射 ({len(self.dict_map)}个): " + ", ".join(dict_list)
                else:
                    return "词典映射为空"
            elif cmd == '!dict' and len(parts) >= 3 and parts[1].lower() == 'add':
                # !dict add key value - 添加词典映射
                key = parts[2]
                value = ' '.join(parts[3:])
                self.dict_map[key] = value
                self.save_dict_map()
                return f"已添加词典映射: {key} -> {value}"
            elif cmd == '!dict' and len(parts) == 3 and parts[1].lower() == 'rm':
                # !dict rm key - 删除词典映射
                key = parts[2]
                if key in self.dict_map:
                    del self.dict_map[key]
                    self.save_dict_map()
                    return f"已删除词典映射: {key}"
                else:
                    return f"词典中不存在关键字: {key}"
            # 添加GUI命令处理
            elif cmd == '!gui':
                if len(parts) < 2:
                    return "GUI命令参数不足，使用 !help 查看帮助"
                
                gui_cmd = parts[1].lower()
                
                if gui_cmd == 'info':
                    # !gui info - 输出当前窗口的信息
                    if self.gui_log:
                        screen_w = self.gui_log.root.winfo_screenwidth()
                        screen_h = self.gui_log.root.winfo_screenheight()
                        w = self.gui_log.root.winfo_width()
                        h = self.gui_log.root.winfo_height()
                        x = self.gui_log.root.winfo_x()
                        y = self.gui_log.root.winfo_y()
                        alpha = self.config.get("env_alpha", 1.0)
                        ignore_status = "穿透" if self.gui_ignore_state == 1 else "非穿透"
                        hide_status = "隐藏" if self.gui_hide_state == 1 else "显示"
                        direct_status = "无边框" if self.gui_direct_state == 1 else "有边框"
                        
                        info = f"显示器: {screen_w}x{screen_h}\n窗口: {w}x{h}+{x}+{y}\n透明度: {alpha}\n穿透: {ignore_status}\n隐藏: {hide_status}\n边框: {direct_status}"
                        return info
                    else:
                        return "GUI未初始化"
                        
                elif gui_cmd == 'hide':
                    if len(parts) == 2:
                        # !gui hide - 切换隐藏状态
                        if self.gui_log:
                            if self.gui_hide_state == 0:
                                # 隐藏窗口
                                self.gui_log.root.withdraw()
                                self.gui_hide_state = 1
                                return "窗口已隐藏"
                            else:
                                # 显示窗口
                                self.gui_log.root.deiconify()
                                self.gui_hide_state = 0
                                return "窗口已显示"
                        else:
                            return "GUI未初始化"
                    elif len(parts) == 3:
                        # !gui hide <bool> - 设置隐藏状态
                        bool_val = parts[2].lower()
                        if bool_val in ['true', '1', 'yes', 'on', 't', 'y']:
                            if self.gui_log:
                                self.gui_log.root.withdraw()
                                self.gui_hide_state = 1
                                return "窗口已隐藏"
                            else:
                                return "GUI未初始化"
                        elif bool_val in ['false', '0', 'no', 'off', 'f', 'n']:
                            if self.gui_log:
                                self.gui_log.root.deiconify()
                                self.gui_hide_state = 0
                                return "窗口已显示"
                            else:
                                return "GUI未初始化"
                        else:
                            return "布尔值无效，使用true/false或1/0"
                    else:
                        return "GUI hide命令参数错误"
                        
                elif gui_cmd == 'ignore':
                    if len(parts) == 2:
                        # !gui ignore - 切换穿透状态
                        if self.gui_log:
                            if self.gui_ignore_state == 0:
                                # 设置穿透
                                try:
                                    import platform
                                    if platform.system() == "Windows":
                                        import pywintypes
                                        from ctypes import windll, c_int, c_ulong, byref
                                        
                                        # 获取窗口句柄
                                        hwnd = windll.user32.GetParent(self.gui_log.root.winfo_id())
                                        
                                        # 设置窗口样式为穿透
                                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                                        ex_style |= 0x20  # WS_EX_TRANSPARENT
                                        ex_style |= 0x80000  # WS_EX_LAYERED
                                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                                        
                                        # 设置透明度（使用配置中的透明度值）
                                        alpha = self.config.get("env_alpha", 1.0)
                                        alpha_val = int(alpha * 255)
                                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                                        
                                        self.gui_ignore_state = 1
                                        return "窗口穿透已启用"
                                    else:
                                        return "仅支持Windows系统设置穿透"
                                except Exception as e:
                                    return f"设置穿透失败: {e}"
                            else:
                                # 取消穿透
                                try:
                                    import platform
                                    if platform.system() == "Windows":
                                        import pywintypes
                                        from ctypes import windll, c_int, c_ulong, byref
                                        
                                        # 获取窗口句柄
                                        hwnd = windll.user32.GetParent(self.gui_log.root.winfo_id())
                                        
                                        # 移除窗口穿透样式
                                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                                        ex_style &= ~0x20  # 移除 WS_EX_TRANSPARENT
                                        ex_style &= ~0x80000  # 移除 WS_EX_LAYERED
                                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                                        
                                        # 恢复透明度（使用配置中的透明度值）
                                        alpha = self.config.get("env_alpha", 1.0)
                                        alpha_val = int(alpha * 255)
                                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                                        
                                        self.gui_ignore_state = 0
                                        return "窗口穿透已禁用"
                                    else:
                                        return "仅支持Windows系统设置穿透"
                                except Exception as e:
                                    return f"取消穿透失败: {e}"
                        else:
                            return "GUI未初始化"
                    elif len(parts) == 3:
                        # !gui ignore <bool> - 设置穿透状态
                        bool_val = parts[2].lower()
                        if bool_val in ['true', '1', 'yes', 'on', 't', 'y']:
                            if self.gui_log:
                                try:
                                    import platform
                                    if platform.system() == "Windows":
                                        import pywintypes
                                        from ctypes import windll, c_int, c_ulong, byref
                                        
                                        # 获取窗口句柄
                                        hwnd = windll.user32.GetParent(self.gui_log.root.winfo_id())
                                        
                                        # 设置窗口样式为穿透
                                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                                        ex_style |= 0x20  # WS_EX_TRANSPARENT
                                        ex_style |= 0x80000  # WS_EX_LAYERED
                                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                                        
                                        # 设置透明度（使用配置中的透明度值）
                                        alpha = self.config.get("env_alpha", 1.0)
                                        alpha_val = int(alpha * 255)
                                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                                        
                                        self.gui_ignore_state = 1
                                        return "窗口穿透已启用"
                                    else:
                                        return "仅支持Windows系统设置穿透"
                                except Exception as e:
                                    return f"设置穿透失败: {e}"
                            else:
                                return "GUI未初始化"
                        elif bool_val in ['false', '0', 'no', 'off', 'f', 'n']:
                            if self.gui_log:
                                try:
                                    import platform
                                    if platform.system() == "Windows":
                                        import pywintypes
                                        from ctypes import windll, c_int, c_ulong, byref
                                        
                                        # 获取窗口句柄
                                        hwnd = windll.user32.GetParent(self.gui_log.root.winfo_id())
                                        
                                        # 移除窗口穿透样式
                                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                                        ex_style &= ~0x20  # 移除 WS_EX_TRANSPARENT
                                        ex_style &= ~0x80000  # 移除 WS_EX_LAYERED
                                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                                        
                                        # 恢复透明度（使用配置中的透明度值）
                                        alpha = self.config.get("env_alpha", 1.0)
                                        alpha_val = int(alpha * 255)
                                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                                        
                                        self.gui_ignore_state = 0
                                        return "窗口穿透已禁用"
                                    else:
                                        return "仅支持Windows系统设置穿透"
                                except Exception as e:
                                    return f"取消穿透失败: {e}"
                            else:
                                return "GUI未初始化"
                        else:
                            return "布尔值无效，使用true/false或1/0"
                    else:
                        return "GUI ignore命令参数错误"
                        
                elif gui_cmd == 'direct':
                    if len(parts) == 2:
                        # !gui direct - 切换边框状态
                        if self.gui_log:
                            if self.gui_direct_state == 0:
                                # 设置无边框
                                try:
                                    self.gui_log.root.overrideredirect(True)
                                    self.gui_direct_state = 1
                                    return "窗口边框已隐藏"
                                except Exception as e:
                                    return f"设置无边框失败: {e}"
                            else:
                                # 恢复边框
                                try:
                                    self.gui_log.root.overrideredirect(False)
                                    self.gui_direct_state = 0
                                    return "窗口边框已显示"
                                except Exception as e:
                                    return f"恢复边框失败: {e}"
                        else:
                            return "GUI未初始化"
                    elif len(parts) == 3:
                        # !gui direct <bool> - 设置边框状态
                        bool_val = parts[2].lower()
                        if bool_val in ['true', '1', 'yes', 'on', 't', 'y']:
                            if self.gui_log:
                                try:
                                    self.gui_log.root.overrideredirect(True)
                                    self.gui_direct_state = 1
                                    return "窗口边框已隐藏"
                                except Exception as e:
                                    return f"设置无边框失败: {e}"
                            else:
                                return "GUI未初始化"
                        elif bool_val in ['false', '0', 'no', 'off', 'f', 'n']:
                            if self.gui_log:
                                try:
                                    self.gui_log.root.overrideredirect(False)
                                    self.gui_direct_state = 0
                                    return "窗口边框已显示"
                                except Exception as e:
                                    return f"恢复边框失败: {e}"
                            else:
                                return "GUI未初始化"
                        else:
                            return "布尔值无效，使用true/false或1/0"
                    else:
                        return "GUI direct命令参数错误"
                        
                elif gui_cmd == 'resize':
                    if len(parts) == 3:
                        # !gui resize <int>,<int> 或 !gui resize ~,<int> 或 !gui resize <int>,~ 或 !gui resize full,<int> 或 !gui resize <int>,full
                        resize_params = parts[2].split(',')
                        if len(resize_params) != 2:
                            return "resize参数格式错误，应为 <int>,<int> 或 ~,<int> 或 <int>,~ 或 full,<int> 或 <int>,full"
                        
                        try:
                            w_str = resize_params[0].strip()
                            h_str = resize_params[1].strip()
                            
                            if self.gui_log:
                                current_w = self.gui_log.root.winfo_width()
                                current_h = self.gui_log.root.winfo_height()
                                
                                # 获取屏幕尺寸
                                screen_w = self.gui_log.root.winfo_screenwidth()
                                screen_h = self.gui_log.root.winfo_screenheight()
                                
                                # 解析宽度
                                if w_str.lower() == 'full':
                                    new_w = screen_w
                                elif w_str == '~':
                                    new_w = current_w
                                else:
                                    new_w = int(w_str)
                                
                                # 解析高度
                                if h_str.lower() == 'full':
                                    new_h = screen_h
                                elif h_str == '~':
                                    new_h = current_h
                                else:
                                    new_h = int(h_str)
                                
                                # 检查边界值
                                if new_w < 100 or new_h < 100:
                                    return "窗口尺寸不能小于100x100像素"
                                
                                if new_w > screen_w or new_h > screen_h:
                                    return "窗口尺寸不能超过屏幕尺寸"
                                
                                self.gui_log.root.geometry(f"{new_w}x{new_h}")
                                return f"窗口大小已调整为: {new_w}x{new_h}"
                            else:
                                return "GUI未初始化"
                        except ValueError:
                            return "resize参数必须为整数、~或full"
                    else:
                        return "GUI resize命令参数错误，格式: !gui resize <w>,<h>"
                        
                elif gui_cmd == 'origin':
                    if len(parts) == 2:
                        # !gui origin - 查询窗口坐标
                        if self.gui_log:
                            x = self.gui_log.root.winfo_x()
                            y = self.gui_log.root.winfo_y()
                            return f"窗口坐标: ({x}, {y})"
                        else:
                            return "GUI未初始化"
                    elif len(parts) == 3:
                        # !gui origin <int>,<int> - 设置窗口坐标
                        origin_params = parts[2].split(',')
                        if len(origin_params) != 2:
                            return "origin参数格式错误，应为 <int>,<int>"
                        
                        try:
                            x = int(origin_params[0].strip())
                            y = int(origin_params[1].strip())
                            
                            if self.gui_log:
                                # 检查边界值
                                screen_w = self.gui_log.root.winfo_screenwidth()
                                screen_h = self.gui_log.root.winfo_screenheight()
                                
                                if x < 0 or y < 0 or x > screen_w or y > screen_h:
                                    return "窗口坐标超出屏幕范围"
                                
                                w = self.gui_log.root.winfo_width()
                                h = self.gui_log.root.winfo_height()
                                
                                self.gui_log.root.geometry(f"{w}x{h}+{x}+{y}")
                                return f"窗口坐标已设置为: ({x}, {y})"
                            else:
                                return "GUI未初始化"
                        except ValueError:
                            return "origin参数必须为整数"
                    else:
                        return "GUI origin命令参数错误，格式: !gui origin <x>,<y>"
                        
                elif gui_cmd == 'set':
                    if len(parts) == 3:
                        # !gui set <int> - 按照预设<int>更改窗口样式
                        try:
                            preset_num = int(parts[2])
                            if preset_num <= 0:
                                return "预设编号必须为正整数"
                            
                            # 加载预设配置
                            import json
                            import os
                            preset_path = "./config/preset.json"
                            
                            if not os.path.exists(preset_path):
                                return f"预设文件不存在: {preset_path}"
                            
                            with open(preset_path, 'r', encoding='utf-8') as f:
                                presets = json.load(f)
                            
                            preset_key = f"env_windows_preset_{preset_num}"
                            if preset_key not in presets:
                                return f"预设 {preset_num} 不存在"
                            
                            preset_data = presets[preset_key]
                            if len(preset_data) != 6:
                                return f"预设 {preset_num} 数据格式错误，应包含6个参数"
                            
                            w_str, h_str, x_str, y_str, alpha_str, ignore_str = preset_data
                            
                            if self.gui_log:
                                # 获取屏幕尺寸
                                screen_w = self.gui_log.root.winfo_screenwidth()
                                screen_h = self.gui_log.root.winfo_screenheight()
                                
                                # 解析尺寸参数
                                w = screen_w if w_str.lower() == 'full' else int(w_str)
                                h = screen_h if h_str.lower() == 'full' else int(h_str)
                                x = int(x_str)
                                y = int(y_str)
                                alpha = float(alpha_str)
                                
                                # 检查参数有效性
                                if alpha < 0 or alpha > 1:
                                    return "透明度必须在0-1之间"
                                
                                # 设置窗口大小和位置
                                self.gui_log.root.geometry(f"{w}x{h}+{x}+{y}")
                                
                                # 设置透明度
                                self.gui_log.set_alpha(alpha)
                                
                                # 更新配置中的透明度
                                self.config["env_alpha"] = alpha
                                import json
                                with open("config/config.json", "w", encoding="utf-8") as f:
                                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                                
                                # 设置穿透状态
                                ignore_bool = ignore_str.lower() in ['true', '1', 'yes', 'on', 't', 'y']
                                
                                # 检查当前穿透状态，如果不同则切换
                                if (self.gui_ignore_state == 1) != ignore_bool:
                                    if ignore_bool:
                                        # 启用穿透
                                        try:
                                            import platform
                                            if platform.system() == "Windows":
                                                import pywintypes
                                                from ctypes import windll, c_int, c_ulong, byref
                                                
                                                # 获取窗口句柄
                                                hwnd = windll.user32.GetParent(self.gui_log.root.winfo_id())
                                                
                                                # 设置窗口样式为穿透
                                                ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                                                ex_style |= 0x20  # WS_EX_TRANSPARENT
                                                ex_style |= 0x80000  # WS_EX_LAYERED
                                                windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                                                
                                                # 设置透明度
                                                alpha_val = int(alpha * 255)
                                                windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                                                
                                                self.gui_ignore_state = 1
                                            else:
                                                return "仅支持Windows系统设置穿透"
                                        except Exception as e:
                                            return f"设置穿透失败: {e}"
                                    else:
                                        # 禁用穿透
                                        try:
                                            import platform
                                            if platform.system() == "Windows":
                                                import pywintypes
                                                from ctypes import windll, c_int, c_ulong, byref
                                                
                                                # 获取窗口句柄
                                                hwnd = windll.user32.GetParent(self.gui_log.root.winfo_id())
                                                
                                                # 移除窗口穿透样式
                                                ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                                                ex_style &= ~0x20  # 移除 WS_EX_TRANSPARENT
                                                ex_style &= ~0x80000  # 移除 WS_EX_LAYERED
                                                windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                                                
                                                # 恢复透明度（使用配置中的透明度值）
                                                alpha_val = int(alpha * 255)
                                                windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                                                
                                                self.gui_ignore_state = 0
                                            else:
                                                return "仅支持Windows系统设置穿透"
                                        except Exception as e:
                                            return f"取消穿透失败: {e}"
                                
                                return f"预设 {preset_num} 已应用: {w}x{h}+{x}+{y}, 透明度:{alpha}, 穿透:{ignore_bool}"
                            else:
                                return "GUI未初始化"
                        except ValueError:
                            return "预设编号必须为整数"
                        except json.JSONDecodeError:
                            return "预设文件格式错误，不是有效的JSON文件"
                        except Exception as e:
                            return f"应用预设失败: {e}"
                    else:
                        return "GUI set命令参数错误，格式: !gui set <int>"
                        
                elif gui_cmd == 'sign':
                    if len(parts) == 3:
                        # !gui sign "<int>,<int>,<int>,<int>,<float>,<bool>" - 注册预设
                        try:
                            # 解析参数字符串
                            params_str = parts[2].strip('"')
                            params = params_str.split(',')
                            
                            if len(params) != 6:
                                return "预设参数必须包含6个值: 宽度,高度,坐标X,坐标Y,透明度,穿透状态"
                            
                            w_str, h_str, x_str, y_str, alpha_str, ignore_str = [p.strip() for p in params]
                            
                            # 验证参数
                            if w_str.lower() != 'full':
                                w = int(w_str)
                                if w < 0:
                                    return "窗口宽度不能为负数"
                            else:
                                w = 'full'
                            
                            if h_str.lower() != 'full':
                                h = int(h_str)
                                if h < 0:
                                    return "窗口高度不能为负数"
                            else:
                                h = 'full'
                            
                            x = int(x_str)
                            y = int(y_str)
                            alpha = float(alpha_str)
                            
                            if alpha < 0 or alpha > 1:
                                return "透明度必须在0-1之间"
                            
                            # 解析布尔值
                            if ignore_str.lower() in ['true', '1', 'yes', 'on', 't', 'y']:
                                ignore = 'true'
                            elif ignore_str.lower() in ['false', '0', 'no', 'off', 'f', 'n']:
                                ignore = 'false'
                            else:
                                return "穿透状态必须为布尔值(0/1或true/false)"
                            
                            # 加载现有预设
                            import json
                            import os
                            preset_path = "./config/preset.json"
                            
                            if os.path.exists(preset_path):
                                with open(preset_path, 'r', encoding='utf-8') as f:
                                    presets = json.load(f)
                            else:
                                presets = {}
                            
                            # 找到下一个可用的预设编号
                            existing_nums = []
                            for key in presets.keys():
                                if key.startswith("env_windows_preset_"):
                                    try:
                                        num = int(key.replace("env_windows_preset_", ""))
                                        existing_nums.append(num)
                                    except ValueError:
                                        continue
                            
                            next_num = 1
                            if existing_nums:
                                next_num = max(existing_nums) + 1
                            
                            # 创建新预设
                            new_preset_key = f"env_windows_preset_{next_num}"
                            presets[new_preset_key] = [str(w), str(h), str(x), str(y), str(alpha), ignore]
                            
                            # 保存预设
                            os.makedirs(os.path.dirname(preset_path), exist_ok=True)
                            with open(preset_path, 'w', encoding='utf-8') as f:
                                json.dump(presets, f, ensure_ascii=False, indent=2)
                            
                            return f"已注册预设 {next_num}"
                            
                        except ValueError:
                            return "参数格式错误，请使用: !gui sign \"w,h,x,y,alpha,ignore\""
                        except Exception as e:
                            return f"注册预设失败: {e}"
                    else:
                        return "GUI sign命令参数错误，格式: !gui sign \"w,h,x,y,alpha,ignore\""
                        
                elif gui_cmd == 'alpha':  # 新增 !gui alpha 命令
                    if len(parts) == 3:
                        try:
                            alpha_value = float(parts[2])
                            if alpha_value < 0 or alpha_value > 1:
                                return "透明度必须在0-1之间"
                            
                            # 调用等效的 !env ALPHA 命令功能
                            self.config["env_alpha"] = alpha_value
                            
                            # 立即更新GUI透明度
                            if self.gui_log:
                                self.gui_log.set_alpha(alpha_value)
                            
                            # 保存配置到文件
                            import json
                            with open("config/config.json", "w", encoding="utf-8") as f:
                                json.dump(self.config, f, indent=4, ensure_ascii=False)
                            
                            return f"ALPHA 已设置为: {alpha_value}"
                        except ValueError:
                            return "透明度值必须为浮点数"
                    else:
                        return "GUI alpha命令参数错误，格式: !gui alpha <float>"
                        
                else:
                    return f"未知的GUI命令: {gui_cmd}，使用 !help 查看帮助"
            else:
                return f"unknown command: {cmd}，使用 !help 查看帮助"
        except Exception as e:
            print(f"[SYS] 命令执行出错: {str(e)}")
            return f"命令执行出错: {str(e)}"

    def _set_video_playback(self, enable):
        """设置视频播放功能的启用状态"""
        self.enable_video_playback = enable
        # 更新配置文件
        self.config["enable_video_playback"] = self.enable_video_playback
        import json
        with open("config/config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        return "启用视频播放" if enable else "禁用视频播放"
    
    def _set_unorthodox(self, enable):
        """设置非正统音乐源功能的启用状态，等效于 !env UNORTHODOX 命令"""
        self.config["env_unorthodox"] = enable
        self.unorthodox_enabled = enable
        
        # 保存配置到文件
        import json
        with open("config/config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        
        status = "已启用" if enable else "已禁用"
        return f"UNORTHODOX {status}"

    def _get_service_status(self):
        """获取当前启用的服务状态"""
        services = ["NeteaseMusic"]  # 网易云音乐服务始终可用
        if self.enable_video_playback:
            services.append("BilibiliVideo")  # 如果视频播放启用，则添加视频服务
        if self.enable_fallback_playlist:
            services.append("FallbackPlaylist")  # 如果随机播放歌单启用，则添加此服务
        if self.unorthodox_enabled:
            services.append("UnorthodoxMusic")  # 如果非正统音乐源启用，则添加此服务
        
        if services:
            return f"功能服务: \n{', \n'.join(services)}"
        else:
            return "功能服务: None"

    async def _get_queue_status(self):
        """获取队列状态"""
        if self.queue_manager.is_empty():
            return "当前队列为空"
        else:
            # 获取队列内容
            queue_list = self.queue_manager.get_queue_list()
            
            # 生成队列详情字符串
            queue_details = [f"当前队列中有 {len(queue_list)} 首歌曲/视频:"]
            for i, item in enumerate(queue_list, 1):
                if isinstance(item, tuple) and len(item) == 3:
                    sid, name, artist = item
                    queue_details.append(f"{i}. {name} - {artist}")
                elif isinstance(item, tuple) and len(item) == 4:
                    # 非正统音乐源
                    song_id, name, artist, audio_url = item
                    queue_details.append(f"{i}. {name} - {artist} (备线源)")
                else:
                    # 视频ID
                    queue_details.append(f"{i}. 视频: {item}")
            
            return "\n".join(queue_details)

    async def _queue_add(self, query):
        """队列增加歌曲"""
        print(f"[ADM] ADMIN: 收到队列添加请求: {query}")
        
        # 解析视频ID，支持多分p格式
        parsed_video_id, p_number = self.parse_bilibili_id(query)
        
        # 检查是否是B站视频ID（先检查原始ID格式，再检查解析后的ID格式）
        if self.is_valid_bilibili_id(query) or self.is_valid_bilibili_id(parsed_video_id):
            if self.queue_manager.size() >= self.queue_maxsize:
                return "点歌队列已满，无法加入"
            
            # 如果有分p信息，构建完整的URL
            if p_number:
                video_url = f"{parsed_video_id}?p={p_number}"
                print(f"[SYS] 解析分p视频: {video_url}")
            else:
                video_url = parsed_video_id
            
            success, msg = await self.queue_manager.add_song(video_url)
            if success:
                return f"入队成功: {video_url} (添加者: ADMIN)"
            else:
                return msg
        else:
            # 尝试解析为歌曲
            sid, name, artist = self.music_bot.get_song_info(query)
            if sid:
                if self.queue_manager.size() >= self.queue_maxsize:
                    return "点歌队列已满，无法加入"
                success, msg = await self.queue_manager.add_song((sid, name, artist))
                if success:
                    return f"入队成功: {name} (添加者: ADMIN)"
                else:
                    return msg
            else:
                return "未找到歌曲或无效的视频ID"

    async def _queue_unorthodox_add(self, query):
        """队列增加歌曲（使用非正统音乐源）"""
        print(f"[ADM] ADMIN: 收到队列添加请求: {query}")
        
        # 检查非正统音乐源是否启用
        if not self.unorthodox_enabled:
            return "备线未启用"
        
        # 检查队列是否已满
        if self.queue_manager.size() >= self.queue_maxsize:
            return "点歌队列已满，无法加入"
        
        # 尝试导入unorthodox模块并使用它搜索音乐
        try:
            from modules.unorthodox import UnorthodoxMusicPlayer
            unorthodox_player = UnorthodoxMusicPlayer()
            await unorthodox_player.initialize()
            result = await unorthodox_player.search_and_get_first_song(query)
            await unorthodox_player.close()
            
            if result:
                song_id, song_name, song_artist, audio_url = result
                # 创建一个包含音频URL的特殊对象，供播放器使用
                unorthodox_item = (song_id, song_name, song_artist, audio_url)
                success, msg = await self.queue_manager.add_song(unorthodox_item)
                if success:
                    return f"入队成功: {song_name} - {song_artist} (添加者: ADMIN)"
                else:
                    return msg
            else:
                return "未找到歌曲"
        except ImportError:
            return "模块未找到，请确保unorthodox.py文件存在"
        except Exception as e:
            # print(f"[SYS] 搜索失败: {str(e)}")
            return f"搜索失败: {str(e)}"

    async def _queue_del(self, index):
        """删除队列指定位置的歌曲"""
        if index < 1 or index > self.queue_maxsize:
            return f"歌曲序号必须在1-{self.queue_maxsize}之间"
        
        if self.queue_manager.is_empty():
            return "当前队列为空，无法删除"
        
        queue_list = self.queue_manager.get_queue_list()
        if index > len(queue_list):
            return f"队列中只有 {len(queue_list)} 首歌曲，无法删除第 {index} 首"
        
        success, deleted_item = await self.queue_manager.remove_song_at_index(index - 1)
        
        if success:
            if isinstance(deleted_item, tuple) and len(deleted_item) == 3:
                sid, name, artist = deleted_item
                return f"已删除第 {index} 首歌曲: {name} - {artist}"
            elif isinstance(deleted_item, tuple) and len(deleted_item) == 4:
                # 非正统音乐源项目
                song_id, song_name, song_artist, audio_url = deleted_item
                return f"已删除第 {index} 首歌曲: {song_name} - {song_artist} (备线源)"
            else:
                return f"已删除第 {index} 个视频: {deleted_item}"
        else:
            return "删除失败"

    async def _queue_clr(self):
        """清除队列"""
        cleared_count = await self.queue_manager.clear_queue()
        return f"已清空队列，共删除 {cleared_count} 首歌曲/视频"