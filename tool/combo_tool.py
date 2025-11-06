import streamlit as st
import requests

def main():
    st.set_page_config(page_title="视频播放器", page_icon="🎬", layout="wide")
    
    st.title("🎬 在线视频播放器")
    st.markdown("直接输入视频直链地址即可播放")
    
    # 输入视频链接
    video_url = st.text_input(
        "视频链接:",
        placeholder="请输入视频直链地址 (支持 mp4, webm, ogg 等格式)",
        key="video_url"
    )
    
    # 预置一些示例链接（可选）
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("示例1 - 测试视频"):
            st.session_state.video_url = "https://www.sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
    with col2:
        if st.button("示例2 - 测试视频"):
            st.session_state.video_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    
    # 播放选项
    col1, col2, col3 = st.columns(3)
    with col1:
        autoplay = st.checkbox("自动播放", value=False)
    with col2:
        muted = st.checkbox("静音", value=False)
    with col3:
        loop = st.checkbox("循环播放", value=False)
    
    # 播放视频
    if video_url:
        try:
            st.video(video_url, autoplay=autoplay, muted=muted, loop=loop)
            st.success("视频加载成功！")
            
            # 显示视频信息
            st.subheader("视频信息")
            st.code(f"视频链接: {video_url}")
            
        except Exception as e:
            st.error(f"视频播放失败: {str(e)}")
            st.info("请检查链接是否有效且支持直接播放")
    else:
        st.info("请在上方输入视频链接开始播放")

if __name__ == "__main__":
    main()
