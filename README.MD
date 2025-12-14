#  自述文件 | README

- [中文](#chinese)
- [English](#english)

---
# Kozeki_MusicBot <a id="chinese"></a>

欢迎使用 **Kozeki_MusicBot** —— 一款基于 Bilibili 弹幕点歌、网易云音乐播放的自动化音乐机器人。

---

##  快速开始

1. **运行 `start.bat`**  
   双击运行项目根目录下的 `start.bat` 文件，将启动图形化交互配置界面。

2. **配置参数**  
   在交互界面中，您可以设置以下内容：

   ### 基础设置
   - **B站直播间号码**：监听弹幕的直播间 ID。
   - **网易云歌单 ID**：用于限制可点歌曲范围（可选）。
   - **播放队列最大长度**：控制同时排队的最大请求数。
   - **轮询弹幕间隔时间**：建议 ≥1 秒，避免请求过于频繁。
   - **GUI界面透明度**：滑块调节0.1 ~ 1，alpha值为1时代表完全不透明。
   - **点播视频功能开关**：rt。

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

---

##  权限管理

本程序采用三级权限模型（类 Unix 权限 `rwx--x---`）：

| 角色 | 权限说明 |
|------|--------|
| **[ADM] 管理员（文件所有者）** | 可读写白名单、执行所有点歌及控制命令 |
| **[GRP] 白名单用户（组用户）** | 仅可执行点歌命令（如点歌、查队列等） |
| **[USR] 游客（其他用户）** | 无任何权限 |

---

##  命令集说明



| 分类             | 命令                          | 功能说明                                                                 |
|------------------|-------------------------------|--------------------------------------------------------------------------|
| **音乐播放控制** | `!pause`                      | 暂停当前播放                                                             |
|                  | `!resume`                     | 恢复播放                                                                 |
|                  | `!skip`                       | 跳过当前歌曲                                                             |
|                  | `!vol <0-100>`                | 设置音量（例如：`!vol 75`）                                              |
|                  | `!vol`                        | 查询当前音量（范围 0–100）                                               |
|                  | `!now`                        | 显示当前正在播放的歌曲信息                                               |
|                  | `!history {num}`              | 显示最近播放的 `{num}` 首歌曲（默认为 5）                                |
| **播放队列管理** | `!queue` 或 `!queue ls`       | 显示当前播放队列                                                         |
|                  | `!queue add ...`              | 添加歌曲至队列（支持歌名或平台 ID）                                      |
|                  | `!queue del N`                | 删除队列中第 `N` 首歌曲（`N` 从 1 开始）                                 |
|                  | `!queue clr`                  | 清空整个播放队列                                                         |
| **白名单管理**   | `!touch user`                 | 将用户 `user` 添加至白名单                                               |
|                  | `!rm user`                    | 从白名单中移除用户 `user`                                                |
|                  | `!cat`                        | 查看当前白名单用户列表                                                   |
|                  | `!clr`                        | 清空白名单，仅保留默认管理员                                             |
| **点歌权限控制** | `!grant`                      | 开放所有人点歌权限（永久有效，直到手动收回）                             |
|                  | `!grant -t SEC`               | 临时开放点歌权限，持续 `SEC` 秒                                          |
|                  | `!grant -c NUM`               | 开放点歌权限，允许非白名单用户点歌 `NUM` 次                              |
|                  | `!revoke -c`                  | 收回“次数型”点歌权限                                                     |
|                  | `!revoke -t`                  | 收回“时间型”点歌权限                                                     |
|                  | `!revoke`                     | 收回所有非白名单用户的点歌权限                                           |
| **时间查询**     | `!time`                       | 查询密钥生成时间                                                         |
|                  | `!time -h`                    | 获取当前系统时间                                                         |
| **用户数据查询** | `!stats user`                 | 查询用户 `user` 的点歌记录                                               |
| **视频播放控制** | `!clock`                      | 查询计时器超时参数（单位：秒）                                           |
|                  | `!clock {num}`                | 设置计时器超时参数为 `{num}` 秒                                          |
|                  | `!service video start`        | 启用视频播放功能                                                         |
|                  | `!service video stop`         | 禁用视频播放功能                                                         |
| **其他**         | `!service`                    | 检查各项功能服务状态                                                     |
|                  | `!env`                        | 查看所有环境变量                                                         |
|                  | `!env {name}`                 | 查询名为 `{name}` 的环境变量值                                           |
|                  | `!env {name} {value}`         | 设置环境变量 `{name}` 的值为 `{value}`                                   |
|                  | `!help`                       | 显示本帮助信息                                                           |
| **普通用户点歌** | `song name / id`              | 直接发送歌曲名称或平台 ID 进行点播（需具备点歌权限）                     |

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
│   └── whitelist.json        # 白名单用户列表
├── data/
│   ├── fused_keys.json       # 记录熔断密钥
│   ├── session.ncm           # 网易云登录会话
│   └── requests.log          # 请求日志
├── mpv.exe                   # 内置 MPV 播放器（Windows）
├── requirements.txt          # 依赖列表
├── main.py                   # 主程序逻辑
├── ui.py                     # 图形界面逻辑
├── README.MD                 # 此自述文件
└── start.bat                 # 启动脚本（Windows）
```

---

>  提示：首次使用请准备好网易云音乐 App 用于扫码登录。

![全体欣赏音乐！](assets/image.jpg)

**`全体欣赏音乐！`**

---
---

# Kozeki_MusicBot <a id="english"></a>

Welcome to **Kozeki_MusicBot** — an automated music bot that supports song requests via Bilibili live chat and plays tracks from NetEase Cloud Music.

---

## Quick Start

1. **Run `start.bat`**  
   Double-click the `start.bat` file in the project root directory to launch the graphical configuration interface.

2. **Configure Settings**  
   In the GUI, you can configure the following options:

   ### Basic Settings
   - **Bilibili Live Room ID**: The room ID whose danmaku (live comments) will be monitored.
   - **NetEase Cloud Playlist ID** (Optional): Restricts playable songs to those within the specified playlist.
   - **Maximum Queue Length**: Controls the maximum number of concurrent song requests allowed in the queue.
   - **Danmaku Polling Interval**: Recommended ≥1 second to avoid excessive API requests.
   - **GUI Opacity**: Adjustable via slider from 0.1 to 1.0 (where 1.0 = fully opaque).
   - **Video Playback Toggle**: Enable or disable video playback functionality.

   ### Advanced Settings
   - **NetEase Session File Path** (Default: `session.ncm`)
   - **MPV Player Executable Path** (Windows default includes `mpv.exe`)
   - **Whitelist File Path** (Default: `whitelist.json`)
   - **Admin Password** (Used to generate a `SHA256` key)
   - **Timeout Parameter**: Number of seconds after a video ends before forcibly terminating the playback process.

   > All settings are automatically saved to `config.json`.

3. **Launch the Main Program**  
   After clicking **"Launch Program"**, the application will:
   - On first run, display a QR code for scanning to log in to NetEase Cloud Music;
   - Upon successful login, save session data as `session.ncm` (no re-login needed subsequently);
   - Begin listening in real time to danmaku in the specified Bilibili live room and process song request commands.

4. **Logging & Whitelist**
   - Successful song requests are logged in `requests.log`;
   - Whitelisted users are stored in `whitelist.json`.

---

## Permission Model

The program implements a Unix-like three-tier permission model (`rwx--x---`):

| Role | Permission Description |
|------|------------------------|
| **[ADM] Admin (Owner)** | Full read/write access to whitelist; can execute all commands (song requests, playback control, etc.) |
| **[GRP] Whitelisted User (Group)** | Can only execute song-related commands (e.g., request songs, check queue) |
| **[USR] Guest (Others)** | No permissions |

---

## Command Reference

| Category | Command | Description |
|----------|--------|-------------|
| **Playback Control** | `!pause` | Pause current playback |
| | `!resume` | Resume playback |
| | `!skip` | Skip current song |
| | `!vol <0-100>` | Set volume (e.g., `!vol 75`) |
| | `!vol` | Show current volume (0–100) |
| | `!now` | Display info of currently playing song |
| | `!history {num}` | Show last `{num}` played songs (default: 5) |
| **Queue Management** | `!queue` or `!queue ls` | List current playback queue |
| | `!queue add ...` | Add song to queue (by name or platform ID) |
| | `!queue del N` | Delete the N-th song in queue (N starts at 1) |
| | `!queue clr` | Clear entire playback queue |
| **Whitelist Management** | `!touch user` | Add user `user` to whitelist |
| | `!rm user` | Remove user `user` from whitelist |
| | `!cat` | View current whitelist |
| | `!clr` | Clear whitelist, keeping only default admin |
| **Permission Control** | `!grant` | Grant open song-request permission to all users (permanent until manually revoked) |
| | `!grant -t SEC` | Temporarily grant permission for `SEC` seconds |
| | `!grant -c NUM` | Allow non-whitelisted users to request songs `NUM` times |
| | `!revoke -c` | Revoke "count-based" permission |
| | `!revoke -t` | Revoke "time-based" permission |
| | `!revoke` | Revoke all non-whitelist song-request permissions |
| **Time Query** | `!time` | Show key generation timestamp |
| | `!time -h` | Show current system time |
| **User Data Query** | `!stats user` | Show `user`'s song request history |
| **Video Playback Control** | `!clock` | Show current timeout value (in seconds) |
| | `!clock {num}` | Set timeout to `{num}` seconds |
| | `!service video start` | Enable video playback |
| | `!service video stop` | Disable video playback |
| **Other** | `!service` | Check status of all services |
| | `!env` | List all environment variables |
| | `!env {name}` | Get value of environment variable `{name}` |
| | `!env {name} {value}` | Set environment variable `{name}` to `{value}` |
| | `!help` | Display this help message |
| **Regular User Request** | `song name / id` | Send song name or platform ID directly to request (requires active permission) |

> **Permission Notes**:
> - All commands starting with `!` are **restricted to admins or whitelisted users**.
> - Regular users can only request songs when permission is explicitly granted via `!grant`.

---

## Dependencies

Ensure the following Python packages are installed:

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
```

Install via:
```bash
pip install -r requirements.txt
```

---

## Becoming an Admin

You may either modify `main.py` directly or use a secret key in danmaku.

**Key Generation Rule**:  
Take the string `YYMMDDHH+ADMIN_KEYS` as seed, compute its SHA256 hash, and use the first 10 characters.

---

## Project Structure

```
Kozeki_MusicBot/
├── assets/
│   ├── bg.png                # UI background image
│   ├── icon.png              # Application icon
│   └── image.jpg             # Reference image
├── config/
│   ├── config.json           # Main configuration file
│   └── whitelist.json        # Whitelist user list
├── data/
│   ├── fused_keys.json       # Records fused/burned keys
│   ├── session.ncm           # NetEase login session
│   └── requests.log          # Request logs
├── mpv.exe                   # Bundled MPV player (Windows)
├── requirements.txt          # Python dependencies
├── main.py                   # Core program logic
├── ui.py                     # GUI implementation
├── README.MD                 # This file
└── start.bat                 # Launcher script (Windows)
```

> **Tip**: On first use, have the NetEase Cloud Music app ready for QR code scanning.

![全体欣赏音乐！](assets/image.jpg)

**`全体欣赏音乐！`**