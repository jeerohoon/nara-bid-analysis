import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import os


########################################################
# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'  # Mac OS용
# plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows용
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
########################################################

# 두 번째 셀 - 데이터 로드 및 전처리

# 문자열을 숫자로 변환하는 함수
def convert_to_numeric(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, str):
        x = x.replace(',', '').strip()
        if '%' in x:
            return float(x.replace('%', '')) / 100
    return pd.to_numeric(x, errors='coerce')

def load_and_preprocess_data():
    # 데이터 폴더 경로 설정
    data_folder = ''
    
    # 입찰정보 1~5 파일 읽기
    bid_files = [os.path.join(data_folder, f'입찰정보_{i}.xlsx') for i in range(1, 6)]
    bid_dfs = [pd.read_excel(file, header=1) for file in bid_files]
    
    # 입찰정보 병합
    merged_bid = pd.concat(bid_dfs, axis=0, ignore_index=True)
    merged_bid = merged_bid.drop_duplicates(subset=['공고번호'], keep='first')
    
    # 낙찰정보 1~5 파일 읽기
    award_files = [os.path.join(data_folder, f'낙찰정보_{i}.xlsx') for i in range(1, 6)]
    award_dfs = [pd.read_excel(file, header=1) for file in award_files]
    
    # 낙찰정보 병합
    merged_award = pd.concat(award_dfs, axis=0, ignore_index=True)
    merged_award = merged_award.drop_duplicates(subset=['공고번호'], keep='first')
    
    # 입찰정보와 낙찰정보 병합
    columns_to_use = [col for col in merged_award.columns if col not in merged_bid.columns or col == '공고번호']
    merged_data = pd.merge(
        merged_bid,
        merged_award[columns_to_use],
        on='공고번호',
        how='left'
    )
    
    # 숫자형으로 변환할 열 목록
    numeric_columns = ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가', '1순위사정률']
    
    # 숫자형 변환
    for col in numeric_columns:
        if col in merged_data.columns:
            merged_data[col] = merged_data[col].apply(convert_to_numeric)
            print(f"{col} 변환 후 유효한 데이터 수: {merged_data[col].notna().sum()}")
    
    # 필수 열의 결측치가 있는 행 삭제
    required_columns = ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가']
    merged_data = merged_data.dropna(subset=required_columns + ['1순위사정률'])
    
    # '번호' 열 삭제
    if '번호' in merged_data.columns:
        merged_data = merged_data.drop('번호', axis=1)
    
    return merged_data

# 데이터 로드 및 전처리 실행
processed_data = load_and_preprocess_data()

########################################################
# 웹에 데이터 프레임 표시
st.title('나라장터 투찰을 위한 사정률 구하기')

# 데이터 프레임 표시    
st.header("1. 2021년 01월 이후 나라장터 입찰 및 낙찰 정보", divider=True)

st.dataframe(processed_data, use_container_width=False)
# 데이터 정보 표시
st.caption(f"전체 {len(processed_data):,}개의 데이터가 포함되어 있습니다.")

########################################################
# 파일 업로드 섹션들을 나누어 배치
col1, col2 = st.columns(2)

with col1:
    st.subheader("새로운 입찰 데이터 업로드")
    bid_file = st.file_uploader("입찰 데이터 파일을 업로드하세요", type=['xlsx', 'xls'], key='bid_upload')
    
    if bid_file is not None:
        try:
            # 기존의 입찰 데이터 업로드 로직
            new_data = pd.read_excel(bid_file, header=1)
            existing_columns = processed_data.columns
            new_data = new_data[existing_columns.intersection(new_data.columns)]
            
            # # 데이터 확인을 위한 정보 출력
            # st.write("업로드된 파일의 열:", new_data.columns.tolist())
            
            required_columns = ['공고번호'] + ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가']
            missing_columns = set(required_columns) - set(new_data.columns)
            
            if missing_columns:
                st.error(f"필수 열이 누락되었습니다: {', '.join(missing_columns)}")
            else:
                # 업데이트 전 데이터 상태 확인
                before_count = len(processed_data)
                before_empty = processed_data['1순위사정률'].isna().sum()
                
                # 숫자형 데이터 변환
                numeric_columns = ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가']
                for col in numeric_columns:
                    if col in new_data.columns:
                        new_data[col] = new_data[col].apply(convert_to_numeric)
                
                # 기존 데이터와 병합 (중복 제거)
                processed_data = pd.concat([processed_data, new_data], axis=0)
                processed_data = processed_data.drop_duplicates(subset=['공고번호'], keep='first')
                
                # 업데이트 후 데이터 상태 확인
                after_count = len(processed_data)
                after_empty = processed_data['1순위사정률'].isna().sum()
                update_count = after_count - before_count
                
                st.success(f"""
                입찰 데이터가 성공적으로 업데이트되었습니다.
                - 추가된 새로운 행 수: {update_count}개
                - 업데이트 전 전체 행 수: {before_count}개
                - 업데이트 후 전체 행 수: {after_count}개
                - 업데이트 전 빈 값: {before_empty}개
                - 업데이트 후 빈 값: {after_empty}개
                """)
                
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
            st.write("오류 상세:", str(e))

with col2:
    st.subheader("새로운 낙찰 데이터 업로드")
    award_file = st.file_uploader("낙찰 데이터 파일을 업로드하세요", type=['xlsx', 'xls'], key='award_upload')
    
    if award_file is not None:
        try:
            # 새로운 낙찰 데이터 읽기 (header=1 설정)
            new_award_data = pd.read_excel(award_file, header=1)
            
            # # 데이터 확인을 위한 정보 출력
            # st.write("업로드된 파일의 열:", new_award_data.columns.tolist())
            
            # 필수 열 확인
            required_columns = ['공고번호', '1순위사정률']
            missing_columns = set(required_columns) - set(new_award_data.columns)
            
            if missing_columns:
                st.error(f"필수 열이 누락되었습니다: {', '.join(missing_columns)}")
            else:
                # 숫자형 데이터 변환
                if '1순위사정률' in new_award_data.columns:
                    new_award_data['1순위사정률'] = new_award_data['1순위사정률'].apply(convert_to_numeric)
                
                # 업데이트 전 데이터 상태 확인
                before_empty = processed_data['1순위사정률'].isna().sum()
                
                # 기존 데이터와 새로운 데이터의 공고번호 매칭
                update_count = 0
                for idx, row in new_award_data.iterrows():
                    mask = (processed_data['공고번호'] == row['공고번호']) & \
                          (pd.isna(processed_data['1순위사정률']))
                    
                    if mask.any():
                        # 빈 값만 업데이트
                        for col in new_award_data.columns:
                            if col in processed_data.columns and col != '공고번호':
                                processed_data.loc[mask, col] = row[col]
                        update_count += 1
                
                # 업데이트 후 데이터 상태 확인
                after_empty = processed_data['1순위사정률'].isna().sum()
                
                st.success(f"""
                낙찰 데이터가 성공적으로 업데이트되었습니다.
                - 업데이트된 행 수: {update_count}개
                - 업데이트 전 빈 값: {before_empty}개
                - 업데이트 후 빈 값: {after_empty}개
                """)
                
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
            st.write("오류 상세:", str(e))

########################################################
# 엑셀 다운로드 기능
st.text("\n=== 데이터 다운로드 ===")
# BytesIO를 사용하여 메모리에 엑셀 파일 생성
from io import BytesIO
import xlsxwriter

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        # 자동 열 너비 조정
        worksheet = writer.sheets['Sheet1']
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
    output.seek(0)
    return output

# 다운로드 버튼 생성
excel_file = to_excel(processed_data)
st.download_button(
    label="📥 업데이트된 데이터 엑셀 다운로드",
    data=excel_file,
    file_name='나라장터_입찰정보.xlsx',
    mime='application/vnd.ms-excel'
)

# 데이터 정보 표시
st.caption(f"전체 {len(processed_data):,}개의 데이터가 포함되어 있습니다.")

########################################################
st.header("2. 기초금액 구간별 1순위사정률 분포", divider=True)

# 기초금액 구간별 평균 사정률 계산
a_value_rates = processed_data.groupby(pd.qcut(processed_data['기초금액'], q=100))['1순위사정률'].agg(['mean', 'count']).reset_index()
a_value_rates.columns = ['기초금액_구간', '평균사정률', '건수']

# 기초금액 구간의 대표값 추출
a_value_rates['기초금액'] = a_value_rates['기초금액_구간'].apply(lambda x: x.mid)

# Seaborn 그래프 생성
fig, ax = plt.subplots(figsize=(15, 6))
sns.scatterplot(data=a_value_rates, 
                x='기초금액',
                y='평균사정률',
                size='건수',
                sizes=(20, 200),
                alpha=0.6)

# 그래프 스타일링
plt.title('기초금액 기준 평균 1순위사정률 분포')
plt.xlabel('기초금액 (원)')
plt.ylabel('평균 1순위사정률 (%)')

# x축 포맷 설정 (원 단위로 표시, 천 단위 구분 기호 추가)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

# Streamlit에 그래프 표시
st.pyplot(fig)

# 통계 정보 표시
st.subheader('기초금액 구간별 통계')
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("평균 기초금액", f"{format(int(processed_data['기초금액'].mean()), ',')}")
with col2:
    st.metric("최고 사정률", f"{a_value_rates['평균사정률'].max():.2f}%")
with col3:
    st.metric("최저 사정률", f"{a_value_rates['평균사정률'].min():.2f}%")

########################################################


# 세 번째 셀 - 예측 모델 클래스
class BidPricePredictor:
    def __init__(self, data):
        # 결측치가 없는 데이터만 선택
        required_columns = ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가', '1순위사정률']
        self.data = data.dropna(subset=required_columns).copy()
        self.model = None
        self.scaler = StandardScaler()
        
        st.text("=== 모델 초기화 ===")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("전체 데이터 수", f"{len(data):,}개")
        with col2:
            st.metric("학습 가능한 데이터 수", f"{len(self.data):,}개")
    
    def prepare_data(self):
        features = ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가']
        target = '1순위사정률'
        
        st.text("=== 데이터 전처리 과정 ===")
        st.metric("전처리 전 데이터 수", f"{len(self.data):,}개")
        
        # 타겟 변수를 0~1 범위로 변환
        if self.data[target].mean() > 1:
            self.data[target] = self.data[target] / 100
        
        # 이상치 제거 (0.9~1.1 범위를 벗어나는 값)
        clean_data = self.data[
            (self.data[target] > 0.9) & 
            (self.data[target] < 1.1)
        ]
        st.metric("이상치 제거 후 데이터 수", f"{len(clean_data):,}개")
        
        if len(clean_data) == 0:
            st.error("전처리 후 남은 데이터가 없습니다.")
            raise ValueError("전처리 후 남은 데이터가 없습니다.")
        
        X = clean_data[features]
        y = clean_data[target]
        
        # 특성 스케일링
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled, y
    
    def train_model(self):
        X_scaled, y = self.prepare_data()
        
        # 학습/테스트 데이터 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # 모델 학습
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # 성능 평가
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5)
        
        # 특성 중요도
        feature_importance = pd.DataFrame({
            'feature': ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가'],
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        st.text("=== 모델 성능 평가 ===")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("학습 데이터 R² 점수", f"{train_score:.4f}")
        with col2:
            st.metric("테스트 데이터 R² 점수", f"{test_score:.4f}")
        with col3:
            st.metric("교차 검증 R² 점수", f"{cv_scores.mean():.4f}")
        
        st.text("=== 특성 중요도 ===")
        # 특성 중요도를 막대 차트로 표시
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=feature_importance, x='importance', y='feature')
        plt.title('특성 중요도')
        st.pyplot(fig)
        
        return self.model
    
    def predict_rate(self, new_data):
        if self.model is None:
            st.error("모델이 학습되지 않았습니다. 먼저 train_model()을 실행하세요.")
            raise ValueError("모델이 학습되지 않았습니다.")
        
        # 특성 스케일링 적용
        scaled_data = self.scaler.transform(new_data)
        
        # 예측 수행
        predicted = self.model.predict(scaled_data)[0]
        
        # 예측값을 퍼센트로 변환하여 반환
        return predicted * 100

########################################################
########################################################
st.header("3. 사정률 예측 모델", divider=True)

# 모델 학습에 사용할 완전한 데이터 확인
complete_data = processed_data.dropna(subset=['기초금액', '추정가격', '투찰률', 'A값', '순공사원가', '1순위사정률'])
st.caption(f"학습에 사용 가능한 완전한 데이터: {len(complete_data):,}개")

# 머신러닝 학습 버튼
if st.button("🤖 머신러닝 모델 학습 시작", type="primary"):
    with st.spinner("머신러닝 모델 학습 중..."):
        try:
            # 예측 모델 학습
            predictor = BidPricePredictor(processed_data)
            model = predictor.train_model()
            
            # 학습된 모델을 세션 상태에 저장
            st.session_state['predictor'] = predictor
            st.session_state['model_trained'] = True
            
            st.success("모델 학습이 완료되었습니다! 이제 새로운 입찰건의 사정률을 예측할 수 있습니다.")
            
        except Exception as e:
            st.error(f"모델 학습 중 오류가 발생했습니다: {str(e)}")
            st.session_state['model_trained'] = False

# 예측 실행 (모델이 학습된 경우에만)
if st.session_state.get('model_trained', False):
    # 예측할 데이터 선택 (1순위사정률이 없는 데이터 중 다른 필수 컬럼은 있는 데이터)
    prediction_candidates = processed_data[pd.isna(processed_data['1순위사정률'])].copy()
    prediction_data = prediction_candidates.dropna(subset=['기초금액', '추정가격', '투찰률', 'A값', '순공사원가'])
    
    if len(prediction_data) > 0:
        st.subheader("새로운 입찰건 사정률 예측 결과")
        
        # 예측 실행
        features = ['기초금액', '추정가격', '투찰률', 'A값', '순공사원가']
        predictions = []
        
        predictor = st.session_state['predictor']
        for idx, row in prediction_data[features].iterrows():
            try:
                predicted_rate = predictor.predict_rate(row.values.reshape(1, -1))
                predictions.append(predicted_rate)
            except:
                predictions.append(np.nan)
        
        # 예측 결과를 데이터프레임에 추가
        prediction_data['1순위사정률(예측값)'] = predictions
        
        # 표시할 열 선택 및 정렬
        display_columns = [
            '공고번호',
            '공사명',
            '개찰일',
            '수요기관',
            '개찰일시',
            '기초금액',
            '추정가격',
            '투찰률',
            'A값',
            '순공사원가',
            '1순위사정률(예측값)'
        ]
        
        # 실제 표시할 열은 데이터프레임에 존재하는 열만 선택
        display_columns = [col for col in display_columns if col in prediction_data.columns]
        
        # 데이터프레임 표시
        st.dataframe(
            prediction_data[display_columns].style.format({
                '공고번호': '{}',  # 문자열 그대로 표시
                '공사명': '{}',  # 문자열 그대로 표시
                '개찰일': '{}',  # 날짜/시간 그대로 표시
                '수요기관': '{}', # 문자열 그대로 표시
                '기초금액': '{:,.0f}',
                '추정가격': '{:,.0f}',
                '투찰률': '{:.4f}',
                'A값': '{:.4f}',
                '순공사원가': '{:,.0f}',
                '1순위사정률(예측값)': '{:.4f}'
            }),
            use_container_width=True
        )
        
        # 예측 통계 정보
        valid_predictions = prediction_data['1순위사정률(예측값)'].dropna()
        if len(valid_predictions) > 0:
            st.text("\n=== 예측된 사정률 통계 ===")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("평균 사정률", f"{valid_predictions.mean():.4f}%")
            with col2:
                st.metric("최소 사정률", f"{valid_predictions.min():.4f}%")
            with col3:
                st.metric("최대 사정률", f"{valid_predictions.max():.4f}%")
        
        st.caption(f"예측된 입찰건 수: {len(valid_predictions):,}개")
    else:
        st.info("예측할 새로운 입찰건이 없습니다.")
else:
    st.info("먼저 머신러닝 모델 학습을 실행해주세요.")
