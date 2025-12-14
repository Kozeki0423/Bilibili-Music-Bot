import sys
import json
import subprocess
import os
from datetime import datetime
import psutil

# 检查环境
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QTabWidget, QFrame, QFormLayout, QLabel, QLineEdit, QPushButton, 
        QListWidget, QGroupBox, QScrollArea, QMessageBox, QInputDialog, QSlider,
        QCheckBox  # 新增复选框
    )
    from PyQt5.QtCore import Qt, QSize
    from PyQt5.QtGui import QPixmap, QPalette, QColor, QFont, QIcon
except ImportError:
    import subprocess
    import sys
    print("正在安装PyQt5库...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt5"])
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
            QTabWidget, QFrame, QFormLayout, QLabel, QLineEdit, QPushButton, 
            QListWidget, QGroupBox, QScrollArea, QMessageBox, QInputDialog, QSlider,
            QCheckBox  # 新增复选框
        )
        from PyQt5.QtCore import Qt, QSize
        from PyQt5.QtGui import QPixmap, QPalette, QColor, QFont, QIcon
        print("PyQt5安装成功！")
    except Exception as e:
        print(f"PyQt5安装失败: {e}")
        input("按回车键退出...")  # 暂挂终端以便查看错误信息
        sys.exit(1)

try:
    import psutil
except ImportError:
    import subprocess
    import sys
    print("正在安装psutil库...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
        print("psutil安装成功！")
    except Exception as e:
        print(f"psutil安装失败: {e}")
        input("按回车键退出...")  # 暂挂终端以便查看错误信息
        sys.exit(1)

class ConfigManager:
    def __init__(self):
        self.config_path = "config/config.json"
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
            "env_alpha": 1.0,
            "enable_video_playback": True,  # 新增视频播放功能开关
            "env_video_timeout_buffer": 3  # 新增视频播放超时容错时间（秒）
        }
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = self.default_config.copy()
            # 确保config目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            self.save_config()
    
    def save_config(self):
        # 确保config目录存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
    
    def update_config(self, key, value):
        self.config[key] = value
        self.save_config()

class WhitelistManager:
    def __init__(self, whitelist_file="config/whitelist.json"):
        self.whitelist_file = whitelist_file
        self.load_whitelist()
    
    def load_whitelist(self):
        if os.path.exists(self.whitelist_file):
            with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.allowed_users = set(data.get('allowed_users', []))
        else:
            # 确保config目录存在
            os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
            self.allowed_users = set()
    
    def save_whitelist(self):
        data = {
            'allowed_users': list(self.allowed_users),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # 确保config目录存在
        os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
        with open(self.whitelist_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_user(self, username):
        if username not in self.allowed_users:
            self.allowed_users.add(username)
            self.save_whitelist()
            return True
        return False
    
    def remove_user(self, username):
        if username in self.allowed_users:
            self.allowed_users.remove(username)
            self.save_whitelist()
            return True
        return False
    
    def get_users(self):
        return sorted(list(self.allowed_users))

class AdminManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.load_admins()
    
    def load_admins(self):
        self.admins = set(self.config_manager.config.get('env_default_admins', ["琴吹炒面"]))
    
    def save_admins(self):
        self.config_manager.update_config('env_default_admins', list(self.admins))
    
    def add_admin(self, username):
        if username not in self.admins:
            self.admins.add(username)
            self.save_admins()
            return True
        return False
    
    def remove_admin(self, username):
        if username in self.admins:
            self.admins.remove(username)
            self.save_admins()
            return True
        return False
    
    def get_admins(self):
        return sorted(list(self.admins))

class SemiTransparentWidget(QWidget):
    def __init__(self, parent=None, config_manager=None, whitelist_manager=None, admin_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.whitelist_manager = whitelist_manager
        self.admin_manager = admin_manager
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #C0C0C0;
                background: rgba(255, 255, 255, 200);
            }
            QTabBar::tab {
                background: rgba(240, 240, 240, 150);
                padding: 12px;
                margin: 3px;
                font-size: 16px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: rgba(255, 255, 255, 200);
            }
        """)
        
        # 基础设置选项卡
        self.basic_tab = QWidget()
        self.create_basic_settings()
        self.tab_widget.addTab(self.basic_tab, "基础设置")
        
        # 高级设置选项卡
        self.advanced_tab = QWidget()
        self.create_advanced_settings()
        self.tab_widget.addTab(self.advanced_tab, "高级设置")
        
        # 白名单管理选项卡
        self.whitelist_tab = QWidget()
        self.create_whitelist_settings()
        self.tab_widget.addTab(self.whitelist_tab, "白名单管理")
        
        # 管理员管理选项卡
        self.admin_tab = QWidget()
        self.create_admin_settings()
        self.tab_widget.addTab(self.admin_tab, "管理员管理")
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("启动程序")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 20px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_button.clicked.connect(self.start_program)
        
        self.save_button = QPushButton("保存配置")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 15px 20px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.save_button.clicked.connect(self.save_config)
        
        self.reset_button = QPushButton("重置为默认")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 15px 20px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.reset_button.clicked.connect(self.reset_to_default)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
    
    def create_basic_settings(self):
        layout = QFormLayout(self.basic_tab)
        # 修复：使用正确的枚举值
        layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        
        # 设置标签和输入框的字体大小
        font = QFont()
        font.setPointSize(14)
        
        # 直播间ID
        self.roomid_input = QLineEdit()
        self.roomid_input.setFont(font)
        self.roomid_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.roomid_input.setText(str(self.config_manager.config.get("env_roomid", "")))
        roomid_label = QLabel("直播间ID:")
        roomid_label.setFont(font)
        layout.addRow(roomid_label, self.roomid_input)
        
        # 轮询间隔
        self.poll_interval_input = QLineEdit()
        self.poll_interval_input.setFont(font)
        self.poll_interval_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.poll_interval_input.setText(str(self.config_manager.config.get("env_poll_interval", "")))
        poll_label = QLabel("轮询间隔(s):")
        poll_label.setFont(font)
        layout.addRow(poll_label, self.poll_interval_input)
        
        # 歌单ID
        self.playlist_input = QLineEdit()
        self.playlist_input.setFont(font)
        self.playlist_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.playlist_input.setText(str(self.config_manager.config.get("env_playlist", "")))
        playlist_label = QLabel("歌单ID:")
        playlist_label.setFont(font)
        layout.addRow(playlist_label, self.playlist_input)
        
        # 队列最大长度
        self.queue_maxsize_input = QLineEdit()
        self.queue_maxsize_input.setFont(font)
        self.queue_maxsize_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.queue_maxsize_input.setText(str(self.config_manager.config.get("env_queue_maxsize", "")))
        qmax_label = QLabel("队列最大长度:")
        qmax_label.setFont(font)
        layout.addRow(qmax_label, self.queue_maxsize_input)
        
        # 视频播放功能开关
        self.video_playback_checkbox = QCheckBox("启用视频播放功能")
        self.video_playback_checkbox.setFont(font)
        self.video_playback_checkbox.setChecked(self.config_manager.config.get("enable_video_playback", True))
        video_label = QLabel("视频播放:")
        video_label.setFont(font)
        layout.addRow(video_label, self.video_playback_checkbox)
        
        # 视频超时容错时间
        self.video_timeout_buffer_input = QLineEdit()
        self.video_timeout_buffer_input.setFont(font)
        self.video_timeout_buffer_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.video_timeout_buffer_input.setText(str(self.config_manager.config.get("env_video_timeout_buffer", 3)))
        timeout_label = QLabel("超时参数(s):")
        timeout_label.setFont(font)
        layout.addRow(timeout_label, self.video_timeout_buffer_input)
        
        # 透明度
        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setMinimum(10)  # 0.1
        self.alpha_slider.setMaximum(100)  # 1.0
        self.alpha_slider.setValue(int(self.config_manager.config.get("env_alpha", 1.0) * 100))
        self.alpha_slider.valueChanged.connect(self.alpha_slider_changed)
        alpha_label = QLabel("GUI透明度:")
        alpha_label.setFont(font)
        self.alpha_value_label = QLabel(f"{self.config_manager.config.get('env_alpha', 1.0):.2f}")
        self.alpha_value_label.setFont(font)
        alpha_layout = QHBoxLayout()
        alpha_layout.addWidget(self.alpha_slider)
        alpha_layout.addWidget(self.alpha_value_label)
        layout.addRow(alpha_label, alpha_layout)
    
    def alpha_slider_changed(self):
        value = self.alpha_slider.value() / 100.0
        self.alpha_value_label.setText(f"{value:.2f}")
    
    def create_advanced_settings(self):
        layout = QFormLayout(self.advanced_tab)
        # 修复：使用正确的枚举值
        layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        
        font = QFont()
        font.setPointSize(14)
        
        # 会话文件
        self.session_file_input = QLineEdit()
        self.session_file_input.setFont(font)
        self.session_file_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.session_file_input.setText(self.config_manager.config.get("env_session_file", "data/session.ncm"))
        session_label = QLabel("会话文件:")
        session_label.setFont(font)
        layout.addRow(session_label, self.session_file_input)
        
        # 白名单文件
        self.whitelist_file_input = QLineEdit()
        self.whitelist_file_input.setFont(font)
        self.whitelist_file_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.whitelist_file_input.setText(self.config_manager.config.get("env_whitelist_file", "config/whitelist.json"))
        whitelist_label = QLabel("白名单文件:")
        whitelist_label.setFont(font)
        layout.addRow(whitelist_label, self.whitelist_file_input)
        
        # MPV路径
        self.mpv_path_input = QLineEdit()
        self.mpv_path_input.setFont(font)
        self.mpv_path_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.mpv_path_input.setText(self.config_manager.config.get("env_mpv_path", ""))
        mpv_label = QLabel("MPV路径:")
        mpv_label.setFont(font)
        layout.addRow(mpv_label, self.mpv_path_input)
        
        # 管理员密码
        self.admin_password_input = QLineEdit()
        self.admin_password_input.setFont(font)
        self.admin_password_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.admin_password_input.setEchoMode(QLineEdit.Password)  # 隐藏密码
        self.admin_password_input.setText(self.config_manager.config.get("env_admin_password", ""))
        password_label = QLabel("管理员密码:")
        password_label.setFont(font)
        layout.addRow(password_label, self.admin_password_input)
    
    def create_whitelist_settings(self):
        layout = QVBoxLayout(self.whitelist_tab)
        
        # 添加用户区域
        add_group = QGroupBox("添加用户")
        add_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        add_layout = QHBoxLayout(add_group)
        
        font = QFont()
        font.setPointSize(14)
        
        self.add_user_input = QLineEdit()
        self.add_user_input.setFont(font)
        self.add_user_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.add_user_button = QPushButton("添加")
        self.add_user_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.add_user_button.clicked.connect(self.add_user)
        
        add_layout.addWidget(QLabel("用户名:"))
        add_layout.addWidget(self.add_user_input)
        add_layout.addWidget(self.add_user_button)
        
        layout.addWidget(add_group)
        
        # 用户列表区域
        list_group = QGroupBox("白名单用户列表")
        list_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        list_layout = QVBoxLayout(list_group)
        
        self.whitelist_list = QListWidget()
        self.whitelist_list.setFont(font)
        self.whitelist_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #C0C0C0;
                background-color: rgba(255, 255, 255, 200);
                font-size: 14px;
                padding: 8px;
            }
        """)
        self.refresh_whitelist()
        list_layout.addWidget(self.whitelist_list)
        
        # 删除按钮
        self.remove_user_button = QPushButton("删除用户")
        self.remove_user_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 12px 20px;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.remove_user_button.clicked.connect(self.remove_selected_user)
        list_layout.addWidget(self.remove_user_button)
        
        layout.addWidget(list_group)
    
    def create_admin_settings(self):
        layout = QVBoxLayout(self.admin_tab)
        
        # 添加管理员区域
        add_group = QGroupBox("添加管理员")
        add_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        add_layout = QHBoxLayout(add_group)
        
        font = QFont()
        font.setPointSize(14)
        
        self.add_admin_input = QLineEdit()
        self.add_admin_input.setFont(font)
        self.add_admin_input.setStyleSheet("padding: 8px; font-size: 14px;")
        self.add_admin_button = QPushButton("添加")
        self.add_admin_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.add_admin_button.clicked.connect(self.add_admin)
        
        add_layout.addWidget(QLabel("用户名:"))
        add_layout.addWidget(self.add_admin_input)
        add_layout.addWidget(self.add_admin_button)
        
        layout.addWidget(add_group)
        
        # 管理员列表区域
        list_group = QGroupBox("管理员列表")
        list_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        list_layout = QVBoxLayout(list_group)
        
        self.admin_list = QListWidget()
        self.admin_list.setFont(font)
        self.admin_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #C0C0C0;
                background-color: rgba(255, 255, 255, 200);
                font-size: 14px;
                padding: 8px;
            }
        """)
        self.refresh_admins()
        list_layout.addWidget(self.admin_list)
        
        # 删除按钮
        self.remove_admin_button = QPushButton("删除管理员")
        self.remove_admin_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 12px 20px;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.remove_admin_button.clicked.connect(self.remove_selected_admin)
        list_layout.addWidget(self.remove_admin_button)
        
        layout.addWidget(list_group)
    
    def add_user(self):
        username = self.add_user_input.text().strip()
        if not username:
            QMessageBox.warning(self, "警告", "请输入用户名！")
            return
        
        if self.whitelist_manager.add_user(username):
            QMessageBox.information(self, "成功", f"用户 '{username}' 已添加到白名单！")
            self.add_user_input.clear()
            self.refresh_whitelist()
        else:
            QMessageBox.warning(self, "警告", f"用户 '{username}' 已存在于白名单中！")
    
    def remove_selected_user(self):
        selected_items = self.whitelist_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选中一个用户！")
            return
        
        username = selected_items[0].text()
        if self.whitelist_manager.remove_user(username):
            QMessageBox.information(self, "成功", f"用户 '{username}' 已从白名单中删除！")
            self.refresh_whitelist()
        else:
            QMessageBox.warning(self, "警告", f"删除用户 '{username}' 失败！")
    
    def add_admin(self):
        username = self.add_admin_input.text().strip()
        if not username:
            QMessageBox.warning(self, "警告", "请输入用户名！")
            return
        
        if self.admin_manager.add_admin(username):
            QMessageBox.information(self, "成功", f"用户 '{username}' 已添加为管理员！")
            self.add_admin_input.clear()
            self.refresh_admins()
        else:
            QMessageBox.warning(self, "警告", f"用户 '{username}' 已是管理员！")
    
    def remove_selected_admin(self):
        selected_items = self.admin_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选中一个管理员！")
            return
        
        username = selected_items[0].text()
        if self.admin_manager.remove_admin(username):
            QMessageBox.information(self, "成功", f"用户 '{username}' 已从管理员列表中删除！")
            self.refresh_admins()
        else:
            QMessageBox.warning(self, "警告", f"删除管理员 '{username}' 失败！")
    
    def refresh_whitelist(self):
        self.whitelist_list.clear()
        users = self.whitelist_manager.get_users()
        for user in users:
            self.whitelist_list.addItem(user)
    
    def refresh_admins(self):
        self.admin_list.clear()
        admins = self.admin_manager.get_admins()
        for admin in admins:
            self.admin_list.addItem(admin)
    
    def save_config(self):
        try:
            # 更新基本配置
            self.config_manager.update_config("env_roomid", int(self.roomid_input.text()))
            self.config_manager.update_config("env_poll_interval", int(self.poll_interval_input.text()))
            self.config_manager.update_config("env_playlist", int(self.playlist_input.text()))
            self.config_manager.update_config("env_mpv_path", self.mpv_path_input.text())
            self.config_manager.update_config("env_session_file", self.session_file_input.text())
            self.config_manager.update_config("env_whitelist_file", self.whitelist_file_input.text())
            self.config_manager.update_config("env_queue_maxsize", int(self.queue_maxsize_input.text()))
            # 更新alpha值
            alpha_value = self.alpha_slider.value() / 100.0
            self.config_manager.update_config("env_alpha", alpha_value)
            # 更新管理员密码
            self.config_manager.update_config("env_admin_password", self.admin_password_input.text())
            # 更新视频播放功能开关
            self.config_manager.update_config("enable_video_playback", self.video_playback_checkbox.isChecked())
            # 更新视频超时容错时间
            self.config_manager.update_config("env_video_timeout_buffer", int(self.video_timeout_buffer_input.text()))
            
            QMessageBox.information(self, "成功", "配置已保存！")
        except ValueError as e:
            QMessageBox.critical(self, "错误", f"输入格式错误: {e}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")
    
    def reset_to_default(self):
        reply = QMessageBox.question(self, "确认", "确定要重置为默认配置吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config_manager.config = self.config_manager.default_config.copy()
            self.config_manager.save_config()
            self.refresh_ui()
            QMessageBox.information(self, "成功", "已重置为默认配置！")
    
    def refresh_ui(self):
        # 刷新基本设置界面
        self.roomid_input.setText(str(self.config_manager.config.get("env_roomid", "")))
        self.poll_interval_input.setText(str(self.config_manager.config.get("env_poll_interval", "")))
        self.playlist_input.setText(str(self.config_manager.config.get("env_playlist", "")))
        self.mpv_path_input.setText(self.config_manager.config.get("env_mpv_path", ""))
        self.queue_maxsize_input.setText(str(self.config_manager.config.get("env_queue_maxsize", "")))
        # 刷新视频播放功能开关
        self.video_playback_checkbox.setChecked(self.config_manager.config.get("enable_video_playback", True))
        # 刷新视频超时容错时间
        self.video_timeout_buffer_input.setText(str(self.config_manager.config.get("env_video_timeout_buffer", 3)))
        # 刷新alpha值
        alpha_value = self.config_manager.config.get("env_alpha", 1.0)
        self.alpha_slider.setValue(int(alpha_value * 100))
        self.alpha_value_label.setText(f"{alpha_value:.2f}")
        
        # 刷新高级设置界面
        self.session_file_input.setText(self.config_manager.config.get("env_session_file", "data/session.ncm"))
        self.whitelist_file_input.setText(self.config_manager.config.get("env_whitelist_file", "config/whitelist.json"))
        self.admin_password_input.setText(self.config_manager.config.get("env_admin_password", ""))
        
        # 刷新白名单
        self.refresh_whitelist()
        
        # 刷新管理员列表
        self.refresh_admins()
    
    def is_main_running(self):
        """精确检查 main.py 是否作为 Python 脚本正在运行"""
        try:
            main_script = os.path.abspath("main.py")
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                    # 检查是否是 Python 进程
                    exe_name = os.path.basename(proc.info['name']).lower()
                    if exe_name not in ('python.exe', 'python', 'python3'):
                        continue
                    # 检查命令行参数中是否有 main.py（标准化路径）
                    for arg in cmdline[1:]:  # 跳过 python 本身
                        if os.path.abspath(arg) == main_script:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"检查进程时出错: {e}")
        return False
    
    def start_program(self):
        try:
            # 击毙残余mpv
            killed_pids = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'mpv.exe':
                        proc.kill()
                        killed_pids.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            if killed_pids:
                print(f"已强制关闭 mpv.exe 进程: PIDs {killed_pids}")
            else:
                print("未检测到运行中的 mpv.exe")
            # 检查main.py是否已经在运行
            if self.is_main_running():
                QMessageBox.warning(self, "警告", "main.py已在运行中！")
                return
            
            # 保存当前配置（自动保存，无需确认）
            # 更新基本配置
            self.config_manager.update_config("env_roomid", int(self.roomid_input.text()))
            self.config_manager.update_config("env_poll_interval", int(self.poll_interval_input.text()))
            self.config_manager.update_config("env_playlist", int(self.playlist_input.text()))
            self.config_manager.update_config("env_mpv_path", self.mpv_path_input.text())
            self.config_manager.update_config("env_session_file", self.session_file_input.text())
            self.config_manager.update_config("env_whitelist_file", self.whitelist_file_input.text())
            self.config_manager.update_config("env_queue_maxsize", int(self.queue_maxsize_input.text()))
            # 更新alpha值
            alpha_value = self.alpha_slider.value() / 100.0
            self.config_manager.update_config("env_alpha", alpha_value)
            # 更新管理员密码
            self.config_manager.update_config("env_admin_password", self.admin_password_input.text())
            # 更新视频播放功能开关
            self.config_manager.update_config("enable_video_playback", self.video_playback_checkbox.isChecked())
            # 更新视频超时容错时间
            self.config_manager.update_config("env_video_timeout_buffer", int(self.video_timeout_buffer_input.text()))

            # 启动 main.py 在新的命令提示符窗口中
            subprocess.Popen([sys.executable, "main.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
            
            # 启动后立即退出 GUI
            QApplication.quit()

        except FileNotFoundError:
            QMessageBox.critical(self, "错误", "未找到 main.py 文件！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动程序失败: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.whitelist_manager = WhitelistManager(self.config_manager.config.get("env_whitelist_file", "config/whitelist.json"))
        self.admin_manager = AdminManager(self.config_manager)
        
        self.setWindowTitle("Kozeki_UserInterface")
        self.setFixedSize(700, 1000)  # 放大窗口
        
        # 设置程序图标
        try:
            # 尝试从文件加载图标
            icon_path = "assets/icon.png"
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                pass
                temp_dir = tempfile.gettempdir()
                temp_icon_path = os.path.join(temp_dir, "temp_icon.png")
        except Exception as e:
            print(f"{e}")
        
        # 设置半透明背景
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(240, 240, 240, 150);
            }
        """)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建半透明背景图片
        try:
            bg_pixmap = QPixmap("assets/bg.png")
            if not bg_pixmap.isNull():
                bg_pixmap = bg_pixmap.scaled(700, 700, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                
                # 创建背景标签
                self.bg_label = QLabel()
                self.bg_label.setPixmap(bg_pixmap)
                self.bg_label.setGeometry(0, 0, 700, 700)
                
                # 设置半透明效果
                self.bg_label.setStyleSheet("background-color: rgba(255, 255, 255, 100);")
                
                # 将背景标签设为底层
                self.bg_label.lower()
                
                # 添加背景标签到主布局
                main_layout.addWidget(self.bg_label)
        except Exception as e:
            print(f"背景图片加载失败: {e}")
            # 如果图片加载失败，使用纯色半透明背景
            pass
        
        # 创建内容部件，传入配置管理器、白名单管理器和管理员管理器
        self.content_widget = SemiTransparentWidget(
            parent=self, 
            config_manager=self.config_manager, 
            whitelist_manager=self.whitelist_manager,
            admin_manager=self.admin_manager
        )
        main_layout.addWidget(self.content_widget)

def main():
    try:
        app = QApplication(sys.argv)
        
        # 设置应用图标
        try:
            icon_path = "assets/icon.png"
            if os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"设置应用图标失败: {e}")
        
        # 设置应用样式
        app.setStyleSheet("""
            QWidget {
                font-size: 14px;
            }
            QTabWidget::pane {
                border: 2px solid #C0C0C0;
                background: rgba(255, 255, 255, 200);
            }
            QTabBar::tab {
                background: rgba(240, 240, 240, 150);
                padding: 12px;
                margin: 3px;
                font-size: 16px;
            }
            QTabBar::tab:selected {
                background: rgba(255, 255, 255, 200);
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid gray;
                border-radius: 8px;
                margin-top: 1.5ex;
                font-size: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                font-size: 16px;
            }
            QLineEdit {
                border: 2px solid #C0C0C0;
                padding: 8px;
                background-color: rgba(255, 255, 255, 200);
                font-size: 14px;
            }
            QListWidget {
                border: 2px solid #C0C0C0;
                background-color: rgba(255, 255, 255, 200);
                font-size: 14px;
            }
            QLabel {
                font-size: 14px;
            }
            QCheckBox {
                font-size: 14px;
            }
        """)
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()  # 打印完整的错误堆栈
        input("按回车键退出...")  # 暂挂终端以便查看错误信息
        sys.exit(1)

if __name__ == "__main__":
    main()