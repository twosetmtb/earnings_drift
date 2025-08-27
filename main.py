import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set page config
st.set_page_config(page_title="Post-Earnings Drift Analyzer", layout="wide")

# Title and description
st.title("📈 Post-Earnings Drift Analyzer")
st.markdown("""
Enter a stock ticker to analyze if the post-earnings overnight gap correlates with the intraday price movement.
This app checks historical earnings data to identify potential drift patterns. **Note**: For educational purposes only, not financial advice.
""")

# Input ticker
ticker_input = st.text_input("Enter Stock Ticker (e.g., MSFT, NVDA, AAPL)", value="MSFT").upper()

# Button to trigger analysis
if st.button("Analyze"):
    with st.spinner("Fetching and analyzing data..."):
        try:
            # Fetch stock data
            stock = yf.Ticker(ticker_input)

            # Get earnings dates
            earnings = stock.earnings_dates
            if earnings is None or earnings.empty:
                st.error(f"No earnings data available for {ticker_input}. Please check the ticker or try again later.")
                st.stop()

            # Filter for past earnings with reported EPS
            earnings = earnings[earnings['Reported EPS'].notna()]
            if earnings.empty:
                st.error(f"No past earnings with reported EPS for {ticker_input}.")
                st.stop()

            # Get historical daily OHLC data (10 years)
            hist = stock.history(period="10y")
            if hist.empty:
                st.error(f"No historical price data available for {ticker_input}.")
                st.stop()

            # Ensure indices are timezone-naive
            earnings.index = earnings.index.tz_localize(None)
            hist.index = hist.index.tz_localize(None)

            # Lists to store data
            data = []

            # For each earnings date
            for ed in earnings.index:
                try:
                    # Find closest trading day on or before earnings date
                    prior_dates = hist.index[hist.index <= ed]
                    if prior_dates.empty:
                        continue
                    pre_date = prior_dates[-1]
                    pre_close = hist.loc[pre_date]['Close']

                    # Find next trading day after earnings date
                    next_dates = hist.index[hist.index > ed]
                    if next_dates.empty:
                        continue
                    next_date = next_dates[0]
                    post_open = hist.loc[next_date]['Open']
                    post_close = hist.loc[next_date]['Close']

                    # Calculate overnight gap %
                    gap_pct = ((post_open - pre_close) / pre_close) * 100

                    # Calculate intraday movement %
                    intraday_pct = ((post_close - post_open) / post_open) * 100

                    data.append({
                        'Earnings Date': ed.date(),
                        'Pre-Earnings Date': pre_date.date(),
                        'Post-Earnings Date': next_date.date(),
                        'Gap %': round(gap_pct, 2),
                        'Intraday %': round(intraday_pct, 2)
                    })
                except Exception as e:
                    continue

            # Create DataFrame
            df = pd.DataFrame(data)

            if df.empty:
                st.error(f"No sufficient data to analyze post-earnings drift for {ticker_input}. Possible reasons:\n"
                         "- Earnings dates do not align with trading days.\n"
                         "- Insufficient price data around earnings.\n"
                         "- Try a different ticker or check data on Yahoo Finance.")
                st.stop()

            # Compute correlation and same-direction percentage
            correlation = df['Gap %'].corr(df['Intraday %'])
            non_zero_df = df[df['Gap %'] != 0]
            same_direction_pct = (np.sign(non_zero_df['Gap %']) == np.sign(
                non_zero_df['Intraday %'])).mean() * 100 if not non_zero_df.empty else 0

            # Display results
            st.subheader(f"Results for {ticker_input}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Correlation (Gap % vs Intraday %)", f"{correlation:.2f}")
            with col2:
                st.metric("Same Direction %", f"{same_direction_pct:.2f}%")

            # Interpretation
            st.subheader("Interpretation")
            if correlation > 0:
                st.success(
                    "Positive correlation detected, suggesting potential post-earnings drift in the same direction as the overnight gap.")
            else:
                st.warning("No positive correlation found.")

            # Trading strategy
            st.subheader("Trading Strategy")
            st.markdown("**Disclaimer**: This is for educational purposes only, not financial advice.")
            if correlation > 0 and same_direction_pct > 50:
                st.markdown("""
                - **If the overnight gap post-earnings is positive (>0%)**, consider buying at open and holding intraday, expecting positive drift.
                - **If negative**, consider shorting or avoiding.
                - **Risks**: Historical patterns may not predict future results. Use stop-losses and proper position sizing.
                - **Next Steps**: Backtest further or combine with other indicators.
                """)
            else:
                st.markdown("- No clear drift pattern detected. Consider other strategies for this stock.")

            # Display detailed data
            st.subheader("Detailed Data")
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"An error occurred: {e}. Please check the ticker or try again later.")