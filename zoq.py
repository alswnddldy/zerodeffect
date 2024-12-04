import streamlit as st
import pandas as pd
from collections import Counter
import plotly.express as px
import re

# 불용어 리스트 정의
stop_words = ['은', '는', '이', '가', '을', '를', '에', '에서', '으로', '도', '만', '의', '와', '과', '에게', '한테', '께']

# 불용어 및 특수기호 제거 함수 정의
def clean_text(text):
    if pd.isnull(text):
        return text
    # 특수기호 제거 (정규표현식으로 처리)
    text = re.sub(r'[^\w\s]', '', text)  # \w는 알파벳, 숫자, 밑줄(_) 포함, \s는 공백
    # 불용어를 제거하기 위해 정규표현식 패턴 생성
    pattern = re.compile(r'\b(' + '|'.join(stop_words) + r')\b')
    return pattern.sub('', text)

# 데이터 로딩
data = pd.read_csv('data.csv', on_bad_lines='skip', encoding='utf-8-sig')

# 관련 열에 결측치가 있는 행 제거
filtered_data = data.dropna(subset=['TYPE_GBN_U_NM', 'TYPE_GBN_NM', 'JOCHI_DESCR', 'D_YMD'])

# 'JOCHI_DESCR' 열에 불용어 및 특수기호 제거 적용
filtered_data['JOCHI_DESCR'] = filtered_data['JOCHI_DESCR'].apply(clean_text)

# 연도 추출 후 정수형으로 변환
filtered_data['YEAR'] = pd.to_datetime(filtered_data['D_YMD'], errors='coerce').dt.year.astype('Int64')

# 사이드바: 연도 선택
st.sidebar.header("연도를 선택하세요")
available_years = sorted(filtered_data['YEAR'].dropna().unique())

if len(available_years) == 0:
    st.sidebar.write("데이터에 사용 가능한 연도가 없습니다.")
else:
    selected_year = st.sidebar.selectbox("연도를 선택하세요", options=available_years)

    # 선택된 연도의 데이터 필터링
    year_filtered_data = filtered_data[filtered_data['YEAR'] == selected_year]

    # 불량 유형별 빈도수 계산
    type_counts = year_filtered_data['TYPE_GBN_U_NM'].value_counts().reset_index()
    type_counts.columns = ['TYPE_GBN_U_NM', '빈도수']

    # 연도에 따라 불량 유형 및 빈도수 표시 (클릭 가능)
    st.sidebar.write("### 불량 유형별 빈도수")
    if not type_counts.empty:
        selected_type = st.sidebar.radio(
            "불량 유형을 클릭하세요:",
            options=type_counts['TYPE_GBN_U_NM'].tolist(),
            index=0,
            format_func=lambda x: f"{x}: {type_counts[type_counts['TYPE_GBN_U_NM'] == x]['빈도수'].values[0]}회"
        )
    else:
        st.sidebar.write("선택한 연도에는 데이터가 없습니다.")
        selected_type = None

    # 선택된 불량 유형 데이터 필터링
    if selected_type:
        type_filtered_data = year_filtered_data[year_filtered_data['TYPE_GBN_U_NM'] == selected_type]

        # Treemap 시각화에 HTML 줄바꿈으로 TOP-5 조치 내용 추가
        st.header(f"불량 유형 및 발생 유형 빈도 Treemap ({selected_type})")

        def get_top_5_actions_html(descriptions):
            actions = [action.strip() for desc in descriptions for action in desc.split('\n') if action.strip()]
            action_counts = Counter(actions)
            top_5 = action_counts.most_common(5)
            if top_5:
                return "<br>".join([f"{i+1}. {action} ({count})" for i, (action, count) in enumerate(top_5)])
            return "조치 내용 없음"

        freq_df = (
            type_filtered_data.groupby(['TYPE_GBN_U_NM', 'TYPE_GBN_NM'])
            .agg(빈도수=('JOCHI_DESCR', 'size'), 조치내용=('JOCHI_DESCR', get_top_5_actions_html))
            .reset_index()
        )

        fig = px.treemap(
            freq_df,
            path=['TYPE_GBN_U_NM', 'TYPE_GBN_NM', '조치내용'],
            values='빈도수',
            color='빈도수',
            color_continuous_scale='RdBu',
            title=f'{selected_type}의 발생유형 및 조치내용 분석 (연도: {selected_year})'
        )

        # 글자 크기를 키우기 위해 textfont_size 속성 설정
        fig.update_traces(textinfo="label+text", hoverinfo="skip", textfont_size=14)

        # Treemap을 Streamlit에 표시
        st.plotly_chart(fig, use_container_width=True)
