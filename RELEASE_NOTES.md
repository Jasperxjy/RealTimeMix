# RealTimeMix v1.0.0 Release Notes

## 下载

| 文件 | 说明 | 大小 |
|------|------|------|
| `RealTimeMix-v1.0.0-win64.zip` | Windows 64位可执行程序（解压即用） | ~270 MB |
| `Source code (zip)` | 源代码压缩包 | — |
| `Source code (tar.gz)` | 源代码压缩包 | — |

## 系统要求

- **操作系统**：Windows 10 / Windows 11
- **运行方式**：解压 `RealTimeMix-v1.0.0-win64.zip`，双击 `RealTimeMix.exe`
- **浏览器扩展**（可选）：需要安装 Python 以运行 Native Messaging Host（见下方说明）

## 功能特性

- 🔐 **图片/视频加密**：将图片或视频按指定块大小进行伪随机块置换混淆
- 🔍 **实时解密透镜**：纯 Win32 实现的透明置顶窗口，精确对齐物理像素，实时解混淆显示
- 🎯 **浏览器插件自动对齐**：Chrome/Edge 扩展支持 Ctrl+Shift+点击自动定位透镜到页面元素
- 🖥️ **多显示器支持**：透镜可拖动到任意显示器
- ⌨️ **快捷键操作**：Ctrl+Shift+方向键精确移动 1px，Ctrl+Shift++/- 微调缩放
- 🎞️ **视频处理**：支持 H.264 编码输出（需安装 ffmpeg 以获得完整音频支持）

## 安装说明

### 方式一：使用打包版（推荐）

1. 下载 `RealTimeMix-v1.0.0-win64.zip`
2. 解压到任意目录（如 `D:\RealTimeMix\`）
3. 双击 `RealTimeMix.exe` 运行主程序

### 方式二：从源码运行

```bash
git clone https://github.com/yourusername/RealTimeMix.git
cd RealTimeMix
pip install -r requirements.txt
python main.py
```

### 浏览器扩展（可选）

1. 打开 Chrome/Edge，进入 `chrome://extensions/`
2. 开启**开发者模式**
3. 点击**加载已解压的扩展程序**，选择程序目录下的 `browser_extension/` 文件夹
4. 复制扩展 ID（32位字母）
5. 进入 `native_host/` 目录，运行 PowerShell：
   ```powershell
   .\install_host.ps1 -ExtensionId <你的扩展ID>
   ```
6. 重启浏览器

> **注意**：浏览器扩展的 Native Messaging Host 依赖 Python。使用打包版时，请确保系统已安装 Python 且 `python` 命令可用。

## 配置文件

程序支持以下环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RTM_LOG_FILE` | `rtm_debug.log` | 日志文件路径 |
| `RTM_LOG_LEVEL` | `DEBUG` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `RTM_PORT` | `35421` | 浏览器插件通信端口 |
| `RTM_PRESETS_FILE` | `presets.json` | 预设保存路径 |
| `RTM_EXCLUDE_CAPTURE` | `1` | 设为 `0` 可让录屏软件捕获透镜窗口 |

## 已知限制

- ⚠️ 这不是密码学安全的加密算法，仅用于内容混淆和预览保护
- 视频处理在无 ffmpeg 时回退到 OpenCV `mp4v` 编码（不含音频）
- 透镜窗口使用纯 Win32 API，仅支持 Windows 平台

## 技术栈

- Python 3.10+ / PyQt6 / OpenCV / NumPy / MSS
- 纯 Win32 API（透镜窗口）
- Chrome Native Messaging（浏览器扩展）

---

**完整文档**：见仓库 [README.md](https://github.com/yourusername/RealTimeMix#readme)

**反馈问题**：请提交 [Issue](https://github.com/yourusername/RealTimeMix/issues)
