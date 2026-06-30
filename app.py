import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import pandas as pd
from duckduckgo_search import DDGS  # 💡 인터넷 검색을 대신해 줄 파이썬 로봇

# --- 1. 기본 UI 설정 ---
st.set_page_config(page_title="스마트 영양사 프로", page_icon="🍎", layout="wide")

# --- 2. API 키 및 최신 모델 설정 ---
api_key = st.secrets["GEMINI_API_KEY"] 
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 3. 사이드바: 기기 최적화 및 프로필 설정 ---
with st.sidebar:
    st.header("📱 화면 레이아웃 설정")
    layout_mode = st.radio(
        "현재 사용 중인 기기에 맞춰 선택하세요:",
        ["📱 모바일 최적화 (세로형)", "🖥️ 태블릿 최적화 (좌우 분할)"]
    )
    st.divider()

    st.header("👤 나의 상태 및 설정")
    weight = st.number_input("체중 (kg)", min_value=30, max_value=150, value=70)
    
    st.header("🏃‍♂️ 오늘의 활동량")
    running_km = st.slider("오늘의 러닝 거리 (km)", 0.0, 20.0, 0.0, step=0.5)
    
    st.header("⚙️ 스마트 분석 모드")
    shift_mode = st.toggle("🌙 야간 근무/당직 모드 (새벽 식사 포함)")
    junior_mode = st.toggle("👧 성장기 주니어 모드 (아이 맞춤 영양)")

    base_cal = weight * 24 * 1.2
    burned_cal = running_km * 70
    target_cal = int(base_cal + burned_cal)
    
    protein_multiplier = 1.6 if running_km > 0 else 1.0
    target_protein = int(weight * protein_multiplier)
    target_carb = int((target_cal * 0.4) / 4) 
    target_fat = int((target_cal * 0.3) / 9)    
    
    st.info(f"🔥 활동 소모 칼로리: +{int(burned_cal)} kcal")

# --- 4. 세션 상태 초기화 ---
if 'cal' not in st.session_state:
    st.session_state.update({"cal": 0, "carb": 0, "protein": 0, "fat": 0})

# --- 5. 실시간 검색 결과를 주입받는 프롬프트 ---
mode_instructions = ""
if shift_mode:
    mode_instructions += "\n* [근무 모드] 야간/교대 근무 중입니다. 소화 부담에 대한 조언을 1줄 추가하세요."
if junior_mode:
    mode_instructions += "\n* [주니어 모드] 성장기 아이 식단입니다. 당류 제한에 초점을 맞춰 피드백하세요."

# 💡 함수: 사용자가 입력한 음식을 인터넷에 직접 검색해서 텍스트로 긁어오는 로봇
def get_web_search_context(query):
    try:
        results = DDGS().text(f"{query} 영양성분 칼로리 공식", max_results=3)
        search_text = "\n".join([r['body'] for r in results])
        return search_text
    except Exception as e:
        return ""

def generate_nutrition_prompt(user_input, search_context):
    return f"""
    당신은 스마트 영양사입니다. 제공된 텍스트나 사진을 분석하여 영양 성분을 계산하세요. 
    
    [실시간 웹 검색 데이터]
    아래는 방금 인터넷에서 실시간으로 검색해 온 '{user_input}'의 영양 정보입니다. 
    당신의 기존 지식보다 이 데이터를 최우선으로 신뢰하여 오차 없이 정확한 수치를 도출하세요.
    데이터: {search_context}
    
    * [다인분/잔반 분할] 섭취 비율이 적혀있거나 먹고 남은 사진이 있다면 '실제로 섭취한 내 몫'만 계산하세요.{mode_instructions}

    반드시 아래의 [형식]에 맞춰 두 부분으로 나누어 출력하세요. '---DATA---' 아래에는 오직 JSON만 적어야 합니다.

    [형식]
    [식단 기록용 요약]
    * 메뉴명: [음식 이름 (브랜드 반영)]
    * 총 칼로리: [000] kcal
    * 탄수화물: [00] g
    * 단백질: [00] g
    * 지방: [00] g
    * 당류: [00] g
    * 나트륨: [000] mg
    * AI 코멘트: [활동량에 맞춘 피드백 1줄 작성]

    ---DATA---
    {{"cal": 0, "carb": 0, "protein": 0, "fat": 0}}
    """

# 결과 처리 함수
def process_response(response_text):
    try:
        text_part, data_part = response_text.split("---DATA---")
        data = json.loads(data_part.strip())
        st.session_state.cal += int(data.get("cal", 0))
        st.session_state.carb += int(data.get("carb", 0))
        st.session_state.protein += int(data.get("protein", 0))
        st.session_state.fat += int(data.get("fat", 0))
        st.success("✨ 분석 완료! 아래의 텍스트를 복사하세요.")
        st.code(text_part.strip(), language="text")
    except Exception as e:
        st.warning("데이터 추출에는 실패했지만, 분석 결과는 다음과 같습니다.")
        st.code(response_text, language="text")

# --- UI 렌더링 함수 ---
def render_dashboard():
    st.subheader("📊 오늘의 누적 대시보드")
    dash_c1, dash_c2, dash_c3, dash_c4 = st.columns(4)
    dash_c1.metric("칼로리", f"{st.session_state.cal} / {target_cal}")
    dash_c2.metric("탄수화물", f"{st.session_state.carb} / {target_carb}g")
    dash_c3.metric("단백질", f"{st.session_state.protein} / {target_protein}g")
    dash_c4.metric("지방", f"{st.session_state.fat} / {target_fat}g")
    
    df = pd.DataFrame([{
        "날짜": "오늘",
        "총 칼로리": st.session_state.cal, "탄수화물": st.session_state.carb,
        "단백질": st.session_state.protein, "지방": st.session_state.fat
    }])
    csv = df.to_csv(index=False).encode('utf-8-sig')
    
    col_dl, col_rs = st.columns(2)
    with col_dl:
        st.download_button("📥 엑셀 다운로드", data=csv, file_name="report.csv", mime="text/csv", use_container_width=True)
    with col_rs:
        if st.button("🔄 기록 초기화", use_container_width=True):
            st.session_state.update({"cal": 0, "carb": 0, "protein": 0, "fat": 0})
            st.rerun()

def render_input_area():
    st.subheader("📸 사진 및 영양성분표 스캔")
    uploaded_files = st.file_uploader("📂 사진 선택 (여러 장 가능)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    extra_info = st.text_input("📝 추가 설명 (선택)", placeholder="예: 파스쿠찌 아이스 카페라떼 레귤러")
    
    if st.button("사진 영양 분석하기", use_container_width=True):
        if uploaded_files:
            images = [Image.open(f) for f in uploaded_files]
            with st.spinner("웹에서 실시간 영양 데이터를 수집 중입니다..."):
                search_data = get_web_search_context(extra_info if extra_info else "일반 음식")
                final_prompt = generate_nutrition_prompt(extra_info, search_data)
                response = model.generate_content([final_prompt] + images)
                return response.text
        else:
            st.warning("사진을 업로드해주세요!")
            return None
            
    st.divider()
    
    st.subheader("✍️ 텍스트 간편 입력")
    food_text = st.text_area("사진이 없다면 글로 적어주세요.", placeholder="예: 파스쿠찌 아이스 카페라떼 레귤러", height=100)
    if st.button("텍스트 영양 분석하기", use_container_width=True):
        if food_text:
            with st.spinner("웹에서 실시간 영양 데이터를 수집 중입니다..."):
                search_data = get_web_search_context(food_text)
                final_prompt = generate_nutrition_prompt(food_text, search_data)
                response = model.generate_content([final_prompt])
                return response.text
        else:
            st.warning("텍스트를 입력해주세요!")
            return None
    return None

# --- 6. 화면 구성 ---
st.title("🍎 스마트 영양사 프로 (Live DB Edition)")

if "모바일" in layout_mode:
    render_dashboard()
    st.divider()
    result = render_input_area()
    if result:
        st.divider()
        st.markdown("### 📋 분석 결과 화면")
        process_response(result)
else:
    left_col, right_col = st.columns([1, 1], gap="large")
    with left_col:
        result = render_input_area()
    with right_col:
        render_dashboard()
        st.divider()
        st.markdown("### 📋 분석 결과 화면")
        if result:
            process_response(result)
        else:
            st.caption("👈 왼쪽에서 분석을 실행하면 이곳에 상세 결과가 나타납니다.")
