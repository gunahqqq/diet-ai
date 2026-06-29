import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. API 키 및 모델 설정
# Streamlit Secrets에 저장된 키 이름 (보통 GOOGLE_API_KEY 또는 GEMINI_API_KEY)
api_key = st.secrets["GOOGLE_API_KEY"] 
genai.configure(api_key=api_key)

# 최신 모델로 설정 (에러 해결!)
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. 식단 앱 기록용 고정 프롬프트 설정 (당류, 나트륨 포함)
system_prompt = """
당신은 스마트 영양사입니다. 제공된 사진이나 텍스트를 분석하여 영양 성분을 알려주세요.
사용자가 식단 기록 앱에 빠르고 정확하게 입력할 수 있도록, 다른 설명은 생략하고 반드시 아래의 형식으로만 답변하세요.

[식단 기록용 요약]
* 음식명: [분석된 음식 이름]
* 총 칼로리: [000] kcal
* 탄수화물: [00] g
* 단백질: [00] g
* 지방: [00] g
* 당류: [00] g
* 나트륨: [000] mg
* 한줄 메모: [식단에 대한 짧은 팁이나 특징]
"""

# 3. 앱 화면 구성
st.title("🍎 스마트 영양사 프로")
st.write("사진을 여러 장 올리거나, 직접 먹은 음식을 텍스트로 입력해 보세요!")

# 두 개의 탭 생성
tab1, tab2 = st.tabs(["📸 사진 여러 장 합산 분석", "✍️ 텍스트 분석"])

# --- 탭 1: 사진 분석 기능 ---
with tab1:
    st.subheader("여러 장의 사진을 한 번에 올려주세요")
    st.info("식판 사진, 간식 사진 등 여러 장을 선택할 수 있습니다.")
    
    # 여러 장 업로드 가능하도록 accept_multiple_files=True 설정
    uploaded_files = st.file_uploader("음식 사진들 업로드", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    
    if uploaded_files and st.button("사진 영양 합산하기"):
        with st.spinner("사진을 분석하고 있습니다... 잠시만 기다려주세요!"):
            try:
                # 업로드된 파일들을 PIL Image 객체로 변환하여 리스트에 담기
                image_parts = [Image.open(file) for file in uploaded_files]
                
                # 프롬프트와 이미지 리스트를 함께 모델에 전달
                response = model.generate_content([system_prompt] + image_parts)
                
                st.success("분석 완료! 우측 상단 아이콘을 눌러 복사하세요.")
                # st.code를 사용하여 클릭 한 번에 텍스트 복사 가능하게 만들기
                st.code(response.text, language="text")
                
            except Exception as e:
                st.error(f"분석 중 에러가 발생했습니다: {e}")


# --- 탭 2: 텍스트 분석 기능 ---
with tab2:
    st.subheader("먹은 음식을 텍스트로 적어주세요")
    food_text = st.text_area("예: 점심으로 콩국수 1그릇과 떡갈비 2조각 먹었고, 간식으로 아메리카노 마셨어", height=100)
    
    if food_text and st.button("텍스트 영양 분석하기"):
        with st.spinner("텍스트를 분석하고 있습니다... 잠시만 기다려주세요!"):
            try:
                # 프롬프트와 사용자가 입력한 텍스트를 함께 모델에 전달
                response = model.generate_content([system_prompt, food_text])
                
                st.success("분석 완료! 우측 상단 아이콘을 눌러 복사하세요.")
                # st.code를 사용하여 클릭 한 번에 텍스트 복사 가능하게 만들기
                st.code(response.text, language="text")
                
            except Exception as e:
                st.error(f"분석 중 에러가 발생했습니다: {e}")
