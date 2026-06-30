import streamlit as st
from google import genai
from PIL import Image
import json
import pandas as pd
import io

# --- 1. 기본 UI 설정 ---
st.set_page_config(page_title="스마트 영양사 3.5", page_icon="🍎", layout="wide")

# --- 2. 최신 SDK 세팅 ---
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

# --- 3. 프롬프트 및 분석 로직 ---
system_prompt = """
당신은 엄격한 스마트 영양사입니다. 사용자가 입력한 음식의 공식 영양성분을 제공하세요.
- 브랜드 음식은 공식 데이터를 최우선으로 합니다.
- 추측하지 말고, 검색 기능을 활용해 정확한 수치를 찾으세요.
- 반드시 아래 형식의 JSON 데이터를 결과 끝에 포함하세요.
[형식]
... (중략: 기존 형식과 동일) ...
---DATA---
{"cal": 0, "carb": 0, "protein": 0, "fat": 0}
"""

def analyze(text, image=None):
    contents = [text]
    if image:
        contents.append(image)
        
    # 최신 SDK의 검색 기능(Google Search) 활성화
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=contents,
        config={
            "tools": [{"google_search": {}}],
            "system_instruction": system_prompt
        }
    )
    return response.text

# --- 4. 화면 구성 ---
st.title("🍎 스마트 영양사 프로 (3.5 Flash)")
food_text = st.text_input("음식 이름 입력")
if st.button("분석"):
    with st.spinner("최신 모델 검색 중..."):
        try:
            res = analyze(food_text)
            st.write(res)
        except Exception as e:
            st.error(f"라이브러리 문제 해결: {e}")
