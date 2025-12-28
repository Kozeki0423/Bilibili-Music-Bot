# main.py
# B站直播间点歌系统主入口

import asyncio
import sys
import threading
import time
from watchdog.observers import Observer

# 导入所有模块
from modules.config_loader import ConfigLoader, ConfigReloadHandler, load_preset_config
from modules.music_bot import MusicBot
from modules.listener import BilibiliListener
from modules.player import Player
from modules.queue_manager import QueueManager
from modules.permission import PermissionManager, WhitelistReloadHandler
from modules.command_handler import CommandHandler
from modules.logger import Logger, HistoryManager
from modules.gui import LogWindow, setup_gui_logging
from modules.utils import check_and_install_requirements, format_system_output, format_admin_output, format_group_output, format_user_output, format_denied_output, is_valid_bilibili_id, parse_bilibili_id, load_fused_keys
from modules.hotkeys import HotkeyManager  # 新增导入

def main():
    # 检查并安装依赖
    check_and_install_requirements()
    
    # 加载配置
    config_loader = ConfigLoader()
    config = config_loader.config
    
    # 初始化预设配置
    preset_config = load_preset_config()
    
    # 初始化各模块
    logger = Logger(config.get("env_log_file", "data/requests.log"))
    history_manager = HistoryManager()
    queue_manager = QueueManager(maxsize=config.get("env_queue_maxsize", 5))
    permission_manager = PermissionManager(config)
    music_bot = MusicBot(
        session_file=config.get("env_session_file", "data/session.ncm"),
        fallback_playlist_id=config.get("env_playlist", 9162892605)
    )
    
    # 初始化GUI
    gui_log = LogWindow(
        title="CLI",
        geometry="400x200",
        alpha=config.get("env_alpha", 1.0)  # 使用原始配置键名
    )
    
    # 初始化播放器
    player = Player(
        mpv_path=config.get("env_mpv_path", "mpv"),
        video_timeout_buffer=config.get("env_video_timeout_buffer", 3)
    )
    
    # 初始化命令处理器 - 传递gui_log参数
    command_handler = CommandHandler(
        player=player,
        queue_manager=queue_manager,
        permission_manager=permission_manager,
        music_bot=music_bot,
        config=config,
        gui_log=gui_log  # 传递GUI对象
    )
    
    # 设置GUI日志输出
    setup_gui_logging(gui_log)
    
    # 初始化快捷键管理器
    hotkey_manager = HotkeyManager(player, queue_manager)
    
    # 定义消息处理回调
    async def handle_message(msg_data):
        raw_content = msg_data.get('text', '')
        content = raw_content.strip()
        user_name = msg_data.get('nickname', '未知')
        
        # 确定用户类型
        if permission_manager.is_admin(user_name):
            user_prefix = "ADM"
            print(format_admin_output(user_name, content))
        elif permission_manager.has_permission(user_name):
            user_prefix = "GRP"
            print(format_group_output(user_name, content))
        else:
            user_prefix = "USR"
            print(format_user_output(user_name, content))
        
        # 检查管理员密钥
        is_valid, result = permission_manager.is_valid_admin_key(content)
        if is_valid:
            admin_key = result
            if user_name not in permission_manager.admins:
                permission_manager.add_admin(user_name)
                print(format_system_output(f"{user_name} 成为管理员"))
                permission_manager.save_fused_key(admin_key)
                print(format_system_output(f"{admin_key} 熔断"))
            else:
                print(format_system_output(f"{user_name} 已经是管理员"))
            return  
        
        # 检查是否是命令
        if content.startswith('!'):
            result = await command_handler.handle_command(user_name, content)
            if result:
                print(format_system_output(result))
            return
        
        # 检查是否包含"撤销"关键词
        if "撤销" in content:
            removed_count = queue_manager.remove_user_songs(user_name, logger.log_file)
            if removed_count > 0:
                print(format_system_output(f"{user_name} 撤销了 {removed_count} 首歌曲"))
            return
        
        # 统一处理点歌请求（包括音乐和视频）
        if content.startswith(("点歌：", "点歌:")):
            query = content.replace("点歌：", "").replace("点歌:", "").strip()
            if not query: 
                return
            print(format_system_output(f"收到点歌请求: {query} (来自: {user_name})"))
            
            # 检查词典映射
            if query in command_handler.dict_map:
                print(format_system_output(f"完成映射: {query} -> {command_handler.dict_map[query]}"))
                query = command_handler.dict_map[query]
            
            # 检查用户权限
            has_perm = permission_manager.check_user_temp_grant(user_name)
            
            if not has_perm:
                print(format_system_output(f"{user_name} 's request aborted: Permission denied"))
                return
            
            # 检查是否是B站视频ID
            parsed_video_id, p_number = parse_bilibili_id(query)
            
            if is_valid_bilibili_id(parsed_video_id) and config.get("enable_video_playback", True):
                # 处理视频ID
                if queue_manager.size() >= 5:
                    print(format_system_output("点歌队列已满，无法加入"))
                    return
                # 如果有分p信息，构建完整的URL
                if p_number:
                    video_url = f"{parsed_video_id}?p={p_number}"
                    print(format_system_output(f"解析分p视频: {video_url}"))
                else:
                    video_url = parsed_video_id
                success, msg = await queue_manager.add_song(video_url)
                if success:
                    print(format_system_output(f"入队成功: {video_url} (点歌者: {user_name})"))
                    # 记录成功的视频请求
                    logger.log_video_request(user_name, video_url)
                    # 扣减临时次数（仅对非白名单、非时间许可用户）
                    if (not permission_manager.has_permission(user_name) and
                        permission_manager.grant_until_time <= time.time() and
                        user_name in permission_manager.temp_grant_counts):
                        permission_manager.use_temp_grant(user_name)
            else:
                # 处理音乐搜索
                sid, name, artist = music_bot.get_song_info(query)
                if sid:
                    # 对网易云音乐进行查重检查在add_song方法中完成
                    success, msg = await queue_manager.add_song((sid, name, artist))
                    if success:
                        print(format_system_output(f"入队成功: {name} (点歌者: {user_name})"))
                        # 记录成功的点歌请求
                        logger.log_request(user_name, name, artist)
                        # 扣减临时次数（仅对非白名单、非时间许可用户）
                        if (not permission_manager.has_permission(user_name) and
                            permission_manager.grant_until_time <= time.time() and
                            user_name in permission_manager.temp_grant_counts):
                            permission_manager.use_temp_grant(user_name)
                    else:
                        print(format_system_output(msg))  # 输出查重或队列满的错误信息
                else:
                    print(format_system_output("未找到歌曲或无效的视频ID"))

    # 初始化监听器
    listener = BilibiliListener(
        room_id=config.get("env_roomid", 1896163590),
        callback=handle_message,
        poll_interval=config.get("env_poll_interval", 5)
    )
    
    # 启动配置热重载监听
    observer = Observer()
    observer.schedule(
        ConfigReloadHandler(config_loader, lambda new_config: update_config(new_config, gui_log, player, permission_manager, command_handler)),
        path="config",
        recursive=False
    )
    # 启动白名单热重载监听
    observer.schedule(
        WhitelistReloadHandler(permission_manager),
        path="config",
        recursive=False
    )
    observer.start()
    
    # 启动播放器
    def start_player():
        asyncio.run(
            player.start_player(
                queue_manager.song_queue,
                music_bot,
                config.get("enable_fallback_playlist", True),
                config.get("env_playlist", 9162892605)
            )
        )
    
    # 启动快捷键监听器
    def start_hotkeys():
        hotkey_manager.start_listening()
    
    # 启动播放器线程
    player_thread = threading.Thread(target=start_player, daemon=True)
    player_thread.start()
    
    # 启动快捷键监听线程
    hotkey_thread = threading.Thread(target=start_hotkeys, daemon=True)
    hotkey_thread.start()
    
    # 启动监听器
    def start_listener():
        asyncio.run(listener.start())
    
    listener_thread = threading.Thread(target=start_listener, daemon=True)
    listener_thread.start()
    
    # 更新配置的回调函数
    def update_config(new_config, gui_log, player, permission_manager, command_handler):
        # 更新GUI透明度
        alpha = new_config.get("env_alpha", 1.0)  # 使用原始配置键名
        gui_log.set_alpha(alpha)
        # 更新管理员列表
        permission_manager.admins = set(new_config.get("env_default_admins", ["磕磕绊绊学语文", "琴吹炒面"]))
        # 更新权限管理器配置
        permission_manager.config = new_config
        permission_manager.admin_password = new_config.get("env_admin_password", "mysecret")
        # 更新播放器配置
        player.video_timeout_buffer = new_config.get("env_video_timeout_buffer", 3)
        # 更新命令处理器配置
        command_handler.config.update(new_config)
        command_handler.fallback_playlist_id = new_config.get("env_playlist", 9162892605)
        command_handler.enable_video_playback = new_config.get("enable_video_playback", True)
        command_handler.video_timeout_buffer = new_config.get("env_video_timeout_buffer", 3)
        command_handler.enable_fallback_playlist = new_config.get("enable_fallback_playlist", True)
        command_handler.queue_maxsize = new_config.get("env_queue_maxsize", 5)
        # 重新加载词典映射
        command_handler.dict_map = command_handler.load_dict_map()
        print("[SYS] 配置已热重载")
    
    # 启动GUI
    try:
        gui_log.run()
    except KeyboardInterrupt:
        print(format_system_output("程序被用户中断"))
    finally:
        print("[SYS] 停止快捷键监听器...")
        hotkey_manager.stop_listening()
        print("[SYS] 停止看门狗监听器...")
        observer.stop()
        observer.join()
        print("[SYS] 看门狗监听器已停止")

if __name__ == '__main__':
    main()