# modules/player.py
# MPV播放器控制模块

import asyncio
import subprocess
import os
import platform
import tempfile
import time
import yt_dlp

class Player:
    def __init__(self, mpv_path="mpv", video_timeout_buffer=3):
        self.mpv_path = mpv_path
        self.video_timeout_buffer = video_timeout_buffer
        self.current_mpv_process = None
        self.mpv_ipc_path = None
        self.current_volume = 100
        self.current_playing = None
        self.current_timer_task = None
        self.play_history = []
        self.max_history = 50
    
    def get_mpv_path(self):
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
        
        # 如果没有找到本地MPV，则返回默认路径
        print(f"未找到本地MPV，使用配置路径: {self.mpv_path}")
        return self.mpv_path

    async def send_mpv_command(self, command):
        """向 MPV 发送 IPC 命令"""
        if not self.mpv_ipc_path or not self.current_mpv_process or self.current_mpv_process.returncode is not None:
            print(f"[{'SYS':>3}] MPV 未运行，无法发送命令")
            return False

        try:
            if platform.system() == "Windows":
                # Windows 使用命名管道
                import win32file, win32pipe, pywintypes
                try:
                    handle = win32file.CreateFile(
                        self.mpv_ipc_path,
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
                    sock.connect(self.mpv_ipc_path)
                    sock.sendall((command + '\n').encode('utf-8'))
                    sock.close()
                    return True
                except Exception as e:
                    print(f"[{'SYS':>3}] IPC 连接失败: {e}")
                    return False
        except Exception as e:
            print(f"[{'SYS':>3}] 发送 MPV 命令出错: {e}")
            return False

    def terminate_mpv_process(self, process):
        """终止MPV进程及其子进程"""
        if process is None or process.returncode is not None:
            return
            
        try:
            if platform.system() == "Windows":
                # Windows: 使用taskkill终止进程树
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Unix-like: 使用psutil终止进程树
                import psutil
                try:
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    parent.terminate()
                    
                    # 等待进程结束，超时则强制杀死
                    gone, alive = psutil.wait_procs([parent] + children, timeout=3)
                    for p in alive:
                        try:
                            p.kill()
                        except psutil.NoSuchProcess:
                            pass
                except psutil.NoSuchProcess:
                    pass
        except ImportError:
            # 如果没有psutil，使用标准方法
            try:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            except ProcessLookupError:
                pass  # 进程已经结束
        except Exception as e:
            print(f"[{'SYS':>3}] 终止MPV进程时出错: {e}")

    def get_video_duration(self, video_url):
        """使用yt-dlp获取视频时长"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                duration = info.get('duration', None)
                if duration is not None:
                    return duration
                else:
                    print(f"[{'SYS':>3}] 无法获取视频时长")
                    return 0
        except Exception as e:
            print(f"[{'SYS':>3}] 获取视频时长失败: {e}")
            return 60

    async def video_timer(self, duration, video_id):
        """视频播放计时器，超时后自动终止MPV进程"""
        print(f"[{'SYS':>3}] 视频时长: {duration}s")
        
        # 等待指定时间，但检查是否播放已被跳过
        start_time = time.time()
        remaining = duration + self.video_timeout_buffer  # 增加配置的容错时间
        
        while remaining > 0:
            await asyncio.sleep(0.5)
            elapsed = time.time() - start_time
            remaining = duration + self.video_timeout_buffer - elapsed
            
            # 检查MPV进程是否还存在
            if self.current_mpv_process and self.current_mpv_process.returncode is not None:
                print(f"[{'SYS':>3}] MPV进程已结束，计时器停止")
                break
        
        # 如果进程仍在运行，强制终止
        if self.current_mpv_process and self.current_mpv_process.returncode is None:
            print(f"[{'SYS':>3}] exit(1)")
            await self.send_mpv_command('quit')
            await asyncio.sleep(0.5)
            self.terminate_mpv_process(self.current_mpv_process)
        else:
            print(f"[{'SYS':>3}] exit(0)")

    async def play_audio(self, song_item, music_bot=None):
        """播放音频或视频"""
        # 取消之前的计时器任务
        if self.current_timer_task and not self.current_timer_task.done():
            self.current_timer_task.cancel()
            try:
                await self.current_timer_task
            except asyncio.CancelledError:
                pass

        # 检查是否是视频ID
        if isinstance(song_item, tuple) and len(song_item) == 3:
            # 普通网易云音乐
            sid, name, artist = song_item
            self.current_playing = (sid, name, artist)  # 更新当前播放
            print(f"[{'SYS':>3}] 正在解析: {name} - {artist}")
            
            if music_bot:
                mp3_url = music_bot.get_song_url(sid)
                if not mp3_url:
                    print(f"[{'SYS':>3}] 解析失败 跳过")
                    self.current_playing = None
                    return

                print(f"[{'SYS':>3}] 启动 MPV: {name}")

                # 构建 MPV 参数
                mpv_args = [
                    self.mpv_path,
                    '--no-video',  # 仅播放音频
                    '--idle=no',
                    f'--input-ipc-server={self.mpv_ipc_path}',
                    f'--volume={self.current_volume}',  # 设置当前音量
                    '--msg-level=all=no',  # 减少日志
                    mp3_url
                ]

                creationflags = 0
                if platform.system() == 'win32':
                    creationflags = subprocess.CREATE_NO_WINDOW

                self.current_mpv_process = await asyncio.create_subprocess_exec(
                    *mpv_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags
                )
        elif isinstance(song_item, tuple) and len(song_item) == 4:
            # 非正统音乐源
            song_id, name, artist, audio_url = song_item
            self.current_playing = (song_id, name, artist)  # 更新当前播放
            print(f"[{'SYS':>3}] 正在解析: {name} - {artist}")
            
            print(f"[{'SYS':>3}] 启动 MPV: {name}")

            # 构建 MPV 参数 - 直接播放音频URL
            mpv_args = [
                self.mpv_path,
                '--no-video',  # 仅播放音频
                '--idle=no',
                f'--input-ipc-server={self.mpv_ipc_path}',
                f'--volume={self.current_volume}',  # 设置当前音量
                '--msg-level=all=no',  # 减少日志
                audio_url
            ]

            creationflags = 0
            if platform.system() == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW

            self.current_mpv_process = await asyncio.create_subprocess_exec(
                *mpv_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags
            )
        else:
            # 处理视频ID
            video_id = song_item
            self.current_playing = (None, f"{video_id}", "")  # 更新当前播放
            print(f"[{'SYS':>3}] 正在播放: {video_id}")

            # 构建视频播放URL
            video_url = f"https://www.bilibili.com/video/{video_id}"
            
            # 获取视频时长
            duration = self.get_video_duration(video_url)
            
            # 启动计时器任务
            self.current_timer_task = asyncio.create_task(self.video_timer(duration, video_id))
            
            # 构建 MPV 参数 - 播放视频，但仅提取音频
            mpv_args = [
                self.mpv_path,
                '--no-video',  # 仅播放音频，忽略画面
                '--idle=yes',  # 保持播放器空闲状态，直到播放完成
                f'--input-ipc-server={self.mpv_ipc_path}',
                f'--volume={self.current_volume}',  # 设置当前音量
                '--msg-level=all=no',  # 减少日志
                '--ytdl=yes',  # 启用youtube-dl支持，用于处理B站视频
                '--cache=yes',  # 启用缓存
                '--demuxer-max-bytes=50MiB',  # 增加缓冲区大小
                '--demuxer-max-back-bytes=25MiB',  # 增加回退缓冲区
                video_url
            ]

            creationflags = 0
            if platform.system() == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW

            self.current_mpv_process = await asyncio.create_subprocess_exec(
                *mpv_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags
            )

        # 等待播放完成
        try:
            await self.current_mpv_process.wait()
        except Exception as e:
            print(f"[{'SYS':>3}] 等待MPV进程结束时出错: {e}")
        
        # 取消计时器任务（如果还在运行）
        if self.current_timer_task and not self.current_timer_task.done():
            self.current_timer_task.cancel()
            try:
                await self.current_timer_task
            except asyncio.CancelledError:
                pass
        
        # 获取播放完成的标题
        if isinstance(song_item, tuple) and len(song_item) == 3:
            sid, name, artist = song_item
            print(f"[{'SYS':>3}] 播放结束: {name}")
            # 记录到历史
            from datetime import datetime
            self.play_history.append((sid, name, artist, datetime.now().isoformat()))
            if len(self.play_history) > self.max_history:
                self.play_history.pop(0)  # FIFO
        elif isinstance(song_item, tuple) and len(song_item) == 4:
            # 非正统音乐源
            song_id, name, artist, audio_url = song_item
            print(f"[{'SYS':>3}] 播放结束: {name}")
            # 记录到历史
            from datetime import datetime
            self.play_history.append((song_id, name, artist, datetime.now().isoformat()))
            if len(self.play_history) > self.max_history:
                self.play_history.pop(0)  # FIFO
        else:
            video_id = song_item
            print(f"[{'SYS':>3}] 视频播放结束: {video_id}")

        # 确保进程完全终止
        if self.current_mpv_process:
            self.terminate_mpv_process(self.current_mpv_process)
        
        self.current_mpv_process = None
        self.current_playing = None
        self.current_timer_task = None

    async def start_player(self, song_queue, music_bot=None, enable_fallback_playlist=True, fallback_playlist_id=9162892605):
        """启动播放器主循环"""
        print(f"[{'SYS':>3}] 播放引擎就绪...")
        
        # 创建临时 IPC 路径
        if platform.system() == "Windows":
            self.mpv_ipc_path = r'\\.\pipe\mpv-kozeki'
        else:
            self.mpv_ipc_path = f"/tmp/mpv-kozeki-{os.getpid()}.sock"
            if os.path.exists(self.mpv_ipc_path):
                os.unlink(self.mpv_ipc_path)

        while True:
            try:
                if song_queue.empty():
                    if enable_fallback_playlist:  # 检查是否启用随机播放歌单功能
                        print(f"[{'SYS':>3}] 无请求，随机播放歌单...")
                        if music_bot:
                            song_item = music_bot.get_random_fallback_song()
                            if not song_item or not song_item[0]:
                                print(f"[{'SYS':>3}] 获取失败，10秒后重试...")
                                await asyncio.sleep(10)
                                continue
                    else:
                        print(f"[{'SYS':>3}] 空队列...")
                        await asyncio.sleep(5)
                        continue
                else:
                    print(f"[{'SYS':>3}] 准备播放点歌 (剩余: {song_queue.qsize()})...")
                    song_item = await song_queue.get()

                await self.play_audio(song_item, music_bot)
                await asyncio.sleep(1)
            except FileNotFoundError:
                print(f"[{'SYS':>3}] 找不到 MPV 播放器: {self.mpv_path}")
                print(f"[{'SYS':>3}] 请确保 MPV 播放器已正确安装或放置在程序根目录下的 'mpv' 文件夹中")
                await asyncio.sleep(10)
            except Exception as e:
                print(f"[{'SYS':>3}] 播放引擎错误: {e}")
                # 取消计时器任务
                if self.current_timer_task and not self.current_timer_task.done():
                    self.current_timer_task.cancel()
                    # 这里需要在异步上下文中处理
                    async def cancel_task():
                        try:
                            await self.current_timer_task
                        except asyncio.CancelledError:
                            pass
                    asyncio.create_task(cancel_task())
                # 确保进程完全终止
                if self.current_mpv_process:
                    self.terminate_mpv_process(self.current_mpv_process)
                self.current_mpv_process = None
                self.current_playing = None
                self.current_timer_task = None
                await asyncio.sleep(5)

    def get_current_playing(self):
        """获取当前播放的歌曲信息"""
        return self.current_playing

    def get_play_history(self, num=5):
        """获取播放历史"""
        return self.play_history[-num:] if self.play_history else []

    def set_volume(self, volume):
        """设置音量"""
        if 0 <= volume <= 100:
            self.current_volume = volume
            if self.current_mpv_process and self.current_mpv_process.returncode is None:
                # 创建一个线程来运行异步任务
                thread = threading.Thread(target=self._run_async_set_volume, args=(volume,))
                thread.daemon = True
                thread.start()
            return True
        return False

    def _run_async_set_volume(self, volume):
        """在新线程中运行异步设置音量操作"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.send_mpv_command(f'set volume {volume}'))
        finally:
            loop.close()

    async def set_volume_async(self, volume):
        """异步设置音量（用于快捷键）"""
        if 0 <= volume <= 100:
            self.current_volume = volume
            if self.current_mpv_process and self.current_mpv_process.returncode is not None:
                print(f"[{'SYS':>3}] MPV进程已结束，无法设置音量")
                return False
            result = await self.send_mpv_command(f'set volume {volume}')
            return result
        return False

    def get_volume(self):
        """获取当前音量"""
        return self.current_volume

    async def pause(self):
        """暂停播放"""
        if self.current_mpv_process and self.current_mpv_process.returncode is not None:
            print(f"[{'SYS':>3}] MPV进程已结束，无法暂停")
            return False
        return await self.send_mpv_command('set pause yes')

    async def resume(self):
        """恢复播放"""
        if self.current_mpv_process and self.current_mpv_process.returncode is not None:
            print(f"[{'SYS':>3}] MPV进程已结束，无法恢复")
            return False
        return await self.send_mpv_command('set pause no')

    async def skip(self):
        """跳过当前播放"""
        if self.current_mpv_process and self.current_mpv_process.returncode is None:
            # 取消计时器任务
            if self.current_timer_task and not self.current_timer_task.done():
                self.current_timer_task.cancel()
                # 异步取消任务
                async def cancel_task():
                    try:
                        await self.current_timer_task
                    except asyncio.CancelledError:
                        pass
                asyncio.create_task(cancel_task())
            # 发送quit命令终止当前播放
            result = await self.send_mpv_command('quit')
            print(f"[{'SYS':>3}] 已跳过当前歌曲")
            return result
        return False