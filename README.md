# RealTimeMix - 实时像素混淆加密工具

一款用于图片和视频的像素块级混淆加密程序，核心特色是**透明屏幕解密透镜**：一个可拖动、置顶的浮窗，自动捕获框下方的屏幕区域并实时解混淆显示。

## 特性

- **混淆加密**：将图片/视频按指定块大小（如 8/16/32/64）进行伪随机块置换打乱。
- **种子驱动**：加密时生成包含长宽比、块大小、随机种子的密钥（Base64），可用于精确还原。
- **解密透镜（实时）**：透明置顶浮窗，拖动到任意屏幕区域（浏览器、播放器、其他软件上方），实时捕获并解混淆显示框内内容。
- **双版本交付**：
  - **Python 原型**（根目录 `.py` 文件）：无需编译，安装依赖后直接运行，适合快速体验与验证。
  - **C++ 生产版**（`src/` 目录）：基于 Qt6 + OpenCV + DXGI 硬件加速捕获，性能更高、延迟更低。

## 文件结构

```
RealTimeMix/
├── CMakeLists.txt              # C++ 构建配置
├── main.py                     # Python 入口
├── seed.py                     # 种子编解码（与 C++ 兼容）
├── scrambler.py                # 混淆/解混淆核心
├── lens_widget.py              # 解密透镜窗口
├── main_window.py              # 主界面
├── src/                        # C++ 源码
│   ├── main.cpp
│   ├── core/
│   │   ├── seed.h / seed.cpp
│   │   ├── scrambler.h / scrambler.cpp
│   │   ├── screen_capture.h / screen_capture_win.cpp   # DXGI 屏幕捕获
│   ├── ui/
│   │   ├── lens_widget.h / lens_widget.cpp
│   │   ├── main_window.h / main_window.cpp
│   └── utils/
│       └── base64.h / base64.cpp
```

## Python 原型快速开始

### 环境要求
- Python 3.10+
- Windows（屏幕捕获依赖 Windows API，其他平台可手动替换为相应截屏库）

### 安装依赖
```bash
pip install PyQt6 opencv-python numpy
```

### 运行
```bash
python main.py
```

### 使用说明
1. **加密**：切换到 "Encrypt" 标签页，选择图片或视频，调整块大小，点击 "Scramble & Save"。下方会显示生成的种子。
2. **解密透镜**：切换到 "Decrypt Lens" 标签页，粘贴种子，点击 "Start Lens"。透镜窗口会出现在屏幕上，拖动到任意位置即可实时解混淆该区域。
3. **透镜交互**：
   - **左键拖拽**：移动窗口
   - **右键菜单**：调整大小预设（480p/720p/1080p/自定义）或关闭透镜

## C++ 生产版编译

### 依赖
- CMake 3.20+
- Qt6 (Core, Widgets, Gui, Multimedia, MultimediaWidgets, OpenGLWidgets)
- OpenCV 4.x
- Windows SDK（用于 DXGI Desktop Duplication API）
- MSVC 2019+ 或 MinGW-w64

### 编译步骤
```bash
# 配置（根据实际安装路径修改 CMAKE_PREFIX_PATH）
cmake -B build -S . -DCMAKE_PREFIX_PATH="C:/opencv/build;C:/Qt/6.5.3/msvc2019_64"

# 构建
cmake --build build --config Release

# 运行
./build/Release/RealTimeMix.exe
```

> **提示**：确保 OpenCV 和 Qt6 的运行时 DLL 在可执行文件目录或系统 PATH 中。

## 算法说明

### 混淆（Scramble）
1. 将图像/帧切分为 `block_size × block_size` 的网格。
2. 使用种子初始化 `mt19937_64` 伪随机数生成器。
3. 通过 Fisher-Yates shuffle 生成块置换表 `P`。
4. 将第 `i` 个源块复制到目标帧的第 `P[i]` 个位置。
5. 边缘不足一整块的部分保留原样。

### 解混淆（Descramble）
利用种子的逆运算：`dst[i] = src[P[i]]`，将像素块还原到正确位置。

### 种子格式（20 字节，Base64 URL-safe）
| 字段 | 大小 | 说明 |
|------|------|------|
| version | 1B | 协议版本（当前为 1） |
| aspect_w / aspect_h | 各 2B | 原始媒体长宽比 |
| block_size | 2B | 混淆块大小（像素） |
| algorithm | 1B | 算法标识（0 = 块置换） |
| seed | 8B | 64 位随机种子 |
| crc32 | 4B | 前 16 字节 CRC32 校验 |

## 性能与优化

| 版本 | 屏幕捕获 | 解混淆 | 适用场景 |
|------|----------|--------|----------|
| Python | `QScreen.grabWindow` (GDI) | CPU (OpenCV) | 原型验证、中小窗口预览 |
| C++ | DXGI Desktop Duplication | CPU/OpenCL (OpenCV UMat) | 高分辨率、低延迟、大窗口 |

C++ 版本可通过以下方式进一步优化：
- 使用 OpenCL/CUDA 加速块置换（OpenCV `cv::UMat`）。
- 使用 GPU 直通渲染（OpenGL/DirectX 纹理）减少 CPU→GPU 拷贝。

## 注意事项

1. **视频编码**：输出视频默认使用 `mp4v` 编码器。如果系统缺少对应编码支持，可尝试改为 `avc1` 或 `XVID`。
2. **DXGI 捕获**：C++ 版本的 DXGI 屏幕捕获在 UAC 提升窗口、锁屏、部分全屏游戏场景下可能暂时不可用，程序会自动跳过帧并使用上一帧内容。
3. **Python 透镜帧率**：默认锁定约 30fps 以平衡 CPU 占用。如果机器性能较强，可在 `lens_widget.py` 中降低 `timer.setInterval()` 的值。
4. **跨显示器**：当前版本默认捕获主显示器。多显示器环境下，若透镜拖到副显示器，捕获内容可能为黑屏或错位（C++ 版本可通过枚举 `IDXGIOutput` 扩展支持）。

## 许可

MIT License
