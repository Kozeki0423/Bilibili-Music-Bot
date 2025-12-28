# modules/gui.py
# GUI日志显示模块

import tkinter as tk
from tkinter import scrolledtext
import threading
import asyncio
import sys
import os
from datetime import datetime

class LogWindow:
    def __init__(self, config=None, title="Bilibili Live Music Player", geometry="600x400", alpha=1.0):
        if config is not None:
            self.config = config
        else:
            self.config = {"env_alpha": alpha}
        self.root = None
        self.text_area = None
        self.scroll_bar = None
        self.log_queue = asyncio.Queue()
        self.gui_thread = None
        self.stop_event = threading.Event()
        self.title = title
        self.geometry = geometry
        self.alpha = alpha
        self.command_handler = None
        
        # GUI状态变量
        self.hide_state = 0  # 0为未隐藏，1为隐藏
        self.ignore_state = 0  # 0为不穿透，1为穿透
        self.direct_state = 0  # 0为有边框，1为无边框

    def set_alpha(self, alpha):
        """设置窗口透明度"""
        try:
            if hasattr(self.root, 'wm_attributes'):
                # Windows系统
                if sys.platform.startswith('win'):
                    import platform
                    if platform.system() == "Windows":
                        from ctypes import windll
                        hwnd = windll.user32.GetParent(self.root.winfo_id())
                        alpha_val = int(alpha * 255)
                        # 设置窗口为分层窗口并设置透明度
                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)
                        ex_style |= 0x80000  # WS_EX_LAYERED
                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                else:
                    # Linux/Mac系统
                    self.root.wm_attributes('-alpha', alpha)
        except Exception as e:
            print(f"[SYS] 设置透明度失败: {e}")

    def create_window(self):
        """创建GUI窗口"""
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry(self.geometry)
        
        # 设置窗口属性
        self.root.wm_attributes('-topmost', True)  # 置顶
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置透明度 - 优先使用配置中的值，如果不存在则使用构造函数传入的alpha值
        alpha = self.config.get("env_alpha", self.alpha)
        self.set_alpha(alpha)
        self.root.attributes("-alpha", self.alpha)
        
        # 创建文本显示区域
        self.text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state='disabled',
            bg='black',
            fg='white',
            font=('Consolas', 10)
        )
        self.text_area.pack(expand=True, fill='both', padx=5, pady=5)
        
        # 不创建输入框和发送按钮，保持窗口简洁

    def on_closing(self):
        """窗口关闭事件"""
        self.stop_event.set()
        if self.gui_thread:
            self.gui_thread.join(timeout=1)
        self.root.destroy()
        os._exit(0)  # 强制退出程序

    def set_ignore(self, ignore):
        """设置窗口穿透状态"""
        try:
            if ignore:
                # 启用穿透
                if sys.platform.startswith('win'):
                    import platform
                    if platform.system() == "Windows":
                        from ctypes import windll
                        hwnd = windll.user32.GetParent(self.root.winfo_id())
                        
                        # 设置窗口样式为穿透
                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                        ex_style |= 0x20  # WS_EX_TRANSPARENT
                        ex_style |= 0x80000  # WS_EX_LAYERED
                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                        
                        # 重新设置透明度 - 使用配置中的值
                        alpha = self.config.get("env_alpha", self.alpha)
                        alpha_val = int(alpha * 255)
                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                        
                        self.ignore_state = 1
                else:
                    # Linux/Mac系统可能需要不同的处理方式
                    self.root.wm_attributes('-transparentcolor', 'white')
            else:
                # 禁用穿透
                if sys.platform.startswith('win'):
                    import platform
                    if platform.system() == "Windows":
                        from ctypes import windll
                        hwnd = windll.user32.GetParent(self.root.winfo_id())
                        
                        # 移除窗口穿透样式
                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                        ex_style &= ~0x20  # 移除 WS_EX_TRANSPARENT
                        # ex_style &= ~0x80000  # 移除 WS_EX_LAYERED
                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                        
                        # 恢复透明度 - 使用配置中的值
                        alpha = self.config.get("env_alpha", self.alpha)
                        alpha_val = int(alpha * 255)
                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                        self.set_alpha(alpha)
                        self.root.attributes("-alpha", self.alpha)
                        
                        self.ignore_state = 0
                        
                else:
                    # Linux/Mac系统取消透明色
                    self.root.wm_attributes('-transparentcolor', '')
        except Exception as e:
            print(f"[SYS] 设置穿透状态失败: {e}")

    def set_direct(self, direct):
        """设置窗口无边框状态"""
        try:
            if direct:
                # 设置无边框
                self.root.overrideredirect(True)
                self.direct_state = 1
            else:
                # 恢复边框
                self.root.overrideredirect(False)
                self.direct_state = 0
        except Exception as e:
            print(f"[SYS] 设置边框状态失败: {e}")

    def add_log(self, message):
        """添加日志到队列"""
        # 如果队列满了，移除旧的日志
        if self.log_queue.qsize() > 1000:  # 限制队列大小
            try:
                self.log_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self.log_queue.put_nowait(message)

    async def update_log_display(self):
        """异步更新日志显示"""
        while not self.stop_event.is_set():
            try:
                # 使用短超时时间，以便及时响应停止事件
                message = await asyncio.wait_for(self.log_queue.get(), timeout=0.1)
                timestamp = datetime.now().strftime('%H:%M:%S')
                # formatted_message = f"[{timestamp}] {message}\n"
                formatted_message = f"{message}\n"
                
                # 在GUI线程中更新文本区域
                self.root.after(0, self._update_text_area, formatted_message)
            except asyncio.TimeoutError:
                continue  # 继续检查停止事件

    def _update_text_area(self, message):
        """在GUI线程中更新文本区域"""
        if self.text_area:
            self.text_area.configure(state='normal')
            self.text_area.insert(tk.END, message)
            self.text_area.see(tk.END)  # 自动滚动到最新消息
            self.text_area.configure(state='disabled')

    def run(self):
        """运行GUI"""
        if not self.root:
            self.create_window()
        
        # 启动异步日志更新任务
        async def run_async_tasks():
            await self.update_log_display()
        
        # 在独立线程中运行异步任务
        def async_thread():
            asyncio.run(run_async_tasks())
        
        self.gui_thread = threading.Thread(target=async_thread, daemon=True)
        self.gui_thread.start()
        
        # 启动GUI主循环
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

    def get_window_info(self):
        """获取窗口信息"""
        if self.root:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            # 优先使用配置中的alpha值
            alpha = self.config.get("env_alpha", self.alpha)
            ignore_status = "穿透" if self.ignore_state == 1 else "非穿透"
            hide_status = "隐藏" if self.hide_state == 1 else "显示"
            direct_status = "无边框" if self.direct_state == 1 else "有边框"
            
            info = {
                "screen_size": (screen_w, screen_h),
                "window_size": (w, h),
                "window_pos": (x, y),
                "alpha": alpha,
                "ignore_status": self.ignore_state,
                "hide_status": self.hide_state,
                "direct_status": self.direct_state
            }
            return info
        return None

def setup_gui_logging(gui_log_instance):
    """设置GUI日志记录系统"""
    import sys
    import io
    
    class GUILogger(io.StringIO):
        def __init__(self, gui_log):
            super().__init__()
            self.gui_log = gui_log

        def write(self, s):
            if s.strip():  # 只记录非空内容
                self.gui_log.add_log(s.strip())
            return super().write(s)

    # 创建GUI记录器并重定向stdout
    gui_logger = GUILogger(gui_log_instance)
    sys.stdout = gui_logger
    sys.stderr = gui_logger

# 保留原有的GUILog类作为备用实现
class GUILog:
    def __init__(self, config):
        self.config = config
        self.root = None
        self.text_area = None
        self.scroll_bar = None
        self.log_queue = asyncio.Queue()
        self.gui_thread = None
        self.stop_event = threading.Event()
        self.command_handler = None
        
        # GUI状态变量
        self.hide_state = 0  # 0为未隐藏，1为隐藏
        self.ignore_state = 0  # 0为不穿透，1为穿透
        self.direct_state = 0  # 0为有边框，1为无边框

    def set_alpha(self, alpha):
        """设置窗口透明度"""
        try:
            if hasattr(self.root, 'wm_attributes'):
                # Windows系统
                if sys.platform.startswith('win'):
                    import platform
                    if platform.system() == "Windows":
                        from ctypes import windll
                        hwnd = windll.user32.GetParent(self.root.winfo_id())
                        alpha_val = int(alpha * 255)
                        # 设置窗口为分层窗口并设置透明度
                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)
                        ex_style |= 0x80000  # WS_EX_LAYERED
                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                else:
                    # Linux/Mac系统
                    self.root.wm_attributes('-alpha', alpha)
        except Exception as e:
            print(f"[SYS] 设置透明度失败: {e}")

    def create_window(self):
        """创建GUI窗口"""
        self.root = tk.Tk()
        self.root.title("Bilibili Live Music Player")
        self.root.geometry("600x400")
        
        # 设置窗口属性
        self.root.wm_attributes('-topmost', True)  # 置顶
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置透明度
        alpha = self.config.get("env_alpha", 1.0)
        self.set_alpha(alpha)
        
        # 创建文本显示区域
        self.text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state='disabled',
            bg='black',
            fg='white',
            font=('Consolas', 10)
        )
        self.text_area.pack(expand=True, fill='both', padx=5, pady=5)
        
        # 不创建输入框和发送按钮，保持窗口简洁

    def on_closing(self):
        """窗口关闭事件"""
        self.stop_event.set()
        if self.gui_thread:
            self.gui_thread.join(timeout=1)
        self.root.destroy()
        os._exit(0)  # 强制退出程序

    def set_ignore(self, ignore):
        """设置窗口穿透状态"""
        try:
            if ignore:
                # 启用穿透
                if sys.platform.startswith('win'):
                    import platform
                    if platform.system() == "Windows":
                        from ctypes import windll
                        hwnd = windll.user32.GetParent(self.root.winfo_id())
                        
                        # 设置窗口样式为穿透
                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                        ex_style |= 0x20  # WS_EX_TRANSPARENT
                        ex_style |= 0x80000  # WS_EX_LAYERED
                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                        
                        # 重新设置透明度
                        alpha = self.config.get("env_alpha", 1.0)
                        alpha_val = int(alpha * 255)
                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                        
                        self.ignore_state = 1
                else:
                    # Linux/Mac系统可能需要不同的处理方式
                    self.root.wm_attributes('-transparentcolor', 'white')
            else:
                # 禁用穿透
                if sys.platform.startswith('win'):
                    import platform
                    if platform.system() == "Windows":
                        from ctypes import windll
                        hwnd = windll.user32.GetParent(self.root.winfo_id())
                        
                        # 移除窗口穿透样式
                        ex_style = windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                        ex_style &= ~0x20  # 移除 WS_EX_TRANSPARENT
                        ex_style &= ~0x80000  # 移除 WS_EX_LAYERED
                        windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                        
                        # 恢复透明度
                        alpha = self.config.get("env_alpha", 1.0)
                        alpha_val = int(alpha * 255)
                        windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, 2)
                        
                        self.ignore_state = 0
                else:
                    # Linux/Mac系统取消透明色
                    self.root.wm_attributes('-transparentcolor', '')
        except Exception as e:
            print(f"[SYS] 设置穿透状态失败: {e}")

    def set_direct(self, direct):
        """设置窗口无边框状态"""
        try:
            if direct:
                # 设置无边框
                self.root.overrideredirect(True)
                self.direct_state = 1
            else:
                # 恢复边框
                self.root.overrideredirect(False)
                self.direct_state = 0
        except Exception as e:
            print(f"[SYS] 设置边框状态失败: {e}")

    def add_log(self, message):
        """添加日志到队列"""
        # 如果队列满了，移除旧的日志
        if self.log_queue.qsize() > 1000:  # 限制队列大小
            try:
                self.log_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self.log_queue.put_nowait(message)

    async def update_log_display(self):
        """异步更新日志显示"""
        while not self.stop_event.is_set():
            try:
                # 使用短超时时间，以便及时响应停止事件
                message = await asyncio.wait_for(self.log_queue.get(), timeout=0.1)
                timestamp = datetime.now().strftime('%H:%M:%S')
                formatted_message = f"[{timestamp}] {message}\n"
                
                # 在GUI线程中更新文本区域
                self.root.after(0, self._update_text_area, formatted_message)
            except asyncio.TimeoutError:
                continue  # 继续检查停止事件

    def _update_text_area(self, message):
        """在GUI线程中更新文本区域"""
        if self.text_area:
            self.text_area.configure(state='normal')
            self.text_area.insert(tk.END, message)
            self.text_area.see(tk.END)  # 自动滚动到最新消息
            self.text_area.configure(state='disabled')

    def run(self):
        """运行GUI"""
        if not self.root:
            self.create_window()
        
        # 启动异步日志更新任务
        async def run_async_tasks():
            await self.update_log_display()
        
        # 在独立线程中运行异步任务
        def async_thread():
            asyncio.run(run_async_tasks())
        
        self.gui_thread = threading.Thread(target=async_thread, daemon=True)
        self.gui_thread.start()
        
        # 启动GUI主循环
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

    def get_window_info(self):
        """获取窗口信息"""
        if self.root:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            alpha = self.config.get("env_alpha", 1.0)
            ignore_status = "穿透" if self.ignore_state == 1 else "非穿透"
            hide_status = "隐藏" if self.hide_state == 1 else "显示"
            direct_status = "无边框" if self.direct_state == 1 else "有边框"
            
            info = {
                "screen_size": (screen_w, screen_h),
                "window_size": (w, h),
                "window_pos": (x, y),
                "alpha": alpha,
                "ignore_status": self.ignore_state,
                "hide_status": self.hide_state,
                "direct_status": self.direct_state
            }
            return info
        return None