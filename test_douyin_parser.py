#!/usr/bin/env python3
"""
测试抖音视频解析功能
"""

import requests
import re
import json
import time
import urllib.parse

def parse_douyin_url(url):
    """
    解析抖音视频链接
    
    Args:
        url: 抖音视频链接（支持短链接和完整链接）
    
    Returns:
        dict: 包含视频信息的字典
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.douyin.com/'
    }
    
    print(f"📝 原始链接: {url}")
    
    # 跟随重定向
    redirect_response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
    final_url = redirect_response.url
    print(f"🔗 最终链接: {final_url}")
    
    # 获取HTML内容
    html_response = requests.get(final_url, headers=headers, timeout=15)
    html_content = html_response.text
    print(f"📄 HTML长度: {len(html_content)} 字符")
    
    # 提取RENDER_DATA
    render_data_match = re.search(r'<script id="RENDER_DATA" type="application/json">([^<]+)</script>', html_content)
    if not render_data_match:
        print("❌ 未找到RENDER_DATA")
        return None
    
    print("✅ 找到RENDER_DATA")
    
    # URL解码
    encoded_data = render_data_match.group(1)
    decoded_data = urllib.parse.unquote(encoded_data)
    print(f"📦 解码后数据长度: {len(decoded_data)} 字符")
    
    # JSON解析
    data = json.loads(decoded_data)
    
    # 尝试多个路径
    aweme_detail = None
    if '23' in data and 'aweme' in data['23'] and 'detail' in data['23']['aweme']:
        aweme_detail = data['23']['aweme']['detail']
        print("✅ 从路径 data['23']['aweme']['detail'] 获取数据")
    elif 'aweme' in data and 'detail' in data['aweme']:
        aweme_detail = data['aweme']['detail']
        print("✅ 从路径 data['aweme']['detail'] 获取数据")
    
    if not aweme_detail:
        print("❌ 未找到aweme_detail")
        print("可用的顶级键:", list(data.keys()))
        return None
    
    # 构建结果
    result = {
        'code': 200,
        'message': 'success',
        'data': {
            'awemeId': aweme_detail.get('awemeId', ''),
            'desc': aweme_detail.get('desc', ''),
            'create_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(aweme_detail.get('createTime', 0))),
            'author_name': aweme_detail.get('authorInfo', {}).get('nickname', ''),
            'author': aweme_detail.get('authorInfo', {}).get('nickname', ''),
            'nickname': aweme_detail.get('authorInfo', {}).get('nickname', ''),
            'cover': '',
            'comment_count': aweme_detail.get('stats', {}).get('commentCount', 0),
            'like_count': aweme_detail.get('stats', {}).get('diggCount', 0),
            'digg_count': aweme_detail.get('stats', {}).get('diggCount', 0),
            'share_count': aweme_detail.get('stats', {}).get('shareCount', 0),
            'collect_count': aweme_detail.get('stats', {}).get('collectCount', 0)
        }
    }
    
    # 处理图片/视频
    images = aweme_detail.get('images', [])
    if images:
        result['data']['type'] = 'image'
        result['data']['images'] = []
        for img in images:
            url_list = img.get('urlList', [])
            if url_list:
                result['data']['images'].append(url_list[0])
        if result['data']['images']:
            result['data']['cover'] = result['data']['images'][0]
        print(f"🖼️ 图片集，共 {len(result['data']['images'])} 张")
    else:
        result['data']['type'] = 'video'
        
        video_url = None
        play_addr = aweme_detail.get('video', {}).get('playAddr', [])
        if play_addr and len(play_addr) > 0:
            video_url = play_addr[0].get('src', '')
        
        if not video_url:
            play_api = aweme_detail.get('video', {}).get('playApi', '')
            if play_api:
                video_url = play_api
        
        if video_url:
            video_url = video_url.replace('playwm', 'play')
            result['data']['video_url'] = video_url
            print(f"🎬 视频: {video_url[:60]}...")
        
        cover_list = aweme_detail.get('video', {}).get('cover', {}).get('urlList', [])
        if cover_list:
            result['data']['cover'] = cover_list[0]
    
    return result

def main():
    print("=" * 60)
    print("抖音视频解析测试")
    print("=" * 60)
    
    # 测试URL（需要替换成有效的抖音链接）
    test_url = input("\n请输入抖音链接: ").strip()
    
    if not test_url:
        print("❌ 未提供链接")
        return
    
    try:
        result = parse_douyin_url(test_url)
        
        if result:
            print("\n" + "=" * 60)
            print("✅ 解析成功")
            print("=" * 60)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("\n❌ 解析失败")
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
