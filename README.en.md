# RealTimeMix

A real-time pixel block permutation scrambler for images and videos. The standout feature is a **transparent screen decrypt lens**: a draggable, always-on-top floating window that captures the screen beneath it and descrambles the content in real time.

<p align="center">
  <img src="demos/crypt_demo.gif" width="80%" alt="Encrypt Demo">
</p>

## Features

- **Block Permutation Scrambling**: Shuffle image/video blocks (8/16/32/64 px) using a deterministic pseudo-random seed.
- **Seed-Driven Encryption**: Each scramble produces a Base64-encoded seed containing aspect ratio, block size, and random seed — the only key needed for perfect reconstruction.
- **Real-Time Decrypt Lens**: Pure Win32 layered window with physical-pixel precision. Drag it over any screen region (browser, player, other apps) to descramble in real time.
- **Chrome Extension Auto-Align**: Browser extension locates image/video elements and automatically positions the lens over them — no manual dragging needed.
- **DPI-Aware & Multi-Monitor**: Works correctly on high-DPI displays and across monitors.
- **Self-Capture Exclusion**: The lens window is invisible to screen capture APIs (Win10 2004+) to avoid mirror-in-mirror effects.

<p align="center">
  <img src="demos/decrypt_demo.gif" width="80%" alt="Decrypt Lens Demo">
</p>

## Quick Start

### Requirements

- Windows 10/11
- Python 3.10+ (for source) or just unzip the release (for standalone)

### Install from Source

```bash
pip install -r requirements.txt
python main.py
```

### Standalone Executable

Download the latest release, unzip, and run `RealTimeMix.exe`.

## Usage

### Encrypt
1. Switch to the **Encrypt** tab.
2. Select an image or video.
3. Adjust block size.
4. Click **Scramble & Save**. The generated seed appears below.

### Decrypt Lens
1. Switch to the **Decrypt Lens** tab.
2. Paste the seed.
3. Click **Start Lens**. The lens window appears.
4. Drag it over the scrambled content.

**Lens Controls:**
- **Left-drag**: Move window
- **Edge/corner drag**: Resize (maintains aspect ratio)
- **Right-click**: Preset sizes (100%/150%/200%/Fit/Custom) or close
- **Double-click**: Close lens
- **Ctrl+Shift+Arrows**: Nudge 1 physical pixel
- **Ctrl+Shift++/-**: Zoom ±0.1%

<p align="center">
  <img src="demos/auto_align_demo.gif" width="80%" alt="Auto Align Demo">
</p>

## Chrome Extension

The extension lets you click any image or video element on a webpage to automatically align the decrypt lens over it.

### Installation

1. Open Chrome/Edge and go to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** and select the `browser_extension/` folder
4. Copy the extension ID (32 lowercase letters)
5. In PowerShell, run:
   ```powershell
   cd native_host
   .\install_host.ps1 -ExtensionId <your-extension-id>
   ```
6. Restart Chrome/Edge

### Usage

1. Start RealTimeMix (`python main.py` or `RealTimeMix.exe`)
2. Paste the seed in the Decrypt Lens tab
3. Enable **Auto Align**
4. On any webpage, press **Ctrl+Shift** and left-click an image/video element
5. The lens automatically snaps to the element

## How It Works

### Architecture

```
Browser Page
  └─ content.js (injected script)
       │  chrome.runtime.sendMessage
       ▼
  background.js (Service Worker)
       │  chrome.runtime.connectNative
       ▼
  realtime_mix_host.py (Native Messaging Host)
       │  TCP JSON (localhost:35421)
       ▼
  main_window.py (RealTimeMix Main App)
       │
       ▼
  lens_window.py (Pure Win32 Lens)
```

### Algorithm: Block Permutation

The image is divided into `block_size × block_size` squares. A Fisher-Yates shuffle seeded by a 64-bit integer generates a global block permutation table. Only complete blocks are shuffled; edge strips (right/bottom) remain untouched.

```python
perm = list(range(n))
rng = random.Random(seed_val)
rng.shuffle(perm)
```

The operation is perfectly reversible: the same seed produces the same permutation table, allowing `descramble(scramble(img)) == img`.

> ⚠️ **Not cryptographically secure.** This is obfuscation, not encryption. Color histograms and local statistics are preserved. Suitable for content hiding and preview protection, not high-security applications.

### Seed Format

20-byte binary structure (little-endian), URL-safe Base64 encoded:

| Field | Offset | Size | Type | Description |
|-------|--------|------|------|-------------|
| version | 0 | 1B | uint8 | Protocol version (1) |
| aspect_w | 1 | 2B | uint16 | Original media width |
| aspect_h | 3 | 2B | uint16 | Original media height |
| block_size | 5 | 2B | uint16 | Block size in pixels |
| algorithm | 7 | 1B | uint8 | Algorithm ID (0 = block perm) |
| seed | 8 | 8B | uint64 | 64-bit random seed |
| crc32 | 16 | 4B | uint32 | CRC32 of first 16 bytes |

### Why Pure Win32 for the Lens?

Qt's `QWidget` uses **logical coordinates** (device-independent pixels). At 175% DPI, `resize(730)` maps to ~1278 physical pixels — no integer logical size maps exactly to a target physical size (e.g., 1280). This causes 1-2px stretching misalignment after `cv2.resize`.

`LensWindow` uses `SetWindowPos` directly in **physical pixels**, and `GetWindowRect` reads physical pixels. Screen capture via `mss` yields the exact original resolution, so descrambled block boundaries align perfectly.

### Performance

| Stage | Implementation | Latency |
|-------|---------------|---------|
| Screen capture | `mss` (Windows DXGI) | ~5-10 ms @ 1080p |
| Resize | OpenCV `cv2.resize` | ~2-5 ms |
| Scramble/Descramble | Python loops + numpy | ~5-10 ms @ 1280×720, bs=32 |
| Display | `UpdateLayeredWindow` | ~1-2 ms |
| **Total frame delay** | — | **~20-30 ms (30-50 fps)** |

The lens runs on a 50ms (20fps) timer by default — smooth enough and low CPU usage.

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RTM_LOG_FILE` | `rtm_debug.log` | Log file path |
| `RTM_LOG_LEVEL` | `DEBUG` | Log level |
| `RTM_PORT` | `35421` | Browser extension TCP port |
| `RTM_PRESETS_FILE` | `presets.json` | Preset save path |
| `RTM_EXCLUDE_CAPTURE` | `1` | Set to `0` to allow screen recorders to capture the lens |

## File Structure

```
RealTimeMix/
├── main.py                    # Entry point
├── main_window.py             # Qt main window
├── lens_window.py             # Pure Win32 lens
├── scrambler.py               # Core scramble/descramble algorithm
├── seed.py                    # Seed codec
├── browser_extension/         # Chrome extension
├── native_host/               # Native Messaging Host
├── demos/                     # Demo GIFs
├── tests/                     # pytest suite
├── pyproject.toml
├── requirements.txt
└── README.md
```

## License

MIT License — see [LICENSE](LICENSE) file.
