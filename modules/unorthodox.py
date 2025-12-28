import asyncio
from playwright.async_api import async_playwright
import json
import re
from urllib.parse import urljoin
import sys
import subprocess
import os
import platform

class UnorthodoxMusicPlayer:
    """
    集成MPV播放功能的备用音乐线路测试工具
    用于验证从music.pjmp3.com获取音乐资源并使用MPV播放的可行性
    """
    
    def __init__(self):
        self.base_url = "https://music.pjmp3.com"
        self.browser = None
        self.context = None
        self.page = None
        self.mpv_path = self._find_mpv_path()
    
    def _find_mpv_path(self):
        """
        自动查找MPV播放器路径
        """
        # 获取当前文件所在目录的父目录（即项目根目录）
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)  # ./modules/unorthodox.py -> ./
        
        # 检测操作系统类型
        if platform.system() == "Windows":
            # Windows平台，查找mpv.exe
            possible_paths = [
                os.path.join(project_root, "mpv.exe"),         # 根目录/
                os.path.join(project_root, "mpv", "mpv.exe"),  # 根目录/mpv/
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    # print(f"[SYS] 找到MPV播放器: {path}")
                    return path
        else:
            # Unix-like系统，查找mpv可执行文件
            possible_paths = [
                os.path.join(project_root, "mpv"),           # 根目录/mpv
                os.path.join(project_root, "mpv", "mpv"),   # 根目录/mpv/mpv
                os.path.join(project_root, "./mpv"),         # 根目录/./mpv
            ]
            for path in possible_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    # print(f"[SYS] 找到MPV播放器: {path}")
                    return path
        
        # 如果没有找到本地MPV，则返回默认路径
        # print("[SYS] 未找到本地MPV，将尝试使用系统MPV")
        return "mpv"
    
    async def initialize(self):
        """初始化Playwright浏览器"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # 设为True可无头运行
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            self.page = await self.context.new_page()
            return True
        except Exception as e:
            print(f"[SYS] 初始化浏览器失败: {e}")
            return False
    
    async def search_song(self, keyword):
        """搜索歌曲"""
        try:
            search_url = f"{self.base_url}/search.php?keyword={keyword}"
            print(f"[SYS] 正在处理...(1/3)")
            
            await self.page.goto(search_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)  # 等待页面加载
            
            # 查找搜索结果
            search_results = await self.page.query_selector_all("a.search-result-list-item")
            
            # print(f"[SYS] 找到 {len(search_results)} 个搜索结果")
            
            results = []
            for i, result in enumerate(search_results[:5]):  # 只取前5个结果
                try:
                    # 获取歌曲信息
                    title_elem = await result.query_selector(".search-result-list-item-left-song")
                    artist_elem = await result.query_selector(".search-result-list-item-left-singer")
                    
                    title = await title_elem.inner_text() if title_elem else "未知歌曲"
                    artist = await artist_elem.inner_text() if artist_elem else "未知歌手"
                    
                    # 获取链接
                    href = await result.get_attribute("href")
                    if href:
                        full_url = urljoin(self.base_url, href)
                        results.append({
                            'title': title,
                            'artist': artist,
                            'url': full_url,
                            'index': i+1
                        })
                        # print(f"[SYS] {i+1}. {title} - {artist}")
                    else:
                        # print(f"[SYS] {i+1}. 找到结果但无链接")
                        continue
                except Exception as e:
                    # print(f"[SYS] 处理搜索结果 {i+1} 时出错: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"[SYS] 搜索过程中出错: {e}")
            # 输出页面内容用于调试
            content = await self.page.content()
            print("[SYS] 页面内容片段:")
            print(content[:1000])
            return []
    
    async def get_audio_url(self, song_page_url):
        """从歌曲页面获取音频URL"""
        try:
            print(f"[SYS] 正在处理...(2/3)")
            await self.page.goto(song_page_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)  # 等待页面加载
            
            # 执行JavaScript获取音频信息
            try:
                audio_data = await self.page.evaluate("""
                    () => {
                        if (typeof ap !== 'undefined' && ap.options && ap.options.audio) {
                            return ap.options.audio;
                        } else {
                            return null;
                        }
                    }
                """)
                
                if audio_data:
                    print("[SYS] 正在处理...(3/3)")
                    if isinstance(audio_data, list) and len(audio_data) > 0:
                        audio_info = audio_data[0]
                        # print(f"[SYS]   歌曲: {audio_info.get('name', '未知')}")
                        # print(f"[SYS]   歌手: {audio_info.get('artist', '未知')}")
                        # print(f"[SYS]   封面: {audio_info.get('cover', '无')}")
                        # print(f"[SYS]   音频URL: {audio_info.get('url', '无')}")
                        
                        return audio_info.get('url', None)
                    else:
                        # print(f"[SYS]   返回数据格式: {type(audio_data)}")
                        # print(f"[SYS]   返回数据: {audio_data}")
                        return None
                else:
                    print("[SYS] 未能获取音频信息")
                    # 输出页面内容用于调试
                    content = await self.page.content()
                    print("[SYS] 页面内容片段:")
                    print(content[:1000])
                    
            except Exception as e:
                print(f"[SYS] 执行JavaScript获取音频信息时出错: {e}")
                # 输出页面内容用于调试
                content = await self.page.content()
                print("[SYS] 页面内容片段:")
                print(content[:1000])
                
        except Exception as e:
            print(f"[SYS] 获取音频URL过程中出错: {e}")
        
        return None
    
    def play_with_mpv(self, audio_url, title, artist):
        """使用MPV播放音频"""
        try:
            
            # 构建MPV命令
            mpv_args = [
                self.mpv_path,
                '--no-video',  # 仅播放音频
                f'--title={title} - {artist}',  # 设置窗口标题
                '--msg-level=all=no',  # 减少日志输出
                audio_url
            ]
            
            # 根据操作系统设置创建进程的标志
            creationflags = 0
            if platform.system() == 'Windows':
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # 启动MPV播放器
            process = subprocess.Popen(
                mpv_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags
            )
            
            # 等待播放完成
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                print("[SYS] 播放完成")
            else:
                print(f"[SYS] MPV播放器退出，返回码: {process.returncode}")
                if stderr:
                    print(f"[SYS] 错误信息: {stderr.decode()}")
            
            return True
            
        except FileNotFoundError:
            print(f"[SYS] 错误: 找不到MPV播放器 '{self.mpv_path}'")
            print("[SYS] 请确保MPV播放器已正确安装或放置在项目根目录下 (./mpv.exe)")
            return False
        except Exception as e:
            print(f"[SYS] 播放过程中出错: {e}")
            return False
    
    async def search_and_get_first_song(self, keyword):
        """搜索一首歌曲并返回第一个结果的详细信息"""
        
        # 搜索歌曲
        search_results = await self.search_song(keyword)
        
        if not search_results:
            print("[SYS] 未找到搜索结果")
            return None
        
        # 取第一个结果
        first_result = search_results[0]
        # print(f"[SYS] 选择歌曲: {first_result['title']} - {first_result['artist']}")
        
        # 获取音频URL
        audio_url = await self.get_audio_url(first_result['url'])
        
        if audio_url:
            print(f"[SYS] 正在处理...(3/3)")
            # print(f"[SYS] 歌曲: {first_result['title']}")
            # print(f"[SYS] 歌手: {first_result['artist']}")
            # print(f"[SYS] 音频URL: {audio_url}")
            
            # 返回歌曲信息
            return (first_result['index'], first_result['title'], first_result['artist'], audio_url)
        else:
            print(f"[SYS] 获取音频URL失败")
            return None
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

async def main():
    """主函数"""
    # print("[SYS] 正在初始化集成MPV播放功能的备用音乐线路测试工具...")
    
    try:
        tester = UnorthodoxMusicPlayer()
        if await tester.initialize():
            print("[SYS] 初始化成功")
        else:
            print("[SYS] 初始化失败")
    except Exception as e:
        print(f"[SYS] 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())