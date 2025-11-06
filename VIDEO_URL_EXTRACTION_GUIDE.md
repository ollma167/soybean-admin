# 抖音视频URL提取指南

## 问题描述

用户反馈：可以获取视频信息（作者、点赞数等），但无法获取视频URL

## 解决方案

### 增强的视频URL提取逻辑

代码现在会按优先级尝试6种不同的方法来提取视频URL：

#### 方法1: playAddr 数组
```python
play_addr = video_info.get('playAddr', [])
# 支持: 
# - list[dict] -> play_addr[0]['src']
# - list[str] -> play_addr[0]
```

#### 方法2: playApi 字段
```python
play_api = video_info.get('playApi', '')
```

#### 方法3: bitRateList（选择最高码率）
```python
bit_rate_list = video_info.get('bitRateList', [])
# 遍历所有码率选项，选择bitRate最高的
# 支持字段: playApi, playAddr
```

#### 方法4: H265/H264编码
```python
# 按优先级尝试
for field in ['playAddrH265', 'playAddrH264', 'playAddrLowbr']:
    play_addr_h = video_info.get(field, [])
```

#### 方法5: 直接字段
```python
video_url = video_info.get('src', '') or video_info.get('url', '')
```

#### 方法6: downloadAddr
```python
download_addr = video_info.get('downloadAddr', {})
url_list = download_addr.get('urlList', [])
```

### URL清理和格式化

```python
# 1. 去除水印标记
video_url = video_url.replace('playwm', 'play')

# 2. 转义字符处理
video_url = video_url.replace('\\u002F', '/')

# 3. 补全协议
if not video_url.startswith('http'):
    if video_url.startswith('//'):
        video_url = 'https:' + video_url
    else:
        video_url = 'https://' + video_url
```

## 调试功能

### 查看原始视频信息结构

当视频URL提取失败时，会显示警告并提供调试信息：

```
⚠️ 视频信息已解析，但未找到视频URL

🔍 查看视频字段结构（调试用）
{
  "playAddr": [...],
  "playApi": "...",
  "bitRateList": [...],
  ...
}
```

### 使用测试脚本

```bash
python3 test_douyin_parser.py
```

测试脚本会输出详细的提取过程：
- 每个字段的尝试结果
- bitRateList中的所有选项
- 最终选择的URL

示例输出：
```
📦 视频信息字段: ['playAddr', 'playApi', 'bitRateList', 'cover', ...]
🔍 检查 bitRateList (3 个选项)
   选项 1: bitRate=1234567, 字段=['playApi', 'bitRate', 'width', 'height']
   选项 2: bitRate=2345678, 字段=['playApi', 'bitRate', 'width', 'height']
   选项 3: bitRate=3456789, 字段=['playApi', 'bitRate', 'width', 'height']
✅ 从 bitRateList 获取 (码率 3456789): https://v26-web.douyinvod.com/...
🎬 最终视频URL: https://v26-web.douyinvod.com/...
```

## 常见问题

### Q1: 为什么视频URL为空？

**可能原因：**
1. 抖音改变了数据结构
2. 视频字段使用了新的命名
3. 视频需要特殊权限访问

**排查步骤：**
1. 查看 "🔍 查看视频字段结构" 中的原始数据
2. 运行 `test_douyin_parser.py` 查看详细提取过程
3. 检查 `_raw_video_info` 中是否有URL相关字段

### Q2: 视频URL存在但无法下载？

**可能原因：**
1. 需要特定的请求头（Referer, User-Agent）
2. URL有时效性（临时链接）
3. 需要Cookie认证

**解决方法：**
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) ...',
    'Referer': 'https://www.douyin.com/'
}
requests.get(video_url, headers=headers)
```

### Q3: playwm vs play？

带 `playwm` 的URL通常是带水印的版本，替换为 `play` 可以获取无水印版本。

```python
video_url = video_url.replace('playwm', 'play')
```

## 数据结构示例

### 完整的video字段结构

```json
{
  "video": {
    "playAddr": [
      {
        "src": "https://v26-web.douyinvod.com/..."
      }
    ],
    "playApi": "https://www.douyin.com/aweme/v1/play/...",
    "bitRateList": [
      {
        "playApi": "https://...",
        "bitRate": 3456789,
        "width": 1080,
        "height": 1920
      }
    ],
    "cover": {
      "urlList": ["https://..."]
    },
    "duration": 15000,
    "width": 1080,
    "height": 1920
  }
}
```

## 最佳实践

1. **优先使用高质量源**：bitRateList中选择最高码率
2. **保留原始信息**：`_raw_video_info` 用于调试
3. **容错处理**：支持多种数据类型（list/dict/str）
4. **URL标准化**：统一处理协议、转义字符、水印标记
