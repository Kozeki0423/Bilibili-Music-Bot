<div align="center">

# Kozeki_MusicBot

![总得放张图](assets/rm.jpg)

[**English**](./README.en.md) | [**中文简体**](../../README.md)

</div>

# Kozeki_MusicBot

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
| **Regular User Request** | `点歌：song name / id` | Send song name or platform ID directly to request (requires active permission) |
| |`撤销`| 删除发出者所有点歌请求

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
|   ├── dict.json             # Dictionary
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