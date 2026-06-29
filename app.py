import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- 1. 모바일 친화적 UI 설정 ---
st.set_page_config(page_title="스마트 영양사 프로 from건아", page_icon="🍎", layout="centered")

# --- 2. API 키 및 모델 설정 (수정 완료된 부분) ---
api_key = st.secrets["GEMINI_API_KEY"] 
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 3. 사이드바: 개인 맞춤형 프로필 & 오늘의 운동 ---
with st.sidebar:
    st.header("👤 나의 신체 정보")
    weight = st.number_input("체중 (kg)", min_value=30, max_value=150, value=70)
    
    st.header("🏃‍♂️ 오늘의 활동량")
    # 러닝 거리를 입력받아 칼로리와 단백질 요구량을 계산
    running_km = st.slider("오늘의 러닝 거리 (km)", 0.0, 20.0, 0.0, step=0.5)
    
    # 목표량 자동 계산 로직
    base_cal = weight * 24 * 1.2 # 기초 대사량 기반 대략적 유지 칼로리
    burned_cal = running_km * 70 # km당 약 70kcal 소모 가정
    target_cal = int(base_cal + burned_cal)
    
    # 러닝 거리가 0보다 크면 고단백 모드(체중 1.5g) 발동, 아니면 일반 모드(체중 1.0g)
    protein_multiplier = 1.6 if running_km > 0 else 1.0
    target_protein = int(weight * protein_multiplier)
    target_carb = int((target_cal * 0.4) / 4) # 탄수화물 40% 비중
    target_fat = int((target_cal * 3) / 9)    # 지방 30% 비중
    
    st.info(f"🔥 러닝 소모 칼로리: +{int(burned_cal)} kcal")
    if running_km > 0:
        st.success("근육 회복을 위해 고단백 식단을 추천합니다!")

# --- 4. 하루 누적 데이터를 위한 세션 상태 초기화 ---
if 'cal' not in st.session_state:
    st.session_state.update({"cal": 0, "carb": 0, "protein": 0, "fat": 0})

# --- 5. 마법의 프롬프트 ---
system_prompt = f"""
당신은 사용자의 건강을 책임지는 '팩트폭력' 스마트 영양사입니다. 
제공된 사진, 영수증, 텍스트, 또는 음성을 분석하여 영양 성분을 계산하세요.
반드시 아래의 [형식]에 맞춰 두 부분으로 나누어 출력해야 합니다. 
'---DATA---' 아래에는 오직 JSON만 적어야 합니다.

[형식]
[식단 기록용 요약]
* 메뉴명: [음식 이름]
* 총 칼로리: [000] kcal
* 탄수화물: [00] g
* 단백질: [00] g
* 지방: [00] g
* 당류: [00] g
* 나트륨: [000] mg
* AI 코멘트: [오늘의 러닝 거리({running_km}km)와 고단백 목표를 고려하여, 칭찬할 건 칭찬하고 나트륨/당류 폭발 시 따끔하게 팩트폭력 피드백 1줄 작성]

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
        
        st.success("분석 완료! 우측 상단 아이콘을 눌러 복사하세요.")
        st.code(text_part.strip(), language="text")
        
    except Exception as e:
        st.warning("데이터 누적에는 실패했지만, 결과는 정상적으로 추출되었습니다.")
        st.code(response_text, language="text")

# --- 6. 메인 화면 UI 및 맞춤형 대시보드 ---
st.title("🍎 스마트 영양사 프로")

st.subheader("📊 오늘의 누적 영양소 (목표량 대비)")
col1, col2, col3, col4 = st.columns(4)
# 사이드바에서 계산된 개인별 맞춤 목표량이 대시보드에 반영됨
col1.metric("칼로리", f"{st.session_state.cal} / {target_cal} kcal")
col2.metric("탄수화물", f"{st.session_state.carb} / {target_carb} g")
col3.metric("단백질", f"{st.session_state.protein} / {target_protein} g")
col4.metric("지방", f"{st.session_state.fat} / {target_fat} g")
st.divider()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📸 사진/영수증", "✍️ 텍스트", "🎙️ 음성 녹음"])

# --- 탭 1: 사진 및 영수증 ---
with tab1:
    col_cam, col_up = st.columns(2)
    with col_cam:
        camera_photo = st.camera_input("📸 바로 촬영", key="cam")
    with col_up:
        uploaded_files = st.file_uploader("📂 사진 선택", type=['png', 'jpg'], accept_multiple_files=True, key="files")
    
    if st.button("분석하기", use_container_width=True, key="btn1"):
        images = []
        if camera_photo: images.append(Image.open(camera_photo))
        if uploaded_files: images.extend([Image.open(f) for f in uploaded_files])
        
        if images:
            with st.spinner("이미지를 꼼꼼히 분석 중입니다..."):
                response = model.generate_content([system_prompt] + images)
                process_response(response.text)
        else:
            st.warning("사진을 촬영하거나 업로드해주세요!")

# --- 탭 2: 텍스트 입력 ---
with tab2:
    food_text = st.text_area(
        "먹은 음식과 양을 편하게 적어주세요.",
        placeholder="예: 러닝 후 고단백 쉐이크 1잔, 닭가슴살 샐러드 먹었어",
        height=100
    )
    if st.button("분석하기", use_container_width=True, key="btn2"):
        if food_text:
            with st.spinner("문맥을 파악하여 영양소를 계산 중입니다..."):
                response = model.generate_content([system_prompt, food_text])
                process_response(response.text)
        else:
            st.warning("텍스트를 입력해주세요!")

# --- 탭 3: 음성 입력 ---
with tab3:
    st.info("타이핑도 귀찮을 때, 버튼을 누르고 오늘 먹은 식단을 말해보세요!")
    audio_value = st.audio_input("음성으로 기록하기")
    
    if audio_value:
        with st.spinner("목소리를 듣고 영양소를 계산 중입니다..."):
            audio_part = {
                "mime_type": "audio/wav",
                "data": audio_value.getvalue()
            }
            response = model.generate_content([system_prompt, audio_part])
            process_response(response.text)
