<div align="center">

#  Kozeki_MusicBot

![总得放张图](docs/assets/rm.jpg)

[**English**](./docs/README.en.md) | [**中文简体**](./README.md)

</div>

# Kozeki_MusicBot

欢迎使用 **Kozeki_MusicBot** —— 一款基于 Bilibili 弹幕点歌、网易云音乐播放的自动化音乐机器人。（仅兼容Windows系统）

---

##  快速开始

1. **运行 `start.bat`**  
   初次使用时请运行`start_init.bat`，这将提供命令提示符窗口用于输出登录的二维码。保留登陆状态后双击运行项目根目录下的 `start.bat` 文件，将启动图形化交互配置界面。

2. **配置参数**  
   在交互界面中，您可以设置以下内容：

   ### 基础设置
   - **B站直播间号码**：监听弹幕的直播间 ID。
   - **网易云歌单 ID**：用于限制可点歌曲范围（可选）。
   - **播放队列最大长度**：控制同时排队的最大请求数。
   - **轮询弹幕间隔时间**：建议 ≥1 秒，避免请求过于频繁。
   - **GUI界面透明度**：滑块调节0.1 ~ 1，alpha值为1时代表完全不透明。
   - **点播视频功能开关**：rt。
   - **备线音乐源开关**：启用后，支持以!queue uadd的方式爬取第三方资源（可能构成侵权）

   ### 高级设置
   - **网易云会话文件路径**（默认为 `session.ncm`）
   - **MPV 播放器路径**（Windows 下默认包含 `mpv.exe`）
   - **白名单文件路径**（默认为 `whitelist.json`）
   - **管理员密码**（用于生成 `SHA256` 密钥）
   - **超时参数**：终止进程的计时器，超过视频时长后多少秒kill

   > 所有配置将自动保存至 `config.json`。

3. **启动主程序**  
   点击“启动程序”按钮后，程序将：
   - 若为首次运行，弹出二维码供扫码登录网易云音乐；
   - 登录成功后，会话信息将保存为 `session.ncm`，后续无需重复登录；
   - 实时监听指定 Bilibili 直播间弹幕，处理点歌指令。

4. **日志与白名单**
   - 成功的点歌请求将记录在 `requests.log`；
   - 白名单用户列表保存于 `whitelist.json`。

5. **快捷键控制**

   | 快捷键 | 功能 |
   |--------|------|
   | `Alt+→` | 跳过当前曲目 |
   | `Alt+P` | 播放/暂停 |
   | `Alt+↑` | 音量增大 |
   | `Alt+↓` | 音量减小 |

---

##  权限管理

本程序采用三级权限模型（类 Unix 权限 `rwx--x---`）：

| 角色 | 权限说明 |
|------|--------|
| **[ADM] 管理员（文件所有者）** | 可读写白名单、执行所有点歌及控制命令 |
| **[GRP] 白名单用户（组用户）** | 仅可执行点歌命令（如点歌、查队列等） |
| **[USR] 游客（其他用户）** | 无任何权限 |

---


## 命令集说明

注意：所有以 `!` 开头的命令仅限管理员或白名单用户使用。  
普通用户仅在通过 `!grant` 授予权限时，可发送 `点歌：歌曲名 / id` 或 `撤销`。

### 音乐播放控制

| 命令 | 说明 |
|------|------|
| `!pause` | 暂停当前播放 |
| `!resume` | 恢复播放 |
| `!skip` | 跳过当前歌曲 |
| `!vol <0-100>` | 设置音量（例如：`!vol 75`） |
| `!vol` | 显示当前音量（范围 0–100） |
| `!now` | 显示当前播放歌曲信息 |
| `!history {num}` | 查看最近播放的 `{num}` 首歌曲（默认为 5） |

### 播放队列管理

| 命令 | 说明 |
|------|------|
| `!queue` 或 `!queue ls` | 列出当前播放队列 |
| `!queue add ...` | 向队列添加歌曲（支持名称或平台 ID） |
| `!queue del N` | 删除队列中第 N 首歌曲（N 从 1 开始计数） |
| `!queue clr` | 清空整个播放队列 |

### 白名单管理

| 命令 | 说明 |
|------|------|
| `!touch user` | 将用户 `user` 加入白名单 |
| `!rm user` | 将用户 `user` 移出白名单 |
| `!cat` | 查看当前白名单 |
| `!clr` | 清空白名单（保留默认管理员） |

### 权限控制

| 命令 | 说明 |
|------|------|
| `!grant` | 向所有用户开放点歌权限（永久有效，直到手动撤销） |
| `!grant -t SEC` | 临时开放权限，持续 `SEC` 秒 |
| `!grant -c NUM` | 允许非白名单用户点歌 `NUM` 次 |
| `!revoke -c` | 撤销“次数型”权限 |
| `!revoke -t` | 撤销“时间型”权限 |
| `!revoke` | 撤销所有非白名单用户的点歌权限 |

### 时间查询

| 命令 | 说明 |
|------|------|
| `!time` | 显示密钥生成时间戳 |
| `!time -h` | 显示当前系统时间 |

### 用户数据查询

| 命令 | 说明 |
|------|------|
| `!stats user` | 显示用户 `user` 的点歌历史记录 |

### 视频播放控制

| 命令 | 说明 |
|------|------|
| `!clock` | 显示当前超时值（单位：秒） |
| `!clock {num}` | 设置超时为 `{num}` 秒 |
| `!service video start` | 启用视频播放功能 |
| `!service video stop` | 禁用视频播放功能 |

### 窗口控制

| 命令 | 说明 |
|------|------|
| `!gui info` | 显示窗口信息 |
| `!gui hide` | 切换窗口可见性 |
| `!gui hide <bool>` | 设置窗口可见性（`true` / `false`） |
| `!gui ignore` | 切换窗口穿透状态 |
| `!gui ignore <bool>` | 设置窗口穿透状态 |
| `!gui direct` | 切换无边框模式 |
| `!gui direct <bool>` | 设置无边框状态 |
| `!gui resize <w>, <h>` | 调整窗口大小为宽 `w`、高 `h` |
| `!gui origin <x>, <y>` | 将窗口移动到坐标 (`x`, `y`) |
| `!gui origin` | 查询当前窗口位置 |
| `!gui alpha <float>` | 设置窗口透明度（0.1–1.0） |
| `!gui set <int>` | 应用预设窗口样式 |
| `!gui sign "<w>, <h>, <x>, <y>, <alpha>, <ignore>"` | 注册新的窗口预设 |

### 其他命令

| 命令 | 说明 |
|------|------|
| `!service` | 查看所有服务状态 |
| `!env` | 列出所有环境变量 |
| `!env {name}` | 获取环境变量 `{name}` 的值 |
| `!env {name} {value}` | 设置环境变量 `{name}` 为 `{value}` |
| `!reload` | 重新加载 `config.json` 配置文件 |
| `!help` | 显示本帮助信息 |

### 普通用户请求

| 输入格式 | 动作 |
|----------|------|
| `点歌：歌曲名 / id` | 请求歌曲（需拥有有效权限） |
| `撤销` | 撤销自己所有待处理的请求 |




> **权限说明**：
> - 所有以 `!` 开头的命令**仅限管理员或白名单用户使用**。
> - 普通用户点歌需在点歌权限开放时（通过 `!grant`）方可生效。

---

##  环境依赖

请确保已安装以下 Python 依赖：

```
aiohttp
pyncm
qrcode
pillow
tk
watchdog
pywin32
PyQt5
psutil
yt-dlp
playwright
keyboard
pynput
```

安装命令：
```bash
pip install -r requirements.txt
```
---
##  成为管理员

直接修改main.py或在弹幕中使用密钥。

密钥规则：`YYMMDDHH+ADMIN_KEYS` 作为种子生成哈希值，取前十位。

---

##  项目文件结构

```
Kozeki_MusicBot/
├── assets/
│   ├── bg.png                # UI 背景图
│   ├── icon.png              # 程序图标
│   └── image.jpg             # 引用图片
├── config/
│   ├── config.json           # 主配置文件
│   ├── dict.json             # 映射词典
│   ├── hotkeys.json          # 快捷键配置
│   └── whitelist.json        # 白名单用户列表
├── data/
│   ├── fused_keys.json       # 记录熔断密钥
│   ├── session.ncm           # 网易云登录会话
│   └── requests.log          # 请求日志
├── docs/
│   ├── assets/
│   │   ├── image.jpg         # 引用图片
│   │   └── rm.jpg            # 引用图片
│   └── README.en.MD          # 洋文自述文件
├── modules/
│   ├──  init.py              # 模块包初始化
│   ├──  command_handler.py   # 命令解析、路由与执行
│   ├──  config_loader.py     # 配置加载、热重载与环境变量管理
│   ├──  gui.py               # GUI 控制逻辑
│   ├──  hotkeys.py           # 提供快捷键支持
│   ├──  listener.py          # 消息监听器
│   ├──  logger.py            # 日志系统
│   ├──  music_bot.py         # 机器人主逻辑
│   ├──  permission.py        # 权限系统
│   ├──  player.py            # MPV 播放器控制
│   ├──  queue_manager.py     # 播放队列管理
│   ├──  unorthodox.py        # 备用音乐源服务
│   └──  utils.py             # 工具函数
├── mpv.exe                   # 内置 MPV 播放器（Windows）
├── requirements.txt          # 依赖列表
├── main.py                   # 程序主入口
├── ui.py                     # 图形界面逻辑
├── README.MD                 # 此自述文件
├── start_init.bat            # 首次运行的启动脚本（Windows）
└── start.bat                 # 启动脚本（Windows）
```

---

>  提示：首次使用请准备好网易云音乐 App 用于扫码登录。

![全体欣赏音乐！](assets/image.jpg)

**`全体欣赏音乐！`**