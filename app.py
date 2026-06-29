import streamlit as st
import google.generativeai as genai
from PIL import Image

# API 키 설정
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

st.title("🍎 스마트 영양사 프로")
st.write("사진을 여러 장 올리거나, 직접 먹은 음식을 입력해 영양 성분을 확인하세요.")

# 두 개의 탭 생성
tab1, tab2 = st.tabs(["📸 사진 여러 장 합산 분석", "✍️ 직접 타이핑해서 검색"])

model = genai.GenerativeModel('gemini-pro')

# 첫 번째 탭: 사진 여러 장 합산 기능
with tab1:
    st.subheader("여러 장의 사진을 한 번에 올려주세요")
    st.info("식판 사진, 간식 사진 등 여러 장을 선택할 수 있습니다.")
    
    # accept_multiple_files=True 로 여러 장 업로드 허용
    uploaded_files = st.file_uploader("음식 사진들 업로드", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files and st.button("사진 영양 합산하기"):
        with st.spinner("사진들을 분석하여 영양소를 모두 더하는 중입니다..."):
            images = [Image.open(file) for file in uploaded_files]
            
            prompt = """
            제공된 모든 음식 사진들을 식별하고, 각 음식의 영양 성분(칼로리, 탄수화물, 단백질, 지방)을 분석해 줘.
            마지막에는 사용자가 먹은 모든 음식의 영양 성분을 전부 더한 **'총 합산 영양 성분'**을 깔끔한 표 형식으로 정리해서 보여줘.
            """
            
            # 프롬프트와 여러 장의 이미지 리스트를 함께 전송
            response = model.generate_content([prompt] + images)
            st.markdown(response.text)

# 두 번째 탭: 텍스트 직접 입력 기능
with tab2:
    st.subheader("먹은 음식을 직접 적어주세요")
    st.info("사진을 못 찍었을 때 유용합니다.")
    
    food_text = st.text_input("예: 점심으로 콩국수 1그릇과 떡갈비 2개 먹었어")
    
    if food_text and st.button("텍스트 영양 분석하기"):
        with st.spinner("입력하신 음식의 영양 정보를 검색 중입니다..."):
            prompt = f"""
            사용자가 다음 음식을 먹었습니다: '{food_text}'
            이 음식들의 총 칼로리, 탄수화물, 단백질, 지방을 추정하여 한눈에 보기 쉬운 표로 정리해 줘.
            그리고 이 식단에 대한 간단한 영양 평가(부족한 영양소나 주의할 점)를 덧붙여 줘.
            """
            
            response = model.generate_content(prompt)
            st.markdown(response.text)
