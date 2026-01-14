"""
Streamlit Frontend for Binary Options Pricing Model.

Run with: streamlit run src/app.py
"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from pathlib import Path

# Import our modules
from models import BinaryOptionPricer, GreeksAnalyzer
from config import OUTPUT_DIR

# Page config
st.set_page_config(
    page_title="BTC 二元期權分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .risk-high { color: #e74c3c; font-weight: bold; }
    .risk-medium { color: #f39c12; font-weight: bold; }
    .risk-low { color: #27ae60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_pricer():
    """Cache the pricer instance."""
    return BinaryOptionPricer()


@st.cache_resource
def get_analyzer():
    """Cache the analyzer instance."""
    return GreeksAnalyzer()


def create_price_surface(pricer, strike, sigma, spot_range, time_range, steps=40):
    """Create 3D price surface using Plotly."""
    spots = np.linspace(spot_range[0], spot_range[1], steps)
    times = np.linspace(time_range[0], time_range[1], steps)

    S, T = np.meshgrid(spots, times)
    prices = np.zeros_like(S)

    for i in range(steps):
        for j in range(steps):
            prices[i, j] = pricer.binary_call_price(S[i, j], strike, T[i, j], sigma)

    fig = go.Figure(data=[go.Surface(
        x=spots,
        y=times,
        z=prices,
        colorscale='RdYlGn',
        colorbar=dict(title='價格')
    )])

    fig.update_layout(
        title=f'Up 期權價格曲面 (Strike: ${strike:,.0f})',
        scene=dict(
            xaxis_title='BTC 現價 ($)',
            yaxis_title='到期時間 (秒)',
            zaxis_title='期權價格',
        ),
        height=500
    )

    return fig


def create_greeks_surface(pricer, strike, sigma, spot_range, time_range, greek='delta', steps=40):
    """Create 3D Greeks surface using Plotly."""
    spots = np.linspace(spot_range[0], spot_range[1], steps)
    times = np.linspace(time_range[0], time_range[1], steps)

    S, T = np.meshgrid(spots, times)
    values = np.zeros_like(S)

    for i in range(steps):
        for j in range(steps):
            greeks = pricer.calculate_greeks(S[i, j], strike, T[i, j], sigma)
            if greek == 'delta':
                values[i, j] = greeks['delta']
            elif greek == 'gamma':
                values[i, j] = abs(greeks['gamma'])
            elif greek == 'theta':
                values[i, j] = greeks['theta'] * 60  # per minute
            elif greek == 'vega':
                values[i, j] = greeks['vega']

    colorscales = {
        'delta': 'Viridis',
        'gamma': 'Hot',
        'theta': 'RdBu',
        'vega': 'Plasma'
    }

    titles = {
        'delta': 'Delta 曲面',
        'gamma': 'Gamma 風險曲面 (峰值=危險)',
        'theta': 'Theta 衰減曲面 (每分鐘)',
        'vega': 'Vega 曲面'
    }

    fig = go.Figure(data=[go.Surface(
        x=spots,
        y=times,
        z=values,
        colorscale=colorscales[greek],
        colorbar=dict(title=greek.capitalize())
    )])

    fig.update_layout(
        title=titles[greek],
        scene=dict(
            xaxis_title='BTC 現價 ($)',
            yaxis_title='到期時間 (秒)',
            zaxis_title=greek.capitalize(),
        ),
        height=500
    )

    return fig


def create_zone_heatmap(pricer, strike, spot_range, time_range, steps=100):
    """Create zone classification heatmap."""
    spots = np.linspace(spot_range[0], spot_range[1], steps)
    times = np.linspace(time_range[0], time_range[1], steps)

    zones = np.zeros((steps, steps))

    zone_map = {
        'linear_decay': 0,
        'lock_in': 1,
        'transition': 1.5,
        'gamma_risk': 2
    }

    for i, t in enumerate(times):
        for j, s in enumerate(spots):
            zone, _ = pricer.classify_zone(t, s, strike)
            zones[i, j] = zone_map.get(zone, 1)

    fig = go.Figure(data=go.Heatmap(
        x=spots,
        y=times,
        z=zones,
        colorscale=[
            [0, '#27ae60'],      # Green - Linear Decay
            [0.5, '#f39c12'],    # Yellow - Lock-in/Transition
            [1, '#e74c3c']       # Red - Gamma Risk
        ],
        colorbar=dict(
            title='風險區域',
            tickvals=[0, 1, 2],
            ticktext=['安全', '過渡', '危險']
        )
    ))

    # Add strike line
    fig.add_vline(x=strike, line_dash="dash", line_color="white", line_width=2)

    fig.update_layout(
        title=f'市場區域分類 (Strike: ${strike:,.0f})',
        xaxis_title='BTC 現價 ($)',
        yaxis_title='到期時間 (秒)',
        height=400
    )

    return fig


def main():
    """Main Streamlit app."""

    # Sidebar
    st.sidebar.title("⚙️ 參數設定")

    # Parameters
    strike = st.sidebar.number_input(
        "行使價 (Strike)",
        min_value=50000,
        max_value=150000,
        value=95000,
        step=100
    )

    spot = st.sidebar.number_input(
        "BTC 現價 (Spot)",
        min_value=50000,
        max_value=150000,
        value=95000,
        step=100
    )

    ttl_minutes = st.sidebar.slider(
        "到期時間 (分鐘)",
        min_value=0.5,
        max_value=15.0,
        value=5.0,
        step=0.5
    )
    ttl_seconds = ttl_minutes * 60

    sigma = st.sidebar.slider(
        "波動率 (年化)",
        min_value=0.2,
        max_value=1.5,
        value=0.6,
        step=0.05,
        format="%.0f%%"
    )

    spot_range_pct = st.sidebar.slider(
        "價格範圍 (%)",
        min_value=0.1,
        max_value=2.0,
        value=0.5,
        step=0.1
    )

    # Calculate ranges
    spot_range = (strike * (1 - spot_range_pct/100), strike * (1 + spot_range_pct/100))
    time_range = (1, 900)

    # Get pricer
    pricer = get_pricer()
    analyzer = get_analyzer()

    # Main content
    st.title("📈 BTC 二元期權分析儀表板")
    st.markdown("**Polymarket 15 分鐘 BTC Up/Down 期權定價模型**")

    # Calculate current pricing
    result = pricer.price(spot, strike, ttl_seconds, sigma)
    risk = analyzer.risk_profile(spot, strike, ttl_seconds, sigma)

    # Top metrics row
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Up 期權價格",
            f"{result.up_price:.2%}",
            delta=None
        )

    with col2:
        st.metric(
            "Down 期權價格",
            f"{result.down_price:.2%}",
            delta=None
        )

    with col3:
        zone_colors = {
            'linear_decay': '🟢 安全',
            'lock_in': '🟡 鎖定',
            'gamma_risk': '🔴 危險',
            'transition': '🟠 過渡'
        }
        st.metric(
            "市場區域",
            zone_colors.get(result.zone, result.zone)
        )

    with col4:
        st.metric(
            "Gamma 風險分數",
            f"{risk['gamma_risk_score']:.0f}/100"
        )

    # Greeks row
    st.markdown("### Greeks 指標")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Delta", f"{result.delta:.6f}")
    with col2:
        st.metric("Gamma", f"{result.gamma:.8f}")
    with col3:
        st.metric("Theta (每秒)", f"{result.theta:.6f}")
    with col4:
        st.metric("Vega", f"{result.vega:.6f}")

    # Zone description
    st.info(f"📊 **{result.zone_description}**")

    # Recommendation
    if risk['gamma_risk_score'] > 70:
        st.error(f"⚠️ **建議**: {risk['recommendation']}")
    elif risk['gamma_risk_score'] > 30:
        st.warning(f"⚡ **建議**: {risk['recommendation']}")
    else:
        st.success(f"✅ **建議**: {risk['recommendation']}")

    # Tabs for different views
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📊 價格曲面", "📈 Greeks 曲面", "🗺️ 區域分類", "📋 歷史資料"])

    with tab1:
        st.markdown("### 期權價格 3D 曲面")
        fig_price = create_price_surface(pricer, strike, sigma, spot_range, time_range)
        st.plotly_chart(fig_price, use_container_width=True)

    with tab2:
        st.markdown("### Greeks 3D 曲面")

        greek_choice = st.selectbox(
            "選擇 Greek",
            ["delta", "gamma", "theta", "vega"],
            format_func=lambda x: {
                'delta': 'Delta (價格敏感度)',
                'gamma': 'Gamma (Delta 加速度)',
                'theta': 'Theta (時間衰減)',
                'vega': 'Vega (波動率敏感度)'
            }[x]
        )

        fig_greek = create_greeks_surface(pricer, strike, sigma, spot_range, time_range, greek_choice)
        st.plotly_chart(fig_greek, use_container_width=True)

    with tab3:
        st.markdown("### 市場區域分類熱力圖")
        st.markdown("""
        - 🟢 **綠色 (Linear Decay)**: 正常衰減，風險低
        - 🟡 **黃色 (Lock-in/Transition)**: 過渡區域，結果趨於確定
        - 🔴 **紅色 (Gamma Risk)**: 危險區域，價格可能劇烈波動
        """)

        fig_zone = create_zone_heatmap(pricer, strike, spot_range, time_range)
        st.plotly_chart(fig_zone, use_container_width=True)

    with tab4:
        st.markdown("### 歷史收集資料")

        # Find CSV files
        csv_files = list(OUTPUT_DIR.glob("btc_15min_*.csv"))

        if csv_files:
            selected_file = st.selectbox(
                "選擇資料檔案",
                csv_files,
                format_func=lambda x: x.name
            )

            if selected_file:
                df = pd.read_csv(selected_file)
                st.markdown(f"**資料筆數**: {len(df)}")

                # Show recent data
                st.dataframe(df.tail(100), use_container_width=True)

                # Price chart
                if 'btc_price' in df.columns:
                    st.markdown("### BTC 價格走勢")
                    fig_btc = go.Figure()
                    fig_btc.add_trace(go.Scatter(
                        y=df['btc_price'].tail(500),
                        mode='lines',
                        name='BTC Price'
                    ))
                    fig_btc.update_layout(
                        title='BTC/USDT 價格 (最近 500 筆)',
                        yaxis_title='價格 ($)',
                        height=300
                    )
                    st.plotly_chart(fig_btc, use_container_width=True)
        else:
            st.warning("尚無收集的資料檔案。請先啟動資料收集器。")
            st.code("python -m src.main collect", language="bash")

    # Footer
    st.markdown("---")
    st.markdown(
        "📖 [使用指南](docs/USER_GUIDE_zh-TW.md) | "
        "🔧 [GitHub](https://github.com/jambocoder159/Tool_premodel)"
    )


if __name__ == "__main__":
    main()
