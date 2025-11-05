# 抖音视频解析功能改进

## 主要变更

### 从外部API改为本地解析

**之前**：依赖外部API（`https://zerorust.dev/api/douyin`）
**现在**：直接请求抖音页面并解析HTML数据

## 技术实现

### 解析流程

1. **URL重定向**：使用 `requests` 跟随短链接重定向到完整URL
2. **获取HTML**：请求移动端页面获取HTML内容
3. **提取数据**：从HTML中的 `RENDER_DATA` script标签提取JSON数据
4. **解析JSON**：URL解码后解析JSON，提取视频信息
5. **格式化输出**：转换为统一的数据格式

### 核心代码

```python
def parse_douyin_url(url):
    # 1. 使用移动端User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.douyin.com/'
    }
    
    # 2. 跟随重定向获取最终URL
    redirect_response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
    final_url = redirect_response.url
    
    # 3. 获取HTML内容
    html_response = requests.get(final_url, headers=headers, timeout=15)
    html_content = html_response.text
    
    # 4. 提取RENDER_DATA
    render_data_match = re.search(r'<script id="RENDER_DATA" type="application/json">([^<]+)</script>', html_content)
    encoded_data = render_data_match.group(1)
    decoded_data = urllib.parse.unquote(encoded_data)
    data = json.loads(decoded_data)
    
    # 5. 解析aweme_detail
    aweme_detail = data['23']['aweme']['detail']  # 或 data['aweme']['detail']
    
    # 6. 提取各项信息
    result = {
        'desc': aweme_detail.get('desc'),
        'author_name': aweme_detail.get('authorInfo', {}).get('nickname'),
        'comment_count': aweme_detail.get('stats', {}).get('commentCount'),
        'like_count': aweme_detail.get('stats', {}).get('diggCount'),
        'share_count': aweme_detail.get('stats', {}).get('shareCount'),
        'collect_count': aweme_detail.get('stats', {}).get('collectCount')
    }
    
    # 7. 处理视频/图片
    if aweme_detail.get('images'):
        # 图片集
        result['images'] = [img['urlList'][0] for img in aweme_detail['images']]
    else:
        # 视频
        result['video_url'] = aweme_detail['video']['playAddr'][0]['src']
    
    return result
```

## 优势

### 1. 无需外部依赖
- ✅ 不依赖第三方API服务
- ✅ 避免API限流和服务不可用问题
- ✅ 更快的响应速度（直连抖音）

### 2. 更稳定可靠
- ✅ 直接从抖音官方页面获取数据
- ✅ 数据结构稳定（页面渲染数据）
- ✅ 支持短链接自动跳转

### 3. 功能完整
- ✅ 支持视频和图片集
- ✅ 获取完整统计数据（评论、点赞、分享、收藏）
- ✅ 获取作者信息和发布时间
- ✅ 自动处理视频URL（去除水印标记）

## 数据结构

### 输入
```python
url = "https://v.douyin.com/xxxxxxx/"  # 短链接
# 或
url = "https://www.douyin.com/video/xxxxxxx"  # 完整链接
```

### 输出
```python
{
    'code': 200,
    'message': 'success',
    'data': {
        'awemeId': '视频ID',
        'desc': '视频描述',
        'create_time': '2025-09-13 17:23:55',
        'author_name': '作者昵称',
        'cover': '封面图URL',
        'comment_count': 180,
        'like_count': 17000,
        'share_count': 1900,
        'collect_count': 2900,
        'type': 'video',  # 或 'image'
        'video_url': '视频URL',  # 视频类型
        'images': ['图片URL1', '图片URL2']  # 图片类型
    }
}
```

## 关键技术点

### 1. User-Agent
使用移动端User-Agent（iPhone Safari）确保获取移动端页面，数据结构更简单

### 2. RENDER_DATA提取
抖音页面在 `<script id="RENDER_DATA">` 中包含完整的页面数据：
- URL编码的JSON字符串
- 需要先URL解码再JSON解析
- 数据路径：`data['23']['aweme']['detail']` 或 `data['aweme']['detail']`

### 3. 视频URL处理
```python
# 去除水印标记
video_url = video_url.replace('playwm', 'play')
```

### 4. 错误处理
- 网络超时处理
- 页面解析失败处理
- 详细的错误追踪（traceback）

## 移植自TypeScript源码

原始TypeScript代码位于：
- `tool/douyin.ts` - 数据解析逻辑
- `tool/douyin-note.ts` - Playwright浏览器自动化

Python实现简化了流程：
- 不需要Playwright浏览器（直接HTTP请求）
- 不需要缓存层（Streamlit有会话状态）
- 保留了核心的数据提取逻辑

## 兼容性

✅ 支持所有抖音链接格式：
- `v.douyin.com/xxx/`
- `www.douyin.com/video/xxx`
- `m.douyin.com/xxx`
- 带参数的完整链接

✅ 自动处理：
- 短链接跳转
- URL编码解码
- 时间戳格式化
- 视频/图片类型判断
