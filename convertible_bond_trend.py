"""
可转债趋势识别系统 - Streamlit交互版
数据源：akshare
运行方法: streamlit run app.py
"""

import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')
import requests
from akshare.utils.tqdm import get_tqdm


# 页面配置
st.set_page_config(
    page_title="可转债趋势识别系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)




def _bond_zh_cov() -> pd.DataFrame:
    """
    东方财富网-数据中心-新股数据-可转债数据
    https://data.eastmoney.com/kzz/default.html
    :return: 可转债数据
    :rtype: pandas.DataFrame
    """
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "sortColumns": "PUBLIC_START_DATE",
        "sortTypes": "-1",
        "pageSize": "500",
        "pageNumber": "1",
        "reportName": "RPT_BOND_CB_LIST",
        "columns": "ALL",
        "quoteColumns": "f2~01~CONVERT_STOCK_CODE~CONVERT_STOCK_PRICE,"
        "f235~10~SECURITY_CODE~TRANSFER_PRICE,f236~10~SECURITY_CODE~TRANSFER_VALUE,"
        "f2~10~SECURITY_CODE~CURRENT_BOND_PRICE,f237~10~SECURITY_CODE~TRANSFER_PREMIUM_RATIO,"
        "f239~10~SECURITY_CODE~RESALE_TRIG_PRICE,f240~10~SECURITY_CODE~REDEEM_TRIG_PRICE,"
        "f23~01~CONVERT_STOCK_CODE~PBV_RATIO",
        "source": "WEB",
        "client": "WEB",
    }
    r = requests.get(url, params=params)
    data_json = r.json()
    total_page = data_json["result"]["pages"]
    big_df = pd.DataFrame()
    tqdm = get_tqdm()
    for page in tqdm(range(1, total_page + 1), leave=False):
        params.update({"pageNumber": page})
        r = requests.get(url, params=params)
        data_json = r.json()
        temp_df = pd.DataFrame(data_json["result"]["data"])
        big_df = pd.concat(objs=[big_df, temp_df], ignore_index=True)

    field_name_mapping = {
        "SECURITY_CODE": "债券代码",
        "SECUCODE": "full_code",
        "SECURITY_NAME_ABBR": "债券简称",
        "LISTING_DATE": "上市时间",
        "CONVERT_STOCK_CODE": "正股代码",
        "RATING": "信用评级",
        "ACTUAL_ISSUE_SCALE": "发行规模",
        "ISSUE_PRICE": "申购上限",
        "CORRECODE": "申购代码",
        "PUBLIC_START_DATE": "申购日期",
        "BOND_START_DATE": "中签号发布日",
        "SECURITY_START_DATE": "原股东配售-股权登记日",
        "SECURITY_SHORT_NAME": "正股简称",
        "FIRST_PER_PREPLACING": "原股东配售-每股配售额",
        "ONLINE_GENERAL_LWR": "中签率",
        "CONVERT_STOCK_PRICE": "正股价",
        "TRANSFER_PRICE": "转股价",
        "TRANSFER_VALUE": "转股价值",
        "CURRENT_BOND_PRICE": "债现价",
        "TRANSFER_PREMIUM_RATIO": "转股溢价率"
    }
    big_df.rename(columns=field_name_mapping, inplace=True)
    big_df = big_df[
        [
            "债券代码",
            "full_code",
            "债券简称",
            "申购日期",
            "申购代码",
            "申购上限",
            "正股代码",
            "正股简称",
            "正股价",
            "转股价",
            "转股价值",
            "债现价",
            "转股溢价率",
            "原股东配售-股权登记日",
            "原股东配售-每股配售额",
            "发行规模",
            "中签号发布日",
            "中签率",
            "上市时间",
            "信用评级",
        ]
    ]

    big_df["申购上限"] = pd.to_numeric(big_df["申购上限"], errors="coerce")
    big_df["正股价"] = pd.to_numeric(big_df["正股价"], errors="coerce")
    big_df["转股价"] = pd.to_numeric(big_df["转股价"], errors="coerce")
    big_df["转股价值"] = pd.to_numeric(big_df["转股价值"], errors="coerce")
    big_df["债现价"] = pd.to_numeric(big_df["债现价"], errors="coerce")
    big_df["转股溢价率"] = pd.to_numeric(big_df["转股溢价率"], errors="coerce")
    big_df["原股东配售-每股配售额"] = pd.to_numeric(
        big_df["原股东配售-每股配售额"], errors="coerce"
    )
    big_df["发行规模"] = pd.to_numeric(big_df["发行规模"], errors="coerce")
    big_df["中签率"] = pd.to_numeric(big_df["中签率"], errors="coerce")
    big_df["中签号发布日"] = pd.to_datetime(
        big_df["中签号发布日"], errors="coerce"
    ).dt.date
    big_df["上市时间"] = pd.to_datetime(big_df["上市时间"], errors="coerce").dt.date
    big_df["申购日期"] = pd.to_datetime(big_df["申购日期"], errors="coerce").dt.date
    big_df["原股东配售-股权登记日"] = pd.to_datetime(
        big_df["原股东配售-股权登记日"], errors="coerce"
    ).dt.date
    big_df["债现价"] = big_df["债现价"].fillna(100)
    return big_df


class ConvertibleBondAnalyzer:
    def __init__(self):
        self.today = datetime.now().strftime('%Y%m%d')
        
    @st.cache_data(ttl=3600*3)  # 缓存1小时
    def get_bond_list(_self):
        """获取可转债列表"""
        try:
            # ak.bond_zh_cov = bond_zh_cov
            bond_df = _bond_zh_cov()
            bond_df = bond_df[
                (bond_df['债现价'] > 100) & 
                (bond_df['债现价'] < 9999999)
            ]
            return bond_df[['债券代码', '债券简称', '债现价', '转股溢价率', 'full_code']]
        except Exception as e:
            st.error(f"获取可转债列表失败: {e}")
            return pd.DataFrame()
    

    @st.cache_data(ttl=3600*3)  # 缓存10分钟
    def get_bond_kline(_self, bond_code):
        """获取单只可转债K线数据"""
        try:
            df = ak.bond_zh_hs_cov_daily(symbol=bond_code)
            if df is None or len(df) < 30:
                return None
            
            df = df.sort_values('date').tail(120)  # 取最近120个交易日
            df['date'] = pd.to_datetime(df['date'])
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume']
            
            # 转换数据类型
            for col in ['open', 'close', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df.reset_index(drop=True)
        except Exception as e:
            return None
    
    def calculate_features(self, df):
        """计算技术特征"""
        if df is None or len(df) < 20:
            return None
        
        features = {}
        df = df.copy()
        
        # 去除空值
        df = df.dropna(subset=['close', 'high', 'low'])
        if len(df) < 20:
            return None
        
        # 1. 趋势连续性
        close_diff = df['close'].diff()
        features['up_days_5'] = (close_diff.tail(5) > 0).sum()
        features['up_days_10'] = (close_diff.tail(10) > 0).sum()
        features['up_ratio_5'] = features['up_days_5'] / 5
        features['up_ratio_10'] = features['up_days_10'] / 10
        
        # 2. 价格质量
        features['avg_change_5'] = close_diff.tail(5).mean()
        features['avg_change_10'] = close_diff.tail(10).mean()
        features['std_change_5'] = close_diff.tail(5).std()
        features['max_drop_5'] = close_diff.tail(5).min()
        
        # 3. 均线系统
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma30'] = df['close'].rolling(30).mean()
        
        current_price = df['close'].iloc[-1]
        features['price_ma5_ratio'] = (current_price / df['ma5'].iloc[-1] - 1) if pd.notna(df['ma5'].iloc[-1]) else 0
        features['price_ma10_ratio'] = (current_price / df['ma10'].iloc[-1] - 1) if pd.notna(df['ma10'].iloc[-1]) else 0
        
        ma5, ma10, ma20 = df['ma5'].iloc[-1], df['ma10'].iloc[-1], df['ma20'].iloc[-1]
        features['ma_bullish'] = 1 if (pd.notna(ma5) and pd.notna(ma10) and pd.notna(ma20) and ma5 > ma10 > ma20) else 0
        
        if len(df) >= 5:
            features['ma5_slope'] = (df['ma5'].iloc[-1] - df['ma5'].iloc[-5]) if pd.notna(df['ma5'].iloc[-5]) else 0
            features['ma10_slope'] = (df['ma10'].iloc[-1] - df['ma10'].iloc[-5]) if pd.notna(df['ma10'].iloc[-5]) else 0
        
        above_ma5 = (df['close'].tail(10) > df['ma5'].tail(10))
        features['days_above_ma5'] = above_ma5.sum()
        
        # 4. 低点抬高
        lows_5 = df['low'].tail(5).values
        features['low_raising'] = 1 if len(lows_5) >= 3 and lows_5[-1] > lows_5[0] else 0
        
        # 5. 量价配合
        volume_ma5 = df['volume'].tail(10).mean()
        current_volume = df['volume'].iloc[-1]
        features['volume_ratio'] = current_volume / volume_ma5 if volume_ma5 > 0 else 1
        
        price_changes = close_diff.tail(5)
        volume_changes = df['volume'].diff().tail(5)
        features['price_volume_corr'] = price_changes.corr(volume_changes) if len(price_changes) >= 2 else 0
        features['price_volume_corr'] = 0 if pd.isna(features['price_volume_corr']) else features['price_volume_corr']
        
        # 6. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs.iloc[-1])) if pd.notna(rs.iloc[-1]) and loss.iloc[-1] != 0 else 50
        
        # 7. MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        dif = ema12 - ema26
        features['macd_dif'] = dif.iloc[-1]
        features['macd_positive'] = 1 if dif.iloc[-1] > 0 else 0
        
        # 8. 累计涨幅
        features['return_1d'] = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) if len(df) >= 1 else 0
        features['return_5d'] = (df['close'].iloc[-1] / df['close'].iloc[-6] - 1) if len(df) >= 6 else 0
        features['return_10d'] = (df['close'].iloc[-1] / df['close'].iloc[-11] - 1) if len(df) >= 11 else 0
        features['return_20d'] = (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) if len(df) >= 21 else 0
        
        return features, df
    
    def calculate_trend_score(self, features):
        """计算趋势评分"""
        if features is None:
            return 0
        
        score = 0
        
        # 连续性得分（30分）
        if features['up_ratio_5'] >= 0.8:
            score += 15
        elif features['up_ratio_5'] >= 0.6:
            score += 10
        
        if features['up_ratio_10'] >= 0.7:
            score += 15
        elif features['up_ratio_10'] >= 0.6:
            score += 10
        
        # 均线系统得分（25分）
        if features['ma_bullish'] == 1:
            score += 10
        if features['price_ma5_ratio'] > 0 and features['price_ma5_ratio'] < 0.05:
            score += 8
        if features['days_above_ma5'] >= 7:
            score += 7
        
        # 上涨质量得分（20分）
        if 0.005 < features['avg_change_5'] < 0.03:
            score += 10
        if features['max_drop_5'] > -3:
            score += 10
        
        # 低点抬高得分（10分）
        if features['low_raising'] == 1:
            score += 10
        
        # 动量得分（15分）
        if 50 < features['rsi'] < 70:
            score += 8
        if features['macd_positive'] == 1:
            score += 7
        
        return score
    

    def plot_kline_with_signals(self, df, bond_name, features):
        """专业级同花顺风格K线图（兼容所有Plotly版本，无报错）"""
        # 数据预处理+空值保护
        df = df.reset_index(drop=True).copy()
        df = df.sort_values(by='date').reset_index(drop=True)
        if df.empty:
            fig = go.Figure()
            fig.update_layout(
                title_text=f"{bond_name} 暂无数据", 
                template='plotly_white',
                height=600
            )
            return fig
    
        # 生成支持布尔索引的x轴（核心修复）
        x_axis = np.arange(len(df))
        date_labels = df['date'].dt.strftime('%Y-%m-%d') if pd.api.types.is_datetime64_any_dtype(df['date']) else df['date'].astype(str)
    
        # ========== 兼容版配色方案 ==========
        up_color = '#E62E2E'          # 阳线主色
        up_border_color = '#C02020'   # 阳线边框
        down_color = '#00965E'        # 阴线主色
        ma_colors = {
            'ma5': '#FF9500',    # 5日均线
            'ma10': '#0066CC',   # 10日均线
            'ma20': '#9933FF',   # 20日均线
            'ma30': '#00CC66'    # 30日均线
        }
    
        # 创建子图（仅保留兼容参数）
        fig = make_subplots(
            rows=3, cols=1,
            vertical_spacing=0.015,
            row_heights=[0.7, 0.15, 0.15],
            subplot_titles=(f'{bond_name} K线图', '成交量', 'RSI')
        )
    
        # 优化子图标题（仅保留兼容样式）
        for i, title in enumerate([f'{bond_name} K线图', '成交量', 'RSI']):
            if i < len(fig.layout.annotations):
                fig.layout.annotations[i].update(
                    font=dict(size=16, family='Arial', color='#2C3E50', weight='bold'),
                    bgcolor='rgba(255,255,255,0.8)'
                )
        
        # ========== 核心：兼容版K线样式（移除所有新版参数） ==========
        up_mask = df['close'] >= df['open']
        down_mask = df['close'] < df['open']
    
        # 阳线：仅保留基础样式（旧版Plotly兼容）
        fig.add_trace(
            go.Candlestick(
                x=x_axis[up_mask],
                open=df.loc[up_mask, 'open'],
                high=df.loc[up_mask, 'high'],
                low=df.loc[up_mask, 'low'],
                close=df.loc[up_mask, 'close'],
                name='阳线',
                increasing_line_color=up_border_color,
                increasing_fillcolor='rgba(255,255,255,0)',  # 空心
                increasing_line_width=2,                     # 加粗边框
                showlegend=False,
                # 修复hover模板：不用%{x}，改用自定义数据
                customdata=np.array([date_labels.iloc[i] for i in np.where(up_mask)[0]]),
                hovertemplate='日期: %{customdata}<br>开盘: %{open}<br>最高: %{high}<br>最低: %{low}<br>收盘: %{close}<extra></extra>'
            ),
            row=1, col=1
        )
    
        # 阴线：仅保留基础样式（旧版Plotly兼容）
        fig.add_trace(
            go.Candlestick(
                x=x_axis[down_mask],
                open=df.loc[down_mask, 'open'],
                high=df.loc[down_mask, 'high'],
                low=df.loc[down_mask, 'low'],
                close=df.loc[down_mask, 'close'],
                name='阴线',
                decreasing_line_color=down_color,
                decreasing_fillcolor=down_color,             # 实心
                decreasing_line_width=1.8,
                showlegend=False,
                # 修复hover模板
                customdata=np.array([date_labels.iloc[i] for i in np.where(down_mask)[0]]),
                hovertemplate='日期: %{customdata}<br>开盘: %{open}<br>最高: %{high}<br>最低: %{low}<br>收盘: %{close}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # ========== 均线优化（移除平滑/渐变等新版参数） ==========
        for ma, color in ma_colors.items():
            if ma in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=x_axis,
                        y=df[ma],
                        name=ma.upper(),
                        line=dict(
                            color=color,
                            width=1.8
                        ),
                        opacity=0.85,
                        showlegend=True,
                        hovertemplate=f'{ma.upper()}: %{y}<extra></extra>'
                    ),
                    row=1, col=1
                )
        
        # ========== 成交量优化（仅保留兼容样式） ==========
        volume_colors = [up_color if row['close'] >= row['open'] else down_color 
                        for idx, row in df.iterrows()]
        
        fig.add_trace(
            go.Bar(
                x=x_axis,
                y=df['volume'],
                name='成交量',
                marker=dict(
                    color=volume_colors,
                    line=dict(width=0.5, color='#E0E0E0')
                ),
                opacity=0.8,
                showlegend=False,
                hovertemplate='成交量: %{y}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # ========== RSI优化（仅保留兼容参数） ==========
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        loss = loss.replace(0, 1e-8)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
    
        # RSI主线条（移除平滑参数）
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=rsi,
                name='RSI',
                line=dict(
                    color='#800080',
                    width=2
                ),
                fill='tonexty',
                fillcolor='rgba(128, 0, 128, 0.15)',
                showlegend=False,
                hovertemplate='RSI: %{y}<extra></extra>'
            ),
            row=3, col=1
        )
    
        # RSI阈值背景（兼容版）
        fig.add_hrect(
            y0=70, y1=100,
            fillcolor='rgba(230, 46, 46, 0.1)',
            line_width=0,
            opacity=0.6,
            row=3, col=1
        )
        fig.add_hrect(
            y0=0, y1=30,
            fillcolor='rgba(0, 150, 94, 0.1)',
            line_width=0,
            opacity=0.6,
            row=3, col=1
        )
    
        # RSI参考线
        fig.add_hline(y=70, line_dash="dash", line_color="#E62E2E", line_width=1.2, opacity=0.8, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00965E", line_width=1.2, opacity=0.8, row=3, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="#888888", line_width=1, opacity=0.6, row=3, col=1)
        
        # ========== 全局布局（仅保留兼容参数） ==========
        fig.update_layout(
            height=900,
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.01,
                xanchor='right',
                x=1,
                font=dict(size=11, family='Arial', weight='500'),
                bgcolor='rgba(255,255,255,0.95)',
                bordercolor='#E0E0E0',
                borderwidth=1
            ),
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='rgba(255,255,255,0.95)',
                bordercolor='#DDDDDD',
                font=dict(size=10, family='Arial')
            ),
            template='plotly_white',
            plot_bgcolor='rgba(248,249,250,1)',
            paper_bgcolor='white',
            margin=dict(l=60, r=30, t=70, b=40),
            font=dict(family='Arial', color='#2C3E50')
        )
    
        # ========== X/Y轴优化（兼容版） ==========
        tick_interval = max(len(x_axis)//15, 1) if len(x_axis) > 15 else 1
        for i in range(1, 4):
            fig.update_xaxes(
                ticks="outside",
                ticklen=6,
                tickwidth=1.2,
                tickvals=x_axis[::tick_interval],
                ticktext=[date_labels.iloc[idx] for idx in range(len(x_axis))[::tick_interval]],
                tickfont=dict(size=10, family='Arial', color='#666666'),
                gridcolor='rgba(220,220,220,0.3)',
                gridwidth=0.8,
                linecolor='#E0E0E0',
                linewidth=1,
                row=i, col=1
            )
        
        # Y轴设置
        fig.update_yaxes(
            title_text="价格",
            title_font=dict(size=12, family='Arial', color='#2C3E50', weight='bold'),
            tickfont=dict(size=10, family='Arial', color='#666666'),
            gridcolor='rgba(220,220,220,0.3)',
            gridwidth=0.8,
            linecolor='#E0E0E0',
            linewidth=1,
            ticks="outside",
            ticklen=6,
            tickwidth=1.2,
            row=1, col=1
        )
    
        fig.update_yaxes(
            title_text="成交量",
            title_font=dict(size=11, family='Arial', color='#2C3E50', weight='bold'),
            tickfont=dict(size=9, family='Arial', color='#666666'),
            gridcolor='rgba(220,220,220,0.2)',
            gridwidth=0.8,
            linecolor='#E0E0E0',
            linewidth=1,
            ticks="outside",
            ticklen=5,
            tickwidth=1,
            row=2, col=1
        )
    
        fig.update_yaxes(
            title_text="RSI (14)",
            title_font=dict(size=11, family='Arial', color='#2C3E50', weight='bold'),
            tickfont=dict(size=9, family='Arial', color='#666666'),
            gridcolor='rgba(220,220,220,0.2)',
            gridwidth=0.8,
            linecolor='#E0E0E0',
            linewidth=1,
            ticks="outside",
            ticklen=5,
            tickwidth=1,
            range=[0, 100],
            row=3, col=1
        )
        
        return fig

# 主应用
def main():
    st.markdown('<p class="main-header">📈 可转债趋势识别系统</p>', unsafe_allow_html=True)
    
    analyzer = ConvertibleBondAnalyzer()
    
    # 初始化session state
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = None
    if 'scan_params' not in st.session_state:
        st.session_state.scan_params = None
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 筛选条件")
        
        score_threshold = st.slider(
            "最低趋势评分",
            min_value=50,
            max_value=90,
            value=60,
            step=5,
            help="评分越高，趋势越强"
        )
        
        min_price = st.number_input("最低价格", value=130.0, step=1.0)
        max_price = st.number_input("最高价格", value=9000.0, step=1.0)
        max_premium = st.number_input("最高转股溢价率(%)", value=30.0, step=5.0)
        
        st.markdown("---")
        st.markdown("### 📊 评分标准")
        st.markdown("""
        - **连续性(30分)**: 连续上涨天数
        - **均线系统(25分)**: 多头排列
        - **上涨质量(20分)**: 涨幅适中
        - **低点抬高(10分)**: 底部抬升
        - **动量指标(15分)**: RSI/MACD
        """)
        
        scan_button = st.button("🔍 开始扫描", type="primary", use_container_width=True)
    
    # 主界面
    if scan_button:
        with st.spinner("正在获取可转债数据..."):
            bond_list = analyzer.get_bond_list()
            # bond_list = bond_list[bond_list['债券代码'].isin(['123263', '127071',"118045", "113657","113593"])]
            
            if len(bond_list) == 0:
                st.error("未获取到可转债数据，请稍后再试")
                return
        
        st.success(f"获取到 {len(bond_list)} 只可转债，开始分析...")
        
        # 进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        
        for idx, row in bond_list.iterrows():
            bond_code = row['full_code'].lower()
            bond_code = bond_code.split('.')[-1] + bond_code.split('.')[0]
            bond_name = row['债券简称']
            
            # 更新进度
            progress = min((idx + 1) / len(bond_list), 1.0)
            progress_bar.progress(progress)
            status_text.text(f"分析中: {bond_name} ({idx+1}/{len(bond_list)})")
            
            # 获取K线数据
            # print(bond_code)
            kline_df = analyzer.get_bond_kline(bond_code)
            # print(kline_df)
            if kline_df is None:
                continue
            
            # 计算特征
            result = analyzer.calculate_features(kline_df)
            if result is None:
                continue
            
            features, df_with_ma = result
            
            # 计算评分
            score = analyzer.calculate_trend_score(features)
            
            # 筛选
            if (score >= score_threshold and 
                min_price <= row['债现价'] <= max_price and
                row['转股溢价率'] <= max_premium):
                
                results.append({
                    '代码': bond_code,
                    '名称': bond_name,
                    '现价': row['债现价'],
                    '今日涨跌': f"{features['return_1d']*100:.2f}%",
                    '转股溢价率': f"{row['转股溢价率']:.2f}%",
                    '趋势评分': score,
                    '5日上涨天数': f"{features['up_days_5']}/5",
                    '10日上涨天数': f"{features['up_days_10']}/10",
                    '均线多头': '✓' if features['ma_bullish'] == 1 else '✗',
                    'RSI': f"{features['rsi']:.1f}",
                    '5日涨幅': f"{features['return_5d']*100:.2f}%",
                    '10日涨幅': f"{features['return_10d']*100:.2f}%",
                    '20日涨幅': f"{features['return_20d']*100:.2f}%",
                    'kline_df': df_with_ma,
                    'features': features
                })
        
        progress_bar.empty()
        status_text.empty()
        
        # 保存结果到session state
        st.session_state.scan_results = results
        st.session_state.scan_params = {
            'score_threshold': score_threshold,
            'min_price': min_price,
            'max_price': max_price,
            'max_premium': max_premium
        }
    
    # 从session state读取结果
    results = st.session_state.scan_results
    
    # 显示结果
    if results is not None and len(results) > 0:
        st.success(f"✅ 发现 {len(results)} 只符合条件的可转债")
        
        # 转换为DataFrame
        result_df = pd.DataFrame([{k: v for k, v in r.items() if k not in ['kline_df', 'features']} 
                                 for r in results])
        result_df = result_df.sort_values('趋势评分', ascending=False)
        
        # 显示表格
        st.dataframe(
            result_df,
            use_container_width=True,
            height=400,
            hide_index=True,
            key='results_table'
        )
        
        # 下载按钮
        csv = result_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下载CSV文件",
            data=csv,
            file_name=f"convertible_bonds_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key='download_csv'
        )
        
        st.markdown("---")
        st.subheader("📊 详细K线图")
        
        # 选择查看的可转债
        bond_options = [f"{r['名称']}({r['代码']}) - 评分:{r['趋势评分']}" for r in results]
        
        # 使用session state保存选中的索引，避免重新渲染时重置
        if 'selected_bond_index' not in st.session_state:
            st.session_state.selected_bond_index = 0
        
        selected_bond = st.selectbox(
            "选择要查看K线图的可转债",
            options=bond_options,
            index=st.session_state.selected_bond_index,
            key='bond_selector'
        )
        
        # 更新选中的索引
        if selected_bond:
            st.session_state.selected_bond_index = bond_options.index(selected_bond)
            # 找到对应的数据 - 通过索引匹配
            selected_index = bond_options.index(selected_bond)
            r = results[selected_index]
            
            # 显示详细信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("趋势评分", f"{r['趋势评分']}/100")
            with col2:
                st.metric("当前价格", r['现价'])
            with col3:
                st.metric("转股溢价率", r['转股溢价率'])
            with col4:
                st.metric("20日涨幅", r['20日涨幅'])
            
            # 绘制K线图
            fig = analyzer.plot_kline_with_signals(
                r['kline_df'],
                r['名称'],
                r['features']
            )
            st.plotly_chart(fig, use_container_width=True, key='kline_chart')
            
            # 技术指标详情
            with st.expander("📈 技术指标详情"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**趋势指标**")
                    st.write(f"- 5日上涨天数: {r['features']['up_days_5']}/5")
                    st.write(f"- 10日上涨天数: {r['features']['up_days_10']}/10")
                    st.write(f"- 5日平均涨幅: {r['features']['avg_change_5']:.2f}")
                    st.write(f"- 最大回撤: {r['features']['max_drop_5']:.2f}")
                    st.write(f"- 站稳5日线天数: {r['features']['days_above_ma5']}/10")
                
                with col2:
                    st.write("**技术指标**")
                    st.write(f"- RSI: {r['features']['rsi']:.2f}")
                    st.write(f"- MACD DIF: {r['features']['macd_dif']:.2f}")
                    st.write(f"- 均线多头: {'是' if r['features']['ma_bullish'] else '否'}")
                    st.write(f"- 量比: {r['features']['volume_ratio']:.2f}")
                    st.write(f"- 低点抬高: {'是' if r['features']['low_raising'] else '否'}")
    elif results is not None and len(results) == 0:
        st.warning("未发现符合条件的可转债，请调整筛选条件")
    
    else:
        st.info('👈 请在左侧设置筛选条件，然后点击"开始扫描"按钮')
        
        st.markdown("---")
        st.markdown("### 📖 使用说明")
        st.markdown("""
        1. **设置筛选条件**: 在左侧调整评分阈值、价格区间等
        2. **开始扫描**: 点击"开始扫描"按钮，系统会自动分析所有可转债
        3. **查看结果**: 在表格中查看符合条件的可转债列表
        4. **查看K线图**: 选择感兴趣的可转债，查看详细的K线图和技术指标
        5. **下载数据**: 点击"下载CSV文件"保存结果
        
        #### ⚠️ 风险提示
        - 本系统仅供参考，不构成投资建议
        - 请结合基本面和市场环境综合判断
        - 投资有风险，入市需谨慎
        """)


if __name__ == "__main__":
    main()
