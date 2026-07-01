import streamlit as st
from google import genai
from PIL import Image
import json
import pandas as pd
import datetime

# --- 1. 기본 UI 및 세션 설정 ---
st.set_page_config(page_title="스마트 영양사 프로", page_icon="🍎", layout="wide")

if "food_records" not in st.session_state:
    st.session_state.food_records = []
    
if "current_result" not in st.session_state:
    st.session_state.current_result = None

# --- 2. 사이드바: 내 정보 및 목표 설정 ---
with st.sidebar:
    st.header("⚙️ 내 정보 설정")
    weight = st.number_input("현재 몸무게 (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.5)
    goal_mode = st.selectbox("현재 목표", ["다이어트 (감량)", "체중 유지", "벌크업 (증량)"])
    
    # 몸무게 기반 간단한 목표 칼로리 계산식 (활동량 보통 기준)
    if goal_mode == "다이어트 (감량)":
        target_cal = int(weight * 25)
    elif goal_mode == "벌크업 (증량)":
        target_cal = int(weight * 35)
    else:
        target_cal = int(weight * 30)
        
    st.success(f"🎯 하루 목표 칼로리: **{target_cal} kcal**")
    st.caption("몸무게와 목표를 기준으로 자동 계산되었습니다.")

# --- 3. API 세팅 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error("API 키 설정에 문제가 있습니다. secrets.toml 파일을 확인해주세요.")
    st.stop()

# --- 4. 분석 함수 ---
def analyze(mode, text, image=None):
    if mode == "자연어 및 사진 분석 (비율 자동 계산)":
        system_prompt = """
        당신은 고도로 지능적인 스마트 영양사입니다. 사용자가 제공한 텍스트나 사진의 맥락을 완벽하게 이해하여 영양성분을 추론하세요.
        1. 텍스트만 입력된 경우: 사용자가 묘사한 양('조금', '반 공기' 등)을 토대로 비율을 역산하여 정확한 섭취량을 계산하세요.
        2. 사진 + 텍스트인 경우: 사진의 전체 양을 파악하고 사용자의 설명(예: "1/3만 먹음")에 맞게 삭감하여 계산하세요.
        3. 공신력 있는 표준 데이터(식약처, USDA) 기반으로 현실적인 수치를 제시하세요.
        """
    else: 
        system_prompt = """
        당신은 정확한 데이터 추출기입니다. 영양성분표 라벨의 텍스트나 이미지를 있는 그대로 읽어내세요.
        1회 제공량인지 총 내용량인지 텍스트 설명과 함께 고려하여 계산하세요.
        """

    system_prompt += """
    반드시 아래 형식의 순수 JSON 데이터만 결과로 반환하세요. (```json 등 마크다운 제외)
    {
      "food_name": "추론된 실제 섭취 음식 및 양",
      "cal": 0,
      "carb": 0,
      "protein": 0,
      "fat": 0,
      "sugar": 0,
      "others": "나트륨 등 기타 영양소",
      "comment": "계산 과정 및 팁"
    }
    """

    contents = []
    if text:
        contents.append(text)
    if image:
        contents.append(image)
        
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=contents,
        config={
            "tools": [{"google_search": {}}],
            "system_instruction": system_prompt
        }
    )
    return response.text

# --- 5. 메인 화면 UI (입력부) ---
st.title("🍎 스마트 영양사 프로")
st.caption("몸무게 기반 맞춤 목표와 함께, AI가 내가 먹은 양을 찰떡같이 계산합니다!")

analysis_mode = st.radio(
    "분석 방식을 선택하세요:", 
    ["자연어 및 사진 분석 (비율 자동 계산)", "영양성분표 라벨 그대로 읽기"],
    horizontal=True
)

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("📸 사진 업로드 (선택사항)", type=["jpg", "jpeg", "png"])
with col2:
    food_text = st.text_area("📝 무엇을 얼마나 드셨나요?", placeholder="예: 밥 반공기에 제육볶음 조금 먹었어.")

if st.button("🔍 AI 스마트 분석하기"):
    if not uploaded_file and not food_text.strip():
        st.warning("사진을 올리거나, 무엇을 드셨는지 텍스트로 적어주세요!")
    else:
        with st.spinner("드신 양과 비율을 AI가 꼼꼼히 역산 중입니다..."):
            image_obj = Image.open(uploaded_file) if uploaded_file else None
            try:
                res = analyze(analysis_mode, food_text, image_obj)
                start_idx = res.find('{')
                end_idx = res.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = res[start_idx:end_idx]
                    st.session_state.current_result = json.loads(json_str)
                else:
                    st.error("데이터 파싱 실패. 원본 응답을 확인하세요.")
                    st.write(res)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# --- 6. 분석 결과 확인 및 결정(기록) 버튼 ---
if st.session_state.current_result:
    st.divider()
    st.subheader("✅ AI 맞춤 분석 결과 (기록 대기 중)")
    
    data = st.session_state.current_result
    st.markdown(f"#### 🍽️ {data.get('food_name', '알 수 없음')}")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("칼로리", f"{data.get('cal', 0)} kcal")
    c2.metric("탄수화물", f"{data.get('carb', 0)} g")
    c3.metric("단백질", f"{data.get('protein', 0)} g")
    c4.metric("지방", f"{data.get('fat', 0)} g")
    c5.metric("당류", f"{data.get('sugar', 0)} g")
    
    st.info(f"**기타 영양소:** {data.get('others', '정보 없음')}")
    st.success(f"💡 **AI 계산 코멘트:** {data.get('comment', '')}")
    
    st.warning("위 수치가 맞다면 아래 버튼을 눌러 기록을 확정해 주세요!")
    
    # 🎯 사용자가 최종 결정하는 버튼
    if st.button("📝 이 수치로 오늘의 식단 기록 확정하기", type="primary", use_container_width=True):
        record = {
            "시간": datetime.datetime.now().strftime("%H:%M"),
            "음식명": data.get('food_name', '알 수 없음'),
            "칼로리": float(data.get('cal', 0)),
            "탄수화물": float(data.get('carb', 0)),
            "단백질": float(data.get('protein', 0)),
            "지방": float(data.get('fat', 0)),
            "당류": float(data.get('sugar', 0))
        }
        st.session_state.food_records.append(record)
        st.session_state.current_result = None 
        st.rerun() 

# --- 7. 오늘의 식단 기록 보관함 및 프로그레스 바 ---
st.divider()
st.subheader("📋 오늘 먹은 식단 현황")

if st.session_state.food_records:
    df = pd.DataFrame(st.session_state.food_records)
    st.dataframe(df, use_container_width=True)
    
    # 총 섭취량 계산
    t_cal = df['칼로리'].sum()
    t_carb = df['탄수화물'].sum()
    t_prot = df['단백질'].sum()
    t_fat = df['지방'].sum()
    
    st.markdown("### 📊 칼로리 달성률")
    # 목표 대비 섭취량 프로그레스 바
    progress_ratio = min(t_cal / target_cal, 1.0) # 1.0(100%)이 최대치
    
    st.progress(progress_ratio)
    
    # 색상 피드백
    if t_cal > target_cal:
        st.error(f"🚨 목표 초과! 현재 **{t_cal} kcal** / 목표 {target_cal} kcal")
    elif t_cal > target_cal * 0.9:
        st.warning(f"⚠️ 목표에 거의 도달했습니다. 현재 **{t_cal} kcal** / 목표 {target_cal} kcal")
    else:
        st.success(f"여유가 있습니다. 현재 **{t_cal} kcal** / 목표 {target_cal} kcal")
        
    st.markdown("### 🍽️ 누적 영양소")
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.metric("총 칼로리", f"{t_cal} kcal")
    tc2.metric("총 탄수화물", f"{t_carb} g")
    tc3.metric("총 단백질", f"{t_prot} g")
    tc4.metric("총 지방", f"{t_fat} g")
    
    if st.button("🗑️ 기록 전체 초기화"):
        st.session_state.food_records = []
        st.rerun()
else:
    st.write("아직 확정된 식단 기록이 없습니다.")
