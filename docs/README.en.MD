<div align="center">

# Kozeki_MusicBot

![总得放张图](assets/rm.jpg)

[**English**](./README.en.md) | [**中文简体**](../README.md)

</div>

# Kozeki_MusicBot

Welcome to **Kozeki_MusicBot** — an automated music bot that supports song requests via Bilibili live chat and plays tracks from NetEase Cloud Music.  
*(Windows only)*

---

## Quick Start

1. **Run `start.bat`**  
   On first use, run `start_init.bat` to open a command prompt window displaying the QR code for NetEase Cloud login.  
   After successful login (session saved as `session.ncm`), simply double-click `start.bat` in the project root to launch the graphical configuration interface.

2. **Configure Settings**  
   In the GUI, you can configure the following options:

### Basic Settings
- **Bilibili Live Room ID**: The room ID whose danmaku (live comments) will be monitored.
- **NetEase Cloud Playlist ID** *(Optional)*: Restricts playable songs to those within the specified playlist.
- **Maximum Queue Length**: Controls the maximum number of concurrent song requests allowed in the queue.
- **Danmaku Polling Interval**: Recommended ≥1 second to avoid excessive API requests.
- **GUI Opacity**: Adjustable via slider from 0.1 to 1.0 (where 1.0 = fully opaque).
- **Video Playback Toggle**: Enable or disable video playback functionality.
- **Backup Music Source Toggle**: When enabled, allows non-NetEase sources via `!queue uadd` (may involve copyright infringement).

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

## Hotkey Controls

| Hotkey      | Function                     |
|-------------|------------------------------|
| `Alt+→`     | Skip current track           |
| `Alt+P`     | Play / Pause                 |
| `Alt+↑`     | Increase volume              |
| `Alt+↓`     | Decrease volume              |

---

## Permission Model

The program implements a Unix-like three-tier permission model (`rwx--x---`):

| Role                        | Permission Description                                                                 |
|----------------------------|----------------------------------------------------------------------------------------|
| **[ADM] Admin (Owner)**    | Full read/write access to whitelist; can execute all commands (song requests, playback control, GUI settings, etc.) |
| **[GRP] Whitelisted User (Group)** | Can only execute song-related commands (e.g., request songs, check queue)          |
| **[USR] Guest (Others)**   | No permissions                                                                         |

---

## Command Reference

> **Note**: All commands starting with `!` are **restricted to admins or whitelisted users**.  
> Regular users may send `点歌：song name / id` or `撤销` **only when permission is granted via `!grant`**.

### Music Playback Control
| Command               | Description                                      |
|-----------------------|--------------------------------------------------|
| `!pause`              | Pause current playback                           |
| `!resume`             | Resume playback                                  |
| `!skip`               | Skip current song                                |
| `!vol <0-100>`        | Set volume (e.g., `!vol 75`)                     |
| `!vol`                | Show current volume (range: 0–100)               |
| `!now`                | Display info of currently playing song           |
| `!history {num}`      | Show last `{num}` played songs (default: 5)      |

### Queue Management
| Command               | Description                                      |
|-----------------------|--------------------------------------------------|
| `!queue` or `!queue ls` | List current playback queue                    |
| `!queue add ...`      | Add song to queue (by name or platform ID)       |
| `!queue del N`        | Delete the N-th song in queue (N starts at 1)    |
| `!queue clr`          | Clear entire playback queue                      |

### Whitelist Management
| Command               | Description                                      |
|-----------------------|--------------------------------------------------|
| `!touch user`         | Add user `user` to whitelist                     |
| `!rm user`            | Remove user `user` from whitelist                |
| `!cat`                | View current whitelist                           |
| `!clr`                | Clear whitelist, keeping only default admin      |

### Permission Control
| Command               | Description                                      |
|-----------------------|--------------------------------------------------|
| `!grant`              | Grant open song-request permission to all users (permanent until manually revoked) |
| `!grant -t SEC`       | Temporarily grant permission for `SEC` seconds   |
| `!grant -c NUM`       | Allow non-whitelisted users to request songs `NUM` times |
| `!revoke -c`          | Revoke "count-based" permission                  |
| `!revoke -t`          | Revoke "time-based" permission                   |
| `!revoke`             | Revoke all non-whitelist song-request permissions|

### Time Query
| Command               | Description                                      |
|-----------------------|--------------------------------------------------|
| `!time`               | Show key generation timestamp                    |
| `!time -h`            | Show current system time                         |

### User Data Query
| Command               | Description                                      |
|-----------------------|--------------------------------------------------|
| `!stats user`         | Show `user`'s song request history               |

### Video Playback Control
| Command                     | Description                                      |
|-----------------------------|--------------------------------------------------|
| `!clock`                    | Show current timeout value (in seconds)          |
| `!clock {num}`              | Set timeout to `{num}` seconds                   |
| `!service video start`      | Enable video playback                            |
| `!service video stop`       | Disable video playback                           |

### Window Control
| Command                             | Description                                      |
|-------------------------------------|--------------------------------------------------|
| `!gui info`                         | Display window information                       |
| `!gui hide`                         | Toggle window visibility                         |
| `!gui hide <bool>`                  | Set visibility (`true`/`false`)                  |
| `!gui ignore`                       | Toggle click-through (穿透) state                |
| `!gui ignore <bool>`                | Set click-through state                          |
| `!gui direct`                       | Toggle borderless mode                           |
| `!gui direct <bool>`                | Set borderless state                             |
| `!gui resize <w>, <h>`              | Resize window to width `w` and height `h`        |
| `!gui origin <x>, <y>`              | Move window to coordinates (`x`, `y`)            |
| `!gui origin`                       | Query current window position                    |
| `!gui alpha <float>`                | Set window opacity (0.1–1.0)                     |
| `!gui set <int>`                    | Apply preset window style                        |
| `!gui sign "<w>, <h>, <x>, <y>, <alpha>, <ignore>"` | Register a new preset |

### Other Commands
| Command               | Description                                      |
|-----------------------|--------------------------------------------------|
| `!service`            | Check status of all services                     |
| `!env`                | List all environment variables                   |
| `!env {name}`         | Get value of environment variable `{name}`       |
| `!env {name} {value}` | Set environment variable `{name}` to `{value}`   |
| `!reload`             | Reload configuration from `config.json`          |
| `!help`               | Display this help message                        |

### Regular User Requests
| Input Format                     | Action                                           |
|----------------------------------|--------------------------------------------------|
| `点歌：song name / id`           | Request a song by name or platform ID (requires active permission) |
| `撤销`                           | Cancel all pending requests from the sender      |

---

## Dependencies

Ensure the following Python packages are installed:

```text
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

Install via:

```bash
pip install -r requirements.txt
```

---

## Becoming an Admin

You may either modify `main.py` directly or use a secret key in danmaku.

**Key Generation Rule**:  
Use the string `YYMMDDHH+ADMIN_KEYS` as seed, compute its SHA256 hash, and take the **first 10 characters** as the valid admin key.

---

## Project Structure

```text
Kozeki_MusicBot/
├── assets/
│   ├── bg.png          # UI background image
│   ├── icon.png        # Application icon
│   └── image.jpg       # Reference image
├── config/
│   ├── config.json     # Main configuration file
│   ├── dict.json       # Mapping dictionary
│   ├── hotkeys.json    # Hotkey configuration
│   └── whitelist.json  # Whitelist user list
├── data/
│   ├── fused_keys.json # Records fused/burned keys
│   ├── session.ncm     # NetEase login session
│   └── requests.log    # Request logs
├── docs/
│   ├── assets/
│   │   ├── image.jpg   # Reference image
│   │   └── rm.jpg      # Reference image
│   └── README.en.md    # This English README
├── modules/
│   ├── __init__.py
│   ├── command_handler.py
│   ├── config_loader.py
│   ├── gui.py
│   ├── hotkeys.py
│   ├── listener.py
│   ├── logger.py
│   ├── music_bot.py
│   ├── permission.py
│   ├── player.py
│   ├── queue_manager.py
│   ├── unorthodox.py   # Backup music source service
│   └── utils.py
├── mpv.exe             # Bundled MPV player (Windows)
├── requirements.txt    # Python dependencies
├── main.py             # Core program logic
├── ui.py               # GUI implementation
├── README.md           # Chinese README
├── start_init.bat      # Initial launch script (for first-time login)
└── start.bat           # Standard launcher script (Windows)
```

> **Tip**: On first use, have the **NetEase Cloud Music app** ready for QR code scanning.

![全体欣赏音乐！](assets/image.jpg)

**`全体欣赏音乐！`**