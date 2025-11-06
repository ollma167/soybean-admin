# 🎬 视频播放器工具

这是一个简单的视频直链播放器，使用 Streamlit 构建。

## 功能特点

- ✅ 支持多种视频格式（mp4, webm, ogg等）
- ✅ 直接输入视频直链即可播放
- ✅ 支持自动播放、静音、循环播放选项
- ✅ 内置测试视频示例

## 安装依赖

```bash
cd tool
pip install -r requirements.txt
```

或者使用国内镜像加速：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 使用方法

1. 安装依赖后，在 tool 目录下运行：

```bash
streamlit run combo_tool.py
```

2. 浏览器会自动打开，如果没有自动打开，请访问：`http://localhost:8501`

3. 在输入框中粘贴视频直链地址，点击播放即可

## 支持的视频格式

- MP4 (.mp4)
- WebM (.webm)
- Ogg (.ogg)
- 其他浏览器支持的视频格式

## 注意事项

- 视频链接必须是可公开访问的直链
- 确保视频服务器允许跨域访问
- 某些受保护的视频可能无法播放
