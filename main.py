import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="한미 주식 수익률 비교 웹앱",
    page_icon="📈",
    layout="wide"
)

st.title("📈 한국 · 미국 주요 주식 수익률 비교 웹앱")
st.write(
    """
    이 웹앱은 `yfinance`를 이용해 한국과 미국 주요 주식의 주가 데이터를 가져오고,
    선택한 기간 동안의 **누적 수익률(%)**과 주가 차트를 비교합니다.
    
    서로 통화가 다른 한국 주식과 미국 주식도 수익률 기준으로 비교할 수 있습니다.
    """
)

st.info("이 앱은 학습용 예제이며, 투자 조언이 아닙니다.")

# =========================
# 종목 목록
# =========================
stock_dict = {
    # 한국 주요 주식
    "삼성전자 005930.KS": "005930.KS",
    "SK하이닉스 000660.KS": "000660.KS",
    "현대차 005380.KS": "005380.KS",
    "기아 000270.KS": "000270.KS",
    "NAVER 035420.KS": "035420.KS",
    "카카오 035720.KS": "035720.KS",
    "LG에너지솔루션 373220.KS": "373220.KS",
    "삼성바이오로직스 207940.KS": "207940.KS",
    "셀트리온 068270.KS": "068270.KS",
    "POSCO홀딩스 005490.KS": "005490.KS",

    # 미국 주요 주식
    "Apple AAPL": "AAPL",
    "Microsoft MSFT": "MSFT",
    "NVIDIA NVDA": "NVDA",
    "Tesla TSLA": "TSLA",
    "Amazon AMZN": "AMZN",
    "Alphabet GOOGL": "GOOGL",
    "Meta META": "META",
    "Netflix NFLX": "NFLX",
    "AMD AMD": "AMD",
    "Broadcom AVGO": "AVGO",

    # 참고용 ETF
    "S&P500 ETF SPY": "SPY",
    "Nasdaq100 ETF QQQ": "QQQ",
    "KODEX 200 069500.KS": "069500.KS",
}

ticker_to_name = {v: k for k, v in stock_dict.items()}

# =========================
# 사이드바 입력
# =========================
st.sidebar.header("⚙️ 분석 설정")

selected_stocks = st.sidebar.multiselect(
    "비교할 종목을 선택하세요",
    options=list(stock_dict.keys()),
    default=[
        "삼성전자 005930.KS",
        "SK하이닉스 000660.KS",
        "Apple AAPL",
        "NVIDIA NVDA",
    ]
)

custom_tickers_text = st.sidebar.text_input(
    "직접 티커 추가",
    placeholder="예: TSLA, 005930.KS, 086520.KQ"
)

period_option = st.sidebar.selectbox(
    "분석 기간 빠른 선택",
    ["사용자 지정", "1개월", "3개월", "6개월", "1년", "3년", "5년"],
    index=4
)

today = datetime.today().date()

if period_option == "1개월":
    default_start = today - timedelta(days=30)
elif period_option == "3개월":
    default_start = today - timedelta(days=90)
elif period_option == "6개월":
    default_start = today - timedelta(days=180)
elif period_option == "1년":
    default_start = today - timedelta(days=365)
elif period_option == "3년":
    default_start = today - timedelta(days=365 * 3)
elif period_option == "5년":
    default_start = today - timedelta(days=365 * 5)
else:
    default_start = today - timedelta(days=365)

col_start, col_end = st.sidebar.columns(2)

with col_start:
    start_date = st.date_input("시작일", value=default_start)

with col_end:
    end_date = st.date_input("종료일", value=today)

chart_type = st.sidebar.radio(
    "차트 종류",
    ["누적 수익률 차트", "정규화 가격 차트", "실제 종가 차트"],
    index=0
)

show_raw_data = st.sidebar.checkbox("원본 데이터 보기", value=False)

# =========================
# 티커 정리
# =========================
selected_tickers = [stock_dict[name] for name in selected_stocks]

custom_tickers = []
if custom_tickers_text.strip():
    custom_tickers = [
        ticker.strip().upper()
        for ticker in custom_tickers_text.split(",")
        if ticker.strip()
    ]

tickers = list(dict.fromkeys(selected_tickers + custom_tickers))

# =========================
# 데이터 다운로드 함수
# =========================
@st.cache_data(ttl=60 * 30)
def load_stock_data(tickers, start_date, end_date):
    """
    yfinance에서 주가 데이터를 가져온다.
    auto_adjust=True를 사용하면 배당, 액면분할 등이 반영된 수정 가격이 Close에 반영된다.
    """
    if not tickers:
        return pd.DataFrame()

    # yfinance의 end는 보통 종료일을 포함하지 않으므로 하루를 더해준다.
    yf_end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    data = yf.download(
        tickers=tickers,
        start=start_date,
        end=yf_end_date,
        auto_adjust=True,
        progress=False,
        threads=True
    )

    if data.empty:
        return pd.DataFrame()

    # 여러 종목일 때: MultiIndex 컬럼에서 Close만 추출
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close_data = data["Close"]
        else:
            return pd.DataFrame()
    else:
        # 단일 종목일 때
        if "Close" in data.columns:
            close_data = data[["Close"]]
            close_data.columns = tickers
        else:
            return pd.DataFrame()

    if isinstance(close_data, pd.Series):
        close_data = close_data.to_frame(name=tickers[0])

    close_data = close_data.dropna(how="all")

    return close_data


# =========================
# 분석 실행
# =========================
if start_date >= end_date:
    st.error("시작일은 종료일보다 앞서야 합니다.")
elif not tickers:
    st.warning("분석할 종목을 하나 이상 선택하거나 직접 입력해 주세요.")
else:
    with st.spinner("주가 데이터를 불러오는 중입니다..."):
        close_df = load_stock_data(tickers, start_date, end_date)

    if close_df.empty:
        st.error("데이터를 불러오지 못했습니다. 티커와 기간을 다시 확인해 주세요.")
    else:
        # 휴장일 차이 때문에 생기는 결측값 처리
        close_df = close_df.sort_index()
        close_df = close_df.ffill().bfill()

        # 완전히 결측인 컬럼 제거
        close_df = close_df.dropna(axis=1, how="all")

        if close_df.empty:
            st.error("유효한 가격 데이터가 없습니다.")
        else:
            # 누적 수익률 계산
            cumulative_return_df = (close_df / close_df.iloc[0] - 1) * 100

            # 정규화 가격 계산: 시작점을 100으로 맞춤
            normalized_price_df = close_df / close_df.iloc[0] * 100

            # 종목명 표시용 컬럼명 변경
            display_columns = {}
            for ticker in close_df.columns:
                display_columns[ticker] = ticker_to_name.get(ticker, ticker)

            close_display_df = close_df.rename(columns=display_columns)
            cumulative_display_df = cumulative_return_df.rename(columns=display_columns)
            normalized_display_df = normalized_price_df.rename(columns=display_columns)

            # =========================
            # 핵심 지표 카드
            # =========================
            st.subheader("📌 선택 종목")
            st.write(", ".join([display_columns.get(t, t) for t in close_df.columns]))

            summary_rows = []

            for ticker in close_df.columns:
                prices = close_df[ticker].dropna()
                returns = prices.pct_change().dropna()

                start_price = prices.iloc[0]
                end_price = prices.iloc[-1]
                total_return = (end_price / start_price - 1) * 100

                volatility = returns.std() * (252 ** 0.5) * 100 if len(returns) > 1 else 0

                cumulative = (prices / prices.iloc[0])
                running_max = cumulative.cummax()
                drawdown = (cumulative / running_max - 1) * 100
                max_drawdown = drawdown.min()

                summary_rows.append({
                    "종목": display_columns.get(ticker, ticker),
                    "티커": ticker,
                    "시작가": start_price,
                    "종가": end_price,
                    "누적 수익률(%)": total_return,
                    "연환산 변동성(%)": volatility,
                    "최대 낙폭 MDD(%)": max_drawdown,
                })

            summary_df = pd.DataFrame(summary_rows)
            summary_df = summary_df.sort_values(by="누적 수익률(%)", ascending=False)

            col1, col2, col3 = st.columns(3)

            best_stock = summary_df.iloc[0]
            worst_stock = summary_df.iloc[-1]
            average_return = summary_df["누적 수익률(%)"].mean()

            col1.metric(
                "수익률 1위",
                best_stock["종목"],
                f"{best_stock['누적 수익률(%)']:.2f}%"
            )

            col2.metric(
                "수익률 최하위",
                worst_stock["종목"],
                f"{worst_stock['누적 수익률(%)']:.2f}%"
            )

            col3.metric(
                "선택 종목 평균 수익률",
                f"{average_return:.2f}%"
            )

            # =========================
            # 차트
            # =========================
            st.subheader("📈 차트 비교")

            if chart_type == "누적 수익률 차트":
                chart_df = cumulative_display_df
                y_title = "누적 수익률 (%)"
                chart_title = "선택 기간 누적 수익률 비교"
            elif chart_type == "정규화 가격 차트":
                chart_df = normalized_display_df
                y_title = "정규화 가격, 시작일 = 100"
                chart_title = "정규화 가격 비교"
            else:
                chart_df = close_display_df
                y_title = "종가"
                chart_title = "실제 종가 비교"

            fig = go.Figure()

            for col in chart_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=chart_df.index,
                        y=chart_df[col],
                        mode="lines",
                        name=col
                    )
                )

            fig.update_layout(
                title=chart_title,
                xaxis_title="날짜",
                yaxis_title=y_title,
                hovermode="x unified",
                template="plotly_white",
                height=600,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            st.plotly_chart(fig, use_container_width=True)

            # =========================
            # 수익률 막대 그래프
            # =========================
            st.subheader("📊 종목별 누적 수익률 순위")

            bar_fig = go.Figure()

            bar_fig.add_trace(
                go.Bar(
                    x=summary_df["종목"],
                    y=summary_df["누적 수익률(%)"],
                    text=summary_df["누적 수익률(%)"].map(lambda x: f"{x:.2f}%"),
                    textposition="auto"
                )
            )

            bar_fig.update_layout(
                title="선택 종목 누적 수익률",
                xaxis_title="종목",
                yaxis_title="누적 수익률 (%)",
                template="plotly_white",
                height=450
            )

            st.plotly_chart(bar_fig, use_container_width=True)

            # =========================
            # 요약 테이블
            # =========================
            st.subheader("📋 분석 요약 테이블")

            formatted_summary_df = summary_df.copy()
            formatted_summary_df["시작가"] = formatted_summary_df["시작가"].map(lambda x: f"{x:,.2f}")
            formatted_summary_df["종가"] = formatted_summary_df["종가"].map(lambda x: f"{x:,.2f}")
            formatted_summary_df["누적 수익률(%)"] = formatted_summary_df["누적 수익률(%)"].map(lambda x: f"{x:.2f}%")
            formatted_summary_df["연환산 변동성(%)"] = formatted_summary_df["연환산 변동성(%)"].map(lambda x: f"{x:.2f}%")
            formatted_summary_df["최대 낙폭 MDD(%)"] = formatted_summary_df["최대 낙폭 MDD(%)"].map(lambda x: f"{x:.2f}%")

            st.dataframe(formatted_summary_df, use_container_width=True)

            # =========================
            # 원본 데이터
            # =========================
            if show_raw_data:
                st.subheader("🧾 원본 종가 데이터")
                st.dataframe(close_display_df, use_container_width=True)

            # =========================
            # CSV 다운로드
            # =========================
            st.subheader("💾 데이터 다운로드")

            csv_data = close_display_df.to_csv(index=True).encode("utf-8-sig")

            st.download_button(
                label="종가 데이터 CSV 다운로드",
                data=csv_data,
                file_name="stock_price_data.csv",
                mime="text/csv"
            )

            summary_csv = summary_df.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                label="분석 요약 CSV 다운로드",
                data=summary_csv,
                file_name="stock_summary.csv",
                mime="text/csv"
            )

            # =========================
            # 학습 포인트
            # =========================
            with st.expander("💡 코드 학습 포인트"):
                st.markdown(
                    """
                    ### 1. 왜 누적 수익률로 비교할까?
                    한국 주식은 원화, 미국 주식은 달러로 거래됩니다.  
                    가격 자체를 비교하면 통화 단위가 달라서 공정하지 않습니다.  
                    그래서 시작일을 기준으로 몇 % 상승 또는 하락했는지 보는 **누적 수익률**을 사용합니다.

                    ### 2. `ffill()`, `bfill()`은 왜 사용할까?
                    한국과 미국은 휴장일이 다릅니다.  
                    어떤 날은 한국 시장은 열리고 미국 시장은 쉬거나, 반대일 수 있습니다.  
                    이런 경우 생기는 빈 데이터를 앞뒤 값으로 채워 차트를 자연스럽게 연결합니다.

                    ### 3. MDD란?
                    MDD는 Maximum Drawdown의 약자로, 고점 대비 가장 크게 하락한 비율입니다.  
                    수익률뿐 아니라 위험도 함께 볼 때 사용합니다.
                    """
                )
