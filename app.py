import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# ==========================================
# 0. 網頁基本設定 & 精緻樣式
# ==========================================
st.set_page_config(
    page_title="股票助理 - 您的專屬台股資產管家", layout="wide", page_icon="📈"
)

st.markdown(
    """
    <style>
    .main { background-color: #FAFAFB; }
    h1, h2, h3 { color: #1E293B; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    .stButton>button { background-color: #0ea5e9; color: white; border-radius: 8px; border: none; }
    .stButton>button:hover { background-color: #0284c7; color: white; }

    .table-header {
        background-color: #F1F5F9;
        padding: 10px;
        border-radius: 4px;
        border: 1px solid #CBD5E1;
        font-weight: bold;
        color: #475569;
        margin-bottom: 8px;
    }
    .table-row {
        background-color: #FFFFFF;
        padding: 10px;
        border-radius: 4px;
        border: 1px solid #E2E8F0;
        margin-bottom: 4px;
    }

    .stButton > button[key^="del_"] {
        background-color: transparent !important;
        color: #64748B !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0px !important;
        font-size: 16px !important;
        cursor: pointer;
    }
    .stButton > button[key^="del_"]:hover {
        color: #EF4444 !important;
        background-color: transparent !important;
    }

    .news-link {
        display: inline-block;
        padding: 2px 8px;
        background-color: #e0f2fe;
        color: #0369a1 !important;
        border-radius: 4px;
        text-decoration: none;
        font-size: 13px;
        font-weight: bold;
    }
    .news-link:hover {
        background-color: #0284c7;
        color: white !important;
    }

    /* 財務指標看板專用樣式 */
    .metric-card-box {
        background-color: #F8FAFC;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #38BDF8;
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 股票助理")
st.caption("個人台股投資組合與多策略風險管理中心")

# ==========================================
# 1. 核心資料庫初始化與載入
# ==========================================
DB_FILE = "trade_history.csv"


def load_trades():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        if "策略標籤" not in df.columns:
            df["策略標籤"] = "#未分類"
        if "交易心得" not in df.columns:
            df["交易心得"] = ""
        if not df.empty:
            df["交易ID"] = range(1, len(df) + 1)
        return df
    return pd.DataFrame()


def save_all_trades(df):
    df.to_csv(DB_FILE, index=False, encoding="utf-8-sig")


df_trades = load_trades()

# ==========================================
# 2. 全域策略切換 (網頁最頂端)
# ==========================================
if not df_trades.empty:
    all_tags = ["✨ 顯示所有策略帳戶"] + sorted(df_trades["策略標籤"].dropna().unique().tolist())
    global_selected_tag = st.selectbox("🎯 【全域篩選】請選擇要檢視的獨立策略帳戶：", all_tags)

    # 全域資料過濾
    if global_selected_tag == "✨ 顯示所有策略帳戶":
        df_filtered_global = df_trades.copy()
    else:
        df_filtered_global = df_trades[df_trades["策略標籤"] == global_selected_tag]
else:
    global_selected_tag = "✨ 顯示所有策略帳戶"
    df_filtered_global = pd.DataFrame()

st.write("---")

# ==========================================
# 3. 建立網頁分頁
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📊 持股比例圓餅圖",
    "📝 交易記帳與流水帳",
    "🧮 換股計算機與壓力測試"
])

# ------------------------------------------
# 【分頁 1：持股比例圓餅圖】
# ------------------------------------------
with tab1:
    st.subheader(f"📊 策略檢視：{global_selected_tag}")

    if not df_filtered_global.empty:
        summary_data = []

        # 遍歷該策略下的所有個股代號
        for ticker in df_filtered_global["股票代號"].unique():
            df_ticker = df_filtered_global[df_filtered_global["股票代號"] == ticker]
            name = df_ticker["股票名稱"].iloc[0]

            buy_shares = df_ticker[df_ticker["交易類型"] == "買入 (Buy)"]["股數"].sum()
            sell_shares = df_ticker[df_ticker["交易類型"] == "賣出 (Sell)"]["股數"].sum()
            current_shares = buy_shares - sell_shares
            avg_cost = df_ticker[df_ticker["交易類型"] == "買入 (Buy)"]["成交單價"].mean()

            if current_shares > 0:
                summary_data.append({
                    "股票代號": ticker, "股票名稱": name,
                    "持股股數": current_shares, "備用現價": avg_cost
                })

        if summary_data:
            portfolio_df = pd.DataFrame(summary_data)
            stock_tickers = portfolio_df["股票代號"].tolist()


            def fetch_current_prices(tickers):
                prices = {}
                for ticker in tickers:
                    try:
                        stock = yf.Ticker(ticker)
                        todays_data = stock.history(period="1d")
                        prices[ticker] = round(todays_data["Close"].iloc[-1], 2) if not todays_data.empty else None
                    except:
                        prices[ticker] = None
                return prices


            with st.spinner("🔍 股票助理正在連網更新此策略目前的最新市價..."):
                current_prices = fetch_current_prices(stock_tickers)

            # 填入現價與計算市值
            portfolio_df["當前現價"] = portfolio_df["股票代號"].map(
                lambda tk: current_prices.get(tk) or portfolio_df[portfolio_df["股票代號"] == tk]["備用現價"].values[0])
            portfolio_df["目前市值"] = portfolio_df["持股股數"] * portfolio_df["當前現價"]
            total_wealth = portfolio_df["目前市值"].sum()

            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown(f"### 💰 該策略股票總市值: **${total_wealth:,.2f}**")

                disp_portfolio = portfolio_df.copy()
                disp_portfolio["新聞連結"] = disp_portfolio["股票代號"].apply(
                    lambda x: f"https://tw.stock.yahoo.com/q/h?s={x.split('.')[0]}")
                disp_portfolio["股票代號"] = disp_portfolio["股票代號"].apply(lambda x: x.split('.')[0])

                st.dataframe(
                    disp_portfolio[["股票代號", "股票名稱", "持股股數", "當前現價", "目前市值", "新聞連結"]],
                    use_container_width=True,
                    column_config={"新聞連結": st.column_config.LinkColumn("📰 財經快訊", display_text="點我查看新聞")}
                )
            with col2:
                fig = px.pie(portfolio_df, values="開設市值" if False else "目前市值", names="股票名稱", hole=0.4,
                             color_discrete_sequence=px.colors.sequential.Teal_r)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 該策略帳戶目前無任何庫存持股。")
    else:
        st.info("💡 請先到交易記帳分頁紀錄您的第一筆交易並建立策略標籤。")

# ------------------------------------------
# 【分頁 2：交易記帳、流水帳與日記】
# ------------------------------------------
with tab2:
    st.subheader("📥 新增交易紀錄")

    # 即時財務指標看板預查輸入
    pre_ticker = st.text_input("📍 請先輸入代號觸發即時財務面板 (例: 2330 / 2454 / 0050)", value="2330").strip()

    # ⚡ 財務指標看板功能 (僅保留本益比)
    if pre_ticker:
        clean_pre = pre_ticker.replace(".TW", "").replace(".TWO", "").strip()
        search_pre = f"{clean_pre}.TW"

        try:
            if not yf.Ticker(search_pre).fast_info.get('lastPrice'): search_pre = f"{clean_pre}.TWO"
        except:
            search_pre = f"{clean_pre}.TWO"

        try:
            with st.spinner("📊 正在為您同步加載該股關鍵財務數據..."):
                tk_obj = yf.Ticker(search_pre)
                pe_ratio = tk_obj.info.get("trailingPE")
                pe_str = f"{round(pe_ratio, 2)} 倍" if pe_ratio else "暫無數據"

                st.markdown(
                    f"""
                    <div class="metric-card-box">
                        <b>🔍 實時財報看板 ({search_pre})</b> | 
                        <span>價盈比 (本益比 PE): <span style='color:#0ea5e9;font-weight:bold;'>{pe_str}</span></span>
                    </div>
                    """, unsafe_allow_html=True
                )
        except:
            pass

    with st.form("trade_form", clear_on_submit=True):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_type = st.selectbox("交易類型", ["買入 (Buy)", "賣出 (Sell)"])
            t_ticker = st.text_input("股票代號 (確認送出代號)", value=pre_ticker).strip()
            t_shares = st.number_input("成交股數", min_value=1, value=1000, step=1)
            t_tag_input = st.text_input("🏷️ 策略標籤 (自行輸入)",
                                        value="#未分類" if global_selected_tag == "✨ 顯示所有策略帳戶" else global_selected_tag).strip()
        with col_t2:
            t_price = st.number_input("成交單價", min_value=0.0, value=100.0, step=0.1)
            t_datetime = st.datetime_input("交易日期與時間", datetime.now())
            t_notes = st.text_area("✍️ 交易日記 (買入原因/賣出動機/個股觀察)",
                                   placeholder="請記錄此筆交易的策略理由、心態觀察...")

        submit_button = st.form_submit_button(label="🚀 寫入交易紀錄與日記")

    if submit_button:
        if not t_ticker:
            st.error("❌ 請填寫股票代號！")
        else:
            clean_code = t_ticker.replace(".TW", "").replace(".TWO", "").strip()
            search_ticker = f"{clean_code}.TW"
            try:
                test_ob = yf.Ticker(f"{clean_code}.TW")
                if not test_ob.fast_info.get('lastPrice'): search_ticker = f"{clean_code}.TWO"
            except:
                search_ticker = f"{clean_code}.TWO"

            try:
                stock_info = yf.Ticker(search_ticker)
                t_name = stock_info.info.get("shortName") or stock_info.info.get("longName") or f"TW_{clean_code}"
            except:
                t_name = f"TW_{clean_code}"

            formatted_time = t_datetime.strftime("%Y-%m-%d %H:%M")
            raw_amount = t_shares * t_price

            fee = max(20, round(raw_amount * 0.001425))
            tax = round(raw_amount * (0.001 if "00" in search_ticker else 0.003)) if t_type == "賣出 (Sell)" else 0
            total_cash = -(raw_amount + fee) if t_type == "買入 (Buy)" else (raw_amount - fee - tax)

            new_trade = {
                "股票代號": search_ticker, "股票名稱": t_name, "交易類型": t_type,
                "股數": t_shares, "成交單價": t_price, "交易時間": formatted_time,
                "手續費": fee, "證交稅": tax, "總收付金額": total_cash,
                "策略標籤": t_tag_input, "交易心得": t_notes
            }
            df = load_trades()
            new_trade["交易ID"] = len(df) + 1
            pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True).to_csv(DB_FILE, index=False,
                                                                                 encoding="utf-8-sig")
            st.success(f"🎉 寫入成功！名稱：【{t_name}】")
            st.rerun()

    st.write("---")

    # 流水帳與已實現分析同步受全域策略篩選限制
    if not df_filtered_global.empty:
        st.subheader(f"📜 歷史交易流水帳 (經策略篩選)")

        # 🌟 【新功能加插處】股票明細歷史獨立搜尋篩選器 🌟
        search_keyword = st.text_input(
            "🔍 搜尋特定股票交易紀錄：",
            placeholder="請輸入欲查詢的股票代號或名稱 (例如: 2330 或 台積電，留空顯示全部)",
            key="table_search_input"
        ).strip()

        # 根據關鍵字進一步過濾 Pandas 資料
        if search_keyword:
            df_filtered_search = df_filtered_global[
                df_filtered_global["股票代號"].str.contains(search_keyword, case=False) |
                df_filtered_global["股票名稱"].str.contains(search_keyword, case=False)
                ]
            st.caption(f"💡 已為您找出共 {len(df_filtered_search)} 筆符合「{search_keyword}」的歷史明細")
        else:
            df_filtered_search = df_filtered_global.copy()

        df_display = df_filtered_search.sort_values(by="交易時間", ascending=False).head(50)

        if not df_display.empty:
            st.markdown('<div class="table-header">', unsafe_allow_html=True)
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6, h_col7, h_col8 = st.columns(
                [0.6, 1.8, 2.7, 1.1, 1.2, 1.3, 1.5, 0.8])
            h_col1.markdown("ID")
            h_col2.markdown("交易時間")
            h_col3.markdown("股票名稱 (標籤)")
            h_col4.markdown("類型")
            h_col5.markdown("<div style='text-align:right;'>股數</div>", unsafe_allow_html=True)
            h_col6.markdown("<div style='text-align:right;'>成交單價</div>", unsafe_allow_html=True)
            h_col7.markdown("<div style='text-align:right;'>總金額</div>", unsafe_allow_html=True)
            h_col8.markdown("<div style='text-align:center;'>操作</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            for _, row in df_display.iterrows():
                st.markdown('<div class="table-row">', unsafe_allow_html=True)
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([0.6, 1.8, 2.7, 1.1, 1.2, 1.3, 1.5, 0.8])
                col1.write(f"{row['交易ID']}")
                col2.write(f"{row['交易時間']}")

                pure_code = row['股票代號'].split('.')[0]
                yahoo_news_url = f"https://tw.stock.yahoo.com/q/h?s={pure_code}"
                col3.markdown(
                    f"**{row['股票名稱']}** ({row['策略標籤']}) <a href='{yahoo_news_url}' target='_blank' class='news-link'>📰 新聞</a>",
                    unsafe_allow_html=True)

                type_color = "#0284c7" if "買入" in row["交易類型"] else "#f43f5e"
                col4.markdown(f"<span style='color:{type_color}; font-weight:bold;'>{row['交易類型']}</span>",
                              unsafe_allow_html=True)
                col5.markdown(f"<div style='text-align:right;'>{row['股數']:,} 股</div>", unsafe_allow_html=True)
                col6.markdown(f"<div style='text-align:right;'>${row['成交單價']:,.2f}</div>", unsafe_allow_html=True)
                amt_color = "#10B981" if row["總收付金額"] < 0 else "#EF4444"
                col7.markdown(
                    f"<div style='text-align:right; color:{amt_color}; font-weight:bold;'>${row['總收付金額']:,.2f}</div>",
                    unsafe_allow_html=True)
                with col8:
                    if st.button("🗑️", key=f"del_{row['交易ID']}"):
                        updated_df = df_trades[df_trades["交易ID"] != row["交易ID"]]
                        save_all_trades(updated_df)
                        st.rerun()

                if pd.notna(row['交易心得']) and str(row['交易心得']).strip() != "":
                    st.markdown(
                        f"<div style='padding-left:35px; color:#64748B; font-size:13px;'>📝 <b>交易日記：</b> {row['交易心得']}</div>",
                        unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("🔍 找不到符合此搜尋關鍵字的交易紀錄。")

        st.write("---")
        st.subheader("📊 已實現交易對照分析 (持有天數與真實損益)")
        df_sells = df_filtered_global[df_filtered_global["交易類型"] == "賣出 (Sell)"]
        df_buys = df_filtered_global[df_filtered_global["交易類型"] == "買入 (Buy)"]

        if not df_sells.empty and not df_buys.empty:
            summary_reports = []
            for _, sell_item in df_sells.iterrows():
                past_buys = df_buys[(df_buys["股票代號"] == sell_item["股票代號"]) & (
                            pd.to_datetime(df_buys["交易時間"]) <= pd.to_datetime(sell_item["交易時間"]))]
                if not past_buys.empty:
                    buy_date = pd.to_datetime(past_buys["交易時間"].min())
                    sell_date = pd.to_datetime(sell_item["交易時間"])
                    holding_days = max(0, (sell_date - buy_date).days)
                    avg_buy_price = past_buys["成交單價"].mean()
                    estimated_buy_cost = (avg_buy_price * sell_item["股數"]) + past_buys["手續費"].iloc[0]
                    real_net_profit = sell_item["總收付金額"] - estimated_buy_cost
                    real_roi = (real_net_profit / estimated_buy_cost) * 100
                    summary_reports.append({
                        "股票": sell_item["股票名稱"], "代號": sell_item["股票代號"], "賣出時間": sell_item["交易時間"],
                        "持有天數": f"{holding_days} 天", "真實損益 (精準淨利)": real_net_profit, "真實報酬率": real_roi
                    })
            if summary_reports:
                rep_df = pd.DataFrame(summary_reports)
                rep_df["代號"] = rep_df["代號"].apply(lambda x: x.split('.')[0])
                st.dataframe(rep_df.style.format({"真實損益 (精準淨利)": "${:,.2f}", "真實報酬率": "{:.2f}%"}),
                             use_container_width=True)

        if st.button("🚨 清空所有歷史紀錄"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.rerun()
    else:
        st.info("目前尚無交易紀錄。")

# ------------------------------------------
# 【分頁 3：換股計算機與壓力測試】
# ------------------------------------------
with tab3:
    st.subheader("🧮 換股計算機與資產壓力測試")

    st.markdown("#### 🔄 換股計算機")
    col_c1, col_c2, col_c3 = st.columns(3)

    with col_c1:
        calc_a_ticker = st.text_input("想賣出的 A 股代號", placeholder="2303", key="calc_a").strip()
        calc_a_shares = st.number_input("預計賣出股數", min_value=1, value=1000, step=100)
    with col_c2:
        calc_b_ticker = st.text_input("想買進的 B 股代號", placeholder="2330", key="calc_b").strip()
    with col_c3:
        st.markdown("<br>", unsafe_allow_html=True)
        calc_trigger = st.button("⚖️ 開始精算換股比例")

    if calc_trigger:
        if not calc_a_ticker or not calc_b_ticker:
            st.error("❌ 請同時輸入 A 股與 B 股的代號才能進行換算！")
        else:
            clean_a = calc_a_ticker.replace(".TW", "").replace(".TWO", "").strip()
            clean_b = calc_b_ticker.replace(".TW", "").replace(".TWO", "").strip()

            tk_a = f"{clean_a}.TW"
            tk_b = f"{clean_b}.TW"

            with st.spinner("🔍 股票助理正在即時連網獲取雙邊最新市價..."):
                try:
                    st_a = yf.Ticker(tk_a)
                    if not st_a.fast_info.get('lastPrice'): tk_a = f"{clean_a}.TWO"
                    st_b = yf.Ticker(tk_b)
                    if not st_b.fast_info.get('lastPrice'): tk_b = f"{clean_b}.TWO"

                    price_a = yf.Ticker(tk_a).history(period="1d")["Close"].iloc[-1]
                    price_b = yf.Ticker(tk_b).history(period="1d")["Close"].iloc[-1]

                    total_sell_val = calc_a_shares * price_a
                    est_buy_shares = int(total_sell_val // price_b)
                    remain_cash = total_sell_val % price_b

                    st.success("📊 換股精算報告完成！")
                    st.markdown(
                        f"""
                        * 當前 **{clean_a}** 市價：`${price_a:,.2f}` | 當前 **{clean_b}** 市價：`${price_b:,.2f}`
                        * 預估賣出總價值：<b style='color:#EF4444;'>${total_sell_val:,.2f}</b>
                        * 在不額外掏出本金的情況下，您可以**全數換購**：<b style='color:#10B981; font-size:18px;'>{est_buy_shares:,} 股</b> 的 {clean_b}
                        * 換股後剩餘零錢現金：`${remain_cash:,.2f}`
                        """, unsafe_allow_html=True
                    )
                except Exception as ce:
                    st.error(f"❌ 價格獲取失敗，請確認代號是否正確。錯誤原因: {ce}")

    st.write("---")

    st.subheader("🚨 黑天鵝崩盤壓力測試模擬器")
    st.markdown("模擬市場極端系統性風險，評估當前篩選策略下持股在資產突發減損時的防禦力。")

    current_portfolio = []
    if not df_filtered_global.empty:
        for ticker in df_filtered_global["股票代號"].unique():
            df_ticker = df_filtered_global[df_filtered_global["股票代號"] == ticker]
            name = df_ticker["股票名稱"].iloc[0]
            buy_shares = df_ticker[df_ticker["交易類型"] == "買入 (Buy)"]["股數"].sum()
            sell_shares = df_ticker[df_ticker["交易類型"] == "賣出 (Sell)"]["股數"].sum()
            current_shares = buy_shares - sell_shares
            if current_shares > 0:
                avg_cost = df_ticker[df_ticker["交易類型"] == "買入 (Buy)"]["成交單價"].mean()
                current_portfolio.append({"代號": ticker, "名稱": name, "股數": current_shares, "備用現價": avg_cost})

    if current_portfolio:
        df_stress_base = pd.DataFrame(current_portfolio)

        with st.spinner("🔍 正在加載最新防守市價基準..."):
            for idx, row in df_stress_base.iterrows():
                try:
                    df_stress_base.loc[idx, "當前現價"] = yf.Ticker(row["代號"]).history(period="1d")["Close"].iloc[-1]
                except:
                    df_stress_base.loc[idx, "當前現價"] = row["備用現價"]

        df_stress_base["當前總市值"] = df_stress_base["股數"] * df_stress_base["當前現價"]
        total_market_val = df_stress_base["當前總市值"].sum()

        st.markdown("#### 🛠️ 設定黑天鵝慘劇劇本")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            drop_percent = st.slider("😱 模擬大盤/整體持股無差別暴跌幅度 (%)", min_value=5, max_value=50, value=20,
                                     step=5)
        with col_s2:
            heavy_stock_ticker = st.selectbox("🎯 挑選一檔核心權值股單獨加強外傷",
                                              ["無"] + df_stress_base["代號"].tolist())
            heavy_drop = st.slider("🔥 該權值股額外追加跌幅 (%)", min_value=0, max_value=60, value=30,
                                   step=5) if heavy_stock_ticker != "無" else 0

        if st.button("💥 執行黑天鵝壓力測試 (Launch Stress Test)"):
            st.write("---")
            st.markdown("### 🛑 壓力測試評估報告")

            df_crushed = df_stress_base.copy()
            total_vaporized = 0

            for idx, row in df_crushed.iterrows():
                current_drop = drop_percent
                if heavy_stock_ticker != "無" and row["代號"] == heavy_stock_ticker:
                    current_drop = heavy_drop

                crushed_price = max(0.0, row["當前現價"] * (1 - current_drop / 100))
                crushed_value = row["股數"] * crushed_price
                vaporized = row["當前總市值"] - crushed_value
                total_vaporized += vaporized

                df_crushed.loc[idx, "模擬跌幅"] = f"-{current_drop}%"
                df_crushed.loc[idx, "預估崩盤後股價"] = round(crushed_price, 2)
                df_crushed.loc[idx, "資產蒸發金額"] = vaporized

            post_crisis_total = total_market_val - total_vaporized
            pct_lost = (total_vaporized / total_market_val) * 100 if total_market_val > 0 else 0

            st.markdown(
                f"""
                <div style='background-color:#EF444410; border: 2px dashed #EF4444; padding: 20px; border-radius: 8px; margin-bottom: 20px;'>
                    <h3 style='color:#EF4444; margin:0;'>☠️ 系統資產重創警告</h3>
                    <p style='margin: 10px 0 0 0; color:#1E293B; font-size:16px;'>
                        在目前篩選的策略中，您的股票總市值將由 <b>${total_market_val:,.2f}</b> 驟降至 <b style='color:#EF4444;'>${post_crisis_total:,.2f}</b>。<br>
                        您的財富將在瞬間 <b>蒸發了 ${total_vaporized:,.2f}</b> (該策略持股重挫了 <b>-{pct_lost:.2f}%</b>)！
                    </p>
                </div>
                """, unsafe_allow_html=True
            )

            st.markdown("#### 🔍 各檔個股損害明細")
            df_crushed["代號"] = df_crushed["代號"].apply(lambda x: x.split('.')[0])
            st.dataframe(
                df_crushed[
                    ["代號", "名稱", "股數", "當前現價", "模擬跌幅", "預估崩盤後股價", "資產蒸發金額"]].style.format({
                    "當前現價": "${:,.2f}", "預估崩盤後股價": "${:,.2f}", "資產蒸發金額": "${:,.2f}"
                }), use_container_width=True
            )
    else:
        st.info("💡 壓力測試模擬器需要您的當前策略帳戶內有實質持股庫存才能進行運算喔！")