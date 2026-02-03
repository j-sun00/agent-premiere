import streamlit as st
import google.generativeai as genai
import pandas as pd
import yt_dlp
import os
import time
import io

# --- 페르소나 데이터 (변경 없음) ---
PERSONAS = {
    "Alex (북미 하드코어)": {
        "name": "Alex", "description": "20대 후반 IT 엔지니어로, PC와 PS5로 FPS, 소울라이크 같은 하드코어 게임을 즐긴다.", "likes": ["정교한 인게임 플레이 메카닉", "도전 욕구를 자극하는 난이도 설계", "가감 없는 타격감 및 물리 효과"], "dislikes": ["실제 플레이 장면이 거의 없는 풀 시네마틱 영상", "과장된 마케팅 문구", "모바일 게임 스타일의 간소화된 UI"]
    },
    "민준 (한국 모바일)": {
        "name": "민준", "description": "20대 초반 대학생으로, 주로 이동 중에 스마트폰으로 수집형 RPG나 모바일 MMORPG를 즐긴다.", "likes": ["수집욕을 자극하는 매력적인 신규 캐릭터와 코스튬", "화려하고 시원시원한 스킬 이펙트", "자동사냥, 소탕 등 시간을 절약해주는 편의 기능"], "dislikes": ["지나치게 복잡하고 정교한 수동 컨트롤 요구", "너무 어둡고 진지하기만 한 분위기", "낮은 퀄리티의 캐릭터 모델링"]
    },
    "Chloe (글로벌 비주얼러)": {
        "name": "Chloe", "description": "30대 초반 그래픽 디자이너로, 게임을 하나의 예술 작품으로 접근한다. 경험의 질을 중시한다.", "likes": ["독창적인 아트 스타일과 미학적 색감", "영화 같은 시네마틱 연출과 조명 활용", "세계관의 깊이를 보여주는 미려한 배경 및 건축 디자인"], "dislikes": ["다른 게임에서 흔히 본 듯한 양산형 아트 스타일", "화면을 어지럽히는 복잡한 UI", "눈에 띄는 저해상도 텍스처나 깨지는 그래픽"]
    },
    "켄지 (설정 전문가)": {
        "name": "켄지", "description": "30대 초반 대학원생으로, 게임의 서사와 세계관 설정을 깊이 파고드는 것을 즐긴다. 스스로를 '아키비스트'라 칭한다.", "likes": ["세계관의 설정을 유추할 수 있는 상징이나 텍스트", "캐릭터의 대사나 표정에 숨겨진 복선", "기존 시리즈와의 설정 연결성"], "dislikes": ["기존에 구축된 세계관과 충돌하는 설정 오류", "깊이 없이 평면적이고 예측 가능한 스토리", "상황과 맞지 않는 어색한 대사"]
    }
}

# --- 제미나이 설정 ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"API 키 설정에 실패했습니다. `.streamlit/secrets.toml` 파일을 확인해주세요. 오류: {e}")
    st.stop()

# --- Streamlit UI ---
st.set_page_config(page_title="에이전트 프리미어", layout="wide")
# [버전명 수정] v5.0 기반에 UI만 개선했다는 의미로 v5.0.1로 명명
st.title("🎬 에이전트 프리미어 (Agent Premiere) v5.0.1") 

# --- [핵심 변경] v5.0 코드에서 이 부분만 교체 ---
with st.sidebar:
    st.header("👥 페르소나 프로필 & 대표 설정")
    # selectbox가 '대표 페르소나 지정'과 '프로필 뷰어' 역할을 동시에 수행
    selected_persona_name = st.selectbox(
        "대표 페르소나 선택 및 프로필 확인:",
        PERSONAS.keys()
    )
    
    # 선택된 페르소나의 상세 정보를 가져와 사이드바에 표시
    persona_to_display = PERSONAS[selected_persona_name]
    st.markdown("---")
    st.subheader(f"👤 {persona_to_display['name']}")
    st.markdown(f"**설명:** {persona_to_display['description']}")
    st.markdown(f"**👍 선호 요소:**")
    for like in persona_to_display['likes']:
        st.markdown(f"- {like}")
    st.markdown(f"**👎 불호 요소:**")
    for dislike in persona_to_display['dislikes']:
        st.markdown(f"- {dislike}")

# --- (이하 모든 코드는 지선님께서 주신 v5.0 코드와 100% 동일합니다) ---
st.subheader("1. 분석할 영상 선택")
youtube_url = st.text_input("유튜브 영상 URL 붙여넣기:", placeholder="https://www.youtube.com/watch?v=...")
st.markdown("<h5 style='text-align: center; color: grey;'>또는</h5>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("동영상 파일 직접 업로드:", type=['mp4', 'mov', 'avi'])

if st.button("🚀 4인 종합 분석 및 가상 시사회 시작"):
    
    video_path = None
    gemini_video_file = None 
    
    try:
        with st.spinner("영상 파일을 준비하는 중입니다..."):
            if youtube_url:
                source_name = youtube_url
                timestamp = int(time.time())
                video_path = f"temp_video_{timestamp}.mp4"
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': video_path, 'quiet': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(youtube_url, download=True)
                    source_name = info_dict.get('title', youtube_url)
            elif uploaded_file:
                source_name = uploaded_file.name
                timestamp = int(time.time())
                video_path = f"temp_{timestamp}_{uploaded_file.name}"
                with open(video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            else:
                st.warning("분석할 유튜브 URL을 입력하거나 동영상 파일을 업로드해주세요.")
                st.stop()

        with st.spinner("AI가 영상을 인식할 수 있도록 업로드하는 중입니다..."):
            gemini_video_file = genai.upload_file(path=video_path, display_name=source_name)
            while gemini_video_file.state.name == "PROCESSING":
                time.sleep(5)
                gemini_video_file = genai.get_file(gemini_video_file.name)
            if gemini_video_file.state.name == "FAILED":
                 st.error("영상 파일 처리 중 오류가 발생했습니다.")
                 st.stop()

        all_reports = {}
        st.subheader(f"📊 '{source_name}' 종합 분석 결과")

        for persona_key, persona_data in PERSONAS.items():
            with st.spinner(f"AI 에이전트 '{persona_data['name']}'가 영상을 '직접 시청하며' 분석 중입니다..."):
                prompt = f"당신은 게임 트레일러 전문 분석가입니다. 당신의 이름과 역할은 '{persona_data['name']}'입니다.\n\n### 당신의 프로필:\n- 설명: {persona_data['description']}\n- 트레일러에서 중요하게 생각하는 요소: {', '.join(persona_data['likes'])}\n- 트레일러에서 부정적으로 보는 요소: {', '.join(persona_data['dislikes'])}\n\n### 분석 임무:\n지금부터 당신은 첨부된 게임 트레일러 영상을 직접 시청하고, 당신의 프로필에 입각하여 전문적인 분석 리포트를 작성해야 합니다. 아래 형식에 맞춰, 영상의 어떤 장면(시간)에서 긍정적/부정적 인상을 받았는지 구체적인 이유와 함께 서술해주세요.\n\n---\n\n**[총평]**\n(트레일러에 대한 전반적인 인상과 평가를 한두 문장으로 요약)\n\n**[👍 긍정적인 부분]**\n* (언급할 시간) - (긍정적으로 평가한 이유)\n* (언급할 시간) - (긍정적으로 평가한 이유)\n\n**[👎 아쉬운 부분]**\n* (언급할 시간) - (아쉽게 평가한 이유)\n* (언급할 시간) - (아쉽게 평가한 이유)\n\n**[결론 및 제언]**\n(이 트레일러가 당신과 같은 타겟 유저에게 어필할 수 있을지에 대한 최종 의견과 개선점을 제안)"
                
                safety_settings = {'HARM_CATEGORY_HARASSMENT': 'BLOCK_MEDIUM_AND_ABOVE','HARM_CATEGORY_HATE_SPEECH': 'BLOCK_MEDIUM_AND_ABOVE','HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_MEDIUM_AND_ABOVE','HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_MEDIUM_AND_ABOVE'}
                
                response = model.generate_content([prompt, gemini_video_file], safety_settings=safety_settings)
                # 엑셀 시트 이름에는 'Alex'와 같이 이름만 들어가도록, all_reports의 키를 이름으로 저장
                all_reports[persona_data['name']] = response.text
            
            # 사용자가 선택한 대표 페르소나의 결과만 화면에 우선 표시
            if persona_key == selected_persona_name:
                with st.expander(f"💬 '{persona_data['name']}'의 심층 분석 리포트 보기 (클릭)", expanded=True):
                    st.markdown(response.text)

        st.success("✅ 4명의 AI 에이전트가 모두 분석을 완료했습니다!")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for name, report in all_reports.items():
                df = pd.DataFrame([report], columns=['분석 리포트'])
                df.to_excel(writer, sheet_name=name, index=False)
        
        processed_data = output.getvalue()
        
        st.download_button(
            label="📄 종합 리포트 다운로드 (.xlsx)",
            data=processed_data,
            file_name=f"Agent_Premiere_Report_{source_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"작업 중 오류가 발생했습니다. 아래 메시지를 확인해주세요.")
        st.exception(e)

    finally:
        with st.spinner("임시 파일을 정리하는 중입니다..."):
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            if gemini_video_file and gemini_video_file.state.name == "ACTIVE":
                genai.delete_file(gemini_video_file.name)
        st.info("임시 파일 정리가 완료되었습니다.")
