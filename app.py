import streamlit as st
from google import genai
from PIL import Image
import json
import pandas as pd
import datetime

# --- 1. 기본 UI 및 세션 상태(기록 보관) 설정 ---
st.set_page_config(page_title="스마트 영양사 프로", page_icon="🍎", layout="wide")

if "food_records" not in st.session_state:
    st.session_state.food_records = []
    
if "current_result" not in st.session_state:
    st.session_state.current_result = None

# --- 2. API 세팅 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error("API 키 설정에 문제가 있습니다. secrets.toml 파일을 확인해주세요.")
    st.stop()

# --- 3. 분석 함수 ---
def analyze(mode, text, image=None):
    if mode == "음식 사진/텍스트 분석 (표준 데이터 기준)":
        system_prompt = """
        당신은 정확하고 객관적인 스마트 영양사입니다. 사용자가 제공한 음식 사진과 설명을 바탕으로 가장 현실적이고 표준적인 영양성분을 제공하세요.
        [🎯 분석 규칙]
        - 식약처, USDA 등 공신력 있는 표준 레시피 데이터베이스를 기반으로 정확하게 분석하세요.
        - 수치를 의도적으로 과장하거나 줄이지 말고, 아는 한도 내에서 가장 실제와 가까운 평균 수치를 제시하세요.
        - 기타 영양소(나트륨, 식이섬유 등)도 파악되는 대로 추가하세요.
        """
    else: # 영양성분표 라벨 그대로 읽기
        system_prompt = """
        당신은 정확한 데이터 추출기입니다. 사용자가 제공한 '영양성분표' 이미지나 텍스트를 있는 그대로 정확하게 읽어내세요.
        [🎯 라벨 리더 규칙]
        - 절대 수치를 변형하지 말고 이미지나 공식 데이터에 적힌 수치 100% 그대로 반영하세요.
        - 1회 제공량인지 총 내용량인지 고려하여 계산하세요.
        """

    # 공통 JSON 포맷 강제
    system_prompt += """
    반드시 아래 형식의 순수 JSON 데이터만 결과로 반환하세요. (```json 등 마크다운 제외)
    {
      "food_name": "음식 이름 (또는 제품명)",
      "cal": 0,
      "carb": 0,
      "protein": 0,
      "fat": 0,
      "sugar": 0,
      "others": "나트륨 00mg 등 기타 영양소 정보",
      "comment": "이 데이터의 출처(표준 레시피, 공식 라벨 등)나 참고 사항 한 줄"
    }
    """

    contents = []
    if text:
        contents.append(text)
    if image:
        contents.append(image)
        
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=contents,
        config={
            "tools": [{"google_search": {}}],
            "system_instruction": system_prompt
        }
    )
    return response.text

# --- 4. 메인 화면 UI ---
st.title("🍎 스마트 영양사 프로 (정확도 중심 & 기록장)")
st.caption("가장 현실적인 표준 데이터를 바탕으로 영양성분을 분석하고 기록합니다.")

analysis_mode = st.radio(
    "분석 방식을 선택하세요:", 
    ["음식 사진/텍스트 분석 (표준 데이터 기준)", "영양성분표 라벨 그대로 읽기 (정확한 수치)"],
    horizontal=True
)

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("📸 사진 업로드 (음식 또는 라벨)", type=["jpg", "jpeg", "png"])
with col2:
    food_text = st.text_area("📝 음식 이름 및 설명 (예: 스타벅스 아메리카노 톨사이즈, 삼겹살 200g)")

if st.button("🔍 영양성분 분석하기", type="primary"):
    if not uploaded_file and not food_text:
        st.warning("사진을 업로드하거나 텍스트를 입력해 주세요!")
    else:
        with st.spinner("가장 정확한 표준 데이터를 검색하고 분석 중입니다..."):
            image_obj = Image.open(uploaded_file) if uploaded_file else None
            try:
                res = analyze(analysis_mode, food_text, image_obj)
                
                start_idx = res.find('{')
                end_idx = res.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = res[start_idx:end_idx]
                    st.session_state.current_result = json.loads(json_str)
                else:
                    st.error("데이터를 불러오는 데 실패했습니다.")
                    st.write(res)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# --- 5. 분석 결과 및 기록 저장 ---
if st.session_state.current_result:
    st.divider()
    st.subheader("✅ 정확한 분석 결과")
    
    data = st.session_state.current_result
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("칼로리", f"{data.get('cal', 0)} kcal")
    c2.metric("탄수화물", f"{data.get('carb', 0)} g")
    c3.metric("단백질", f"{data.get('protein', 0)} g")
    c4.metric("지방", f"{data.get('fat', 0)} g")
    c5.metric("당류", f"{data.get('sugar', 0)} g")
    
    st.info(f"**기타 영양소:** {data.get('others', '정보 없음')}")
    st.success(f"💡 **AI 코멘트:** {data.get('comment', '')}")
    
    if st.button("💾 이 기록을 오늘 식단에 추가하기"):
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

# --- 6. 오늘의 식단 기록 보관함 ---
st.divider()
st.subheader("📋 오늘 먹은 식단 기록")

if st.session_state.food_records:
    df = pd.DataFrame(st.session_state.food_records)
    st.dataframe(df, use_container_width=True)
    
    st.markdown("### 📊 오늘의 총 누적 섭취량")
    t_cal = df['칼로리'].sum()
    t_carb = df['탄수화물'].sum()
    t_prot = df['단백질'].sum()
    t_fat = df['지방'].sum()
    
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.metric("총 칼로리", f"{t_cal} kcal")
    tc2.metric("총 탄수화물", f"{t_carb} g")
    tc3.metric("총 단백질", f"{t_prot} g")
    tc4.metric("총 지방", f"{t_fat} g")
    
    if st.button("🗑️ 기록 전체 초기화"):
        st.session_state.food_records = []
        st.rerun()
else:
    st.write("아직 기록된 식단이 없습니다. 분석 후 저장 버튼을 눌러주세요!")
