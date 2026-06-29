import streamlit as st
import google.generativeai as genai
from PIL import Image

api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

st.title("🍎 스마트 영양사")
st.write("먹기 전 사진과 남은 사진을 올리면 섭취한 영양 성분을 분석합니다.")

col1, col2 = st.columns(2)
with col1:
    before_img = st.file_uploader("먹기 전 사진", type=["jpg", "png"])
with col2:
    after_img = st.file_uploader("먹고 남은 사진", type=["jpg", "png"])

if before_img and after_img and st.button("분석 시작"):
    with st.spinner("분석 중입니다..."):
        before = Image.open(before_img)
        after = Image.open(after_img)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "두 사진을 비교해서 사용자가 먹은 양의 비율을 계산하고, 이 음식의 전체 영양 성분 대비 '실제 섭취한 칼로리와 탄수화물/단백질/지방'을 표로 깔끔하게 정리해줘."
        
        response = model.generate_content([prompt, before, after])
        st.markdown(response.text)
