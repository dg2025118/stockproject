import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# ==============================
# 1. 웹페이지 기본 설정
# ==============================
st.set_page_config(
    page_title="한미 주식 수익률 비교",
    page_icon="📈",
    layout="wide"
)

st.title("📈 한국 · 미국 주식 수익률 비교 웹앱")

st.write("""
이 웹앱은 `yfinance`를 이용해서 한국과 미국 주요 주식의 주가를 가져오고,  
선택한 기간 동안의 **누적 수익률**을 비교해 주는 학습용 웹앱입니다.
""")

st.warning("이 웹앱은 학습용 예제이며, 투자 추천이 아닙니다.")

# ==============================
# 2. 주식 목록 만들기
# ==============================
# 왼쪽은 화면에 보이는 이름, 오른쪽은 yfinance에서 사용하는 티커입니다.
stock_list = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "현대차": "005380.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "LG에너지솔루션": "373220.KS",

    "애플": "AAPL",
    "마이크로소프트": "MSFT",
    "엔비디아": "NVDA",
    "테슬라": "TSLA",
    "아마존": "AMZN",
    "구글": "GOOGL",
    "메타": "META",

    "S&P500 ETF": "SPY",
    "나스닥100 ETF": "QQQ"
}

# 티커를 다시 이름으로 바꾸기 위한 딕셔너리
ticker_to_name = {ticker: name for name, ticker in stock_list.items()}

# ==============================
# 3. 사이드바 만들기
# ==============================
st.sidebar.header("⚙️ 분석 설정")

selected_names = st.sidebar.multiselect(
    "비교할 주식을 선택하세요",
    list(stock_list.keys()),
    default=["삼성전자", "애플", "엔비디아"]
)

start_date = st.sidebar.date_input(
    "시작일",
    value=date.today() - timedelta(days=365)
)

end_date = st.sidebar.date_input(
    "종료일",
    value=date.today()
)

st.sidebar.markdown("---")

custom_ticker = st.sidebar.text_input(
    "직접 티커 입력",
    placeholder="예: TSLA, 005930.KS, 086520.KQ"
)

st.sidebar.caption("""
한국 주식은 보통 뒤에 `.KS` 또는 `.KQ`를 붙입니다.  
예: 삼성전자 `005930.KS`, 에코프로 `086520.KQ`
""")

# ==============================
# 4. 선택한 주식을 티커로 바꾸기
# ==============================
tickers = []

for name in selected_names:
    tickers.append(stock_list[name])

if custom_ticker:
    tickers.append(custom_ticker.strip().upper())

# 중복 제거
tickers = list(set(tickers))

# ==============================
# 5. yfinance 데이터 가져오는 함수
# ==============================
@st.cache_data
def get_stock_data(ticker_list, start, end):
    """
    yfinance에서 주가 데이터를 가져오는 함수입니다.
    종가 Close만 사용합니다.
    """

    data = yf.download(
        ticker_list,
        start=start,
        end=end + timedelta(days=1),
        auto_adjust=True,
        progress=False
    )

    if data.empty:
        return pd.DataFrame()

    # 여러 종목을 가져온 경우
    if isinstance(data.columns, pd.MultiIndex):
        close_data = data["Close"]

    # 한 종목만 가져온 경우
    else:
        close_data = data[["Close"]]
        close_data.columns = ticker_list

    return close_data

# ==============================
# 6. 메인 화면 실행 부분
# ==============================
if len(tickers) == 0:
    st.info("왼쪽 사이드바에서 주식을 선택해 주세요.")

elif start_date >= end_date:
    st.error("시작일은 종료일보다 빨라야 합니다.")

else:
    st.subheader("선택한 티커")
    st.write(tickers)

    with st.spinner("주가 데이터를 가져오는 중입니다..."):
        price_data = get_stock_data(tickers, start_date, end_date)

    if price_data.empty:
        st.error("데이터를 가져오지 못했습니다. 티커나 날짜를 확인해 주세요.")

    else:
        # 날짜순 정렬
        price_data = price_data.sort_index()

        # 휴장일 차이로 생긴 빈칸 채우기
        price_data = price_data.ffill().bfill()

        # 컬럼명을 티커에서 회사 이름으로 바꾸기
        new_columns = {}

        for ticker in price_data.columns:
            if ticker in ticker_to_name:
                new_columns[ticker] = ticker_to_name[ticker]
            else:
                new_columns[ticker] = ticker

        price_data = price_data.rename(columns=new_columns)

        # ==============================
        # 7. 누적 수익률 계산
        # ==============================
        # 공식:
        # 누적 수익률 = (오늘 가격 / 첫날 가격 - 1) * 100
        return_data = (price_data / price_data.iloc[0] - 1) * 100

        # ==============================
        # 8. 차트 보여주기
        # ==============================
        tab1, tab2, tab3 = st.tabs(
            ["📈 누적 수익률", "💰 실제 종가", "📋 요약표"]
        )

        with tab1:
            st.subheader("📈 누적 수익률 비교")

            st.write("""
            시작일을 0%로 맞춘 뒤, 각 주식이 얼마나 오르거나 내렸는지 비교합니다.  
            통화가 다른 한국 주식과 미국 주식을 비교할 때 유용합니다.
            """)

            fig_return = px.line(
                return_data,
                x=return_data.index,
                y=return_data.columns,
                title="누적 수익률 비교",
                labels={
                    "value": "누적 수익률 (%)",
                    "index": "날짜",
                    "variable": "종목"
                }
            )

            st.plotly_chart(fig_return, use_container_width=True)

        with tab2:
            st.subheader("💰 실제 종가 차트")

            st.write("""
            실제 주가 흐름을 보여줍니다.  
            단, 한국 주식은 원화, 미국 주식은 달러이므로 직접 비교할 때는 주의해야 합니다.
            """)

            fig_price = px.line(
                price_data,
                x=price_data.index,
                y=price_data.columns,
                title="실제 종가 비교",
                labels={
                    "value": "종가",
                    "index": "날짜",
                    "variable": "종목"
                }
            )

            st.plotly_chart(fig_price, use_container_width=True)

        with tab3:
            st.subheader("📋 수익률 요약표")

            summary = []

            for stock_name in price_data.columns:
                first_price = price_data[stock_name].iloc[0]
                last_price = price_data[stock_name].iloc[-1]
                total_return = (last_price / first_price - 1) * 100

                summary.append({
                    "종목": stock_name,
                    "시작 가격": round(first_price, 2),
                    "마지막 가격": round(last_price, 2),
                    "누적 수익률(%)": round(total_return, 2)
                })

            summary_df = pd.DataFrame(summary)

            summary_df = summary_df.sort_values(
                by="누적 수익률(%)",
                ascending=False
            )

            st.dataframe(summary_df, use_container_width=True)

            # CSV 다운로드 버튼
            csv = summary_df.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                label="요약표 CSV 다운로드",
                data=csv,
                file_name="stock_summary.csv",
                mime="text/csv"
            )

        # ==============================
        # 9. 원본 데이터 확인
        # ==============================
        with st.expander("원본 주가 데이터 보기"):
            st.dataframe(price_data, use_container_width=True)

        with st.expander("초보자를 위한 코드 설명"):
            st.markdown("""
            ### 1. `yfinance`란?
            야후 파이낸스에서 주식 가격 데이터를 가져오는 파이썬 라이브러리입니다.

            ### 2. 한국 주식 티커는 왜 `.KS`가 붙을까?
            야후 파이낸스에서 한국 코스피 주식은 보통 `.KS`,  
            코스닥 주식은 `.KQ`를 붙여서 사용합니다.

            예시:

            - 삼성전자: `005930.KS`
            - SK하이닉스: `000660.KS`
            - 에코프로: `086520.KQ`

            ### 3. 누적 수익률이란?
            첫날 가격을 기준으로 현재 가격이 몇 퍼센트 올랐는지 계산한 값입니다.

            공식은 다음과 같습니다.

            ```python
            누적 수익률 = (현재 가격 / 첫날 가격 - 1) * 100
            ```

            예를 들어 첫날 가격이 10,000원이고 마지막 가격이 12,000원이면

            ```python
            (12000 / 10000 - 1) * 100 = 20
            ```

            즉, 수익률은 20%입니다.

            ### 4. 왜 실제 가격보다 수익률 비교가 중요할까?
            삼성전자는 원화로 거래되고, 애플은 달러로 거래됩니다.  
            그래서 가격 자체를 비교하면 정확한 비교가 어렵습니다.  
            하지만 수익률은 퍼센트이기 때문에 서로 비교하기 쉽습니다.
            """)
