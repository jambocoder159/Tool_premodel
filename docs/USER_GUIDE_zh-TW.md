# Tool_premodel 使用指南

> Polymarket 15 分鐘 BTC 二元期權定價模型與分析工具

## 目錄

1. [專案概述](#專案概述)
2. [安裝指南](#安裝指南)
3. [快速開始](#快速開始)
4. [資料收集模組](#資料收集模組)
5. [定價模型](#定價模型)
6. [Greeks 分析](#greeks-分析)
7. [3D 視覺化](#3d-視覺化)
8. [市場區域分類](#市場區域分類)
9. [完整範例](#完整範例)
10. [常見問題](#常見問題)

---

## 專案概述

本專案用於研究 Polymarket 的 15 分鐘加密貨幣預測市場，主要功能包括：

- **資料收集**：即時收集 Binance BTC 價格與 Polymarket 訂單簿資料
- **定價模型**：使用 Black-Scholes 框架計算二元期權理論價格
- **Greeks 分析**：計算 Delta、Gamma、Theta、Vega 敏感度指標
- **3D 視覺化**：生成價格曲面與 Greeks 曲面圖表

### 專案結構

```
Tool_premodel/
├── src/
│   ├── data/                 # 資料收集模組
│   │   ├── binance_client.py    # Binance WebSocket 客戶端
│   │   ├── polymarket_client.py # Polymarket API 客戶端
│   │   ├── collector.py         # 資料收集器
│   │   └── storage.py           # CSV 儲存
│   ├── models/               # 定價模型
│   │   ├── pricing.py           # 二元期權定價
│   │   └── greeks.py            # Greeks 分析器
│   ├── visualization/        # 視覺化模組
│   │   └── surfaces.py          # 3D 曲面圖表
│   ├── config.py             # 設定檔
│   └── main.py               # 主程式入口
├── output/                   # 輸出目錄（CSV、圖表）
├── tests/                    # 測試檔案
└── docs/                     # 文件
```

---

## 安裝指南

### 系統需求

- Python 3.10+
- pip 套件管理器

### 安裝步驟

```bash
# 1. 複製專案
git clone https://github.com/jambocoder159/Tool_premodel.git
cd Tool_premodel

# 2. 安裝依賴套件
pip install -r requirements.txt
```

### 依賴套件

| 套件 | 用途 |
|------|------|
| websockets | Binance WebSocket 連線 |
| aiohttp | Polymarket REST API |
| pandas | 資料處理 |
| numpy | 數值計算 |
| scipy | 統計函數（常態分佈） |
| matplotlib | 3D 視覺化 |

---

## 快速開始

### 測試 Binance 連線

```bash
python -m src.main test-binance
```

預期輸出：
```
Testing Binance WebSocket connection...
Connecting to Binance...
BTC/USDT: $95291.50 (qty: 0.000060)
Binance connection working!
```

### 搜尋 Polymarket 市場

```bash
# 列出 15 分鐘 BTC 市場
python -m src.main list

# 搜尋 Bitcoin 相關市場
python -m src.main search bitcoin
```

### 啟動資料收集

```bash
# 前景執行（Ctrl+C 停止）
python -m src.main collect

# 帶除錯訊息
python -m src.main collect --debug
```

### 背景執行（推薦）

```bash
# 啟動背景收集
nohup python -m src.main collect > output/collector.log 2>&1 &

# 查看進程 ID
ps aux | grep "src.main collect"

# 監控日誌
tail -f output/collector.log

# 停止收集（將 PID 替換為實際進程 ID）
kill <PID>
```

---

## 資料收集模組

### BinanceClient

即時串流 BTC/USDT 交易資料。

```python
import asyncio
from src.data import BinanceClient

async def main():
    client = BinanceClient()

    # 串流交易資料
    async for trade in client.stream_trades():
        print(f"價格: ${trade.price:.2f}, 數量: {trade.quantity}")

        # 收集 10 筆後停止
        if trade.trade_id % 10 == 0:
            break

    await client.disconnect()

asyncio.run(main())
```

### PolymarketClient

獲取 Polymarket 15 分鐘市場資料。

```python
import asyncio
from src.data import PolymarketClient

async def main():
    client = PolymarketClient()

    # 搜尋 BTC Up/Down 市場
    markets = await client.find_btc_updown_markets()

    for market in markets:
        print(f"市場: {market.question}")
        print(f"Up Token: {market.yes_token_id[:32]}...")
        print(f"到期: {market.end_date}")

    # 如果找到市場，獲取價格
    if markets:
        client.set_market(markets[0])
        prices = await client.get_current_prices()
        if prices:
            print(f"Up 價格: {prices.yes_price:.4f}")
            print(f"Down 價格: {prices.no_price:.4f}")

    await client.close()

asyncio.run(main())
```

### DataCollector

整合 Binance 和 Polymarket 資料。

```python
import asyncio
from src.data import DataCollector

async def main():
    collector = DataCollector()

    # 啟動收集（會自動搜尋市場）
    # 按 Ctrl+C 停止
    await collector.start()

asyncio.run(main())
```

### 資料格式

收集的資料儲存在 `output/btc_15min_*.csv`：

| 欄位 | 說明 |
|------|------|
| timestamp | ISO 格式時間戳 |
| btc_price | BTC/USDT 現貨價格 |
| yes_price | Up 期權中點價格 |
| no_price | Down 期權中點價格 |
| yes_bid / yes_ask | Up 期權買賣價 |
| no_bid / no_ask | Down 期權買賣價 |
| time_to_expiry_seconds | 距離到期秒數 |
| market_id | 市場 ID |

---

## 定價模型

### BinaryOptionPricer

使用 Black-Scholes 框架計算二元期權價格。

```python
from src.models import BinaryOptionPricer

# 建立定價器（預設波動率 60%）
pricer = BinaryOptionPricer(default_volatility=0.60)

# 計算完整定價結果
result = pricer.price(
    spot=95000,        # BTC 現價
    strike=95000,      # 行使價
    ttl_seconds=300,   # 5 分鐘到期
    sigma=0.60         # 年化波動率（可選）
)

print(f"Up 價格: {result.up_price:.4f} ({result.up_price*100:.2f}%)")
print(f"Down 價格: {result.down_price:.4f} ({result.down_price*100:.2f}%)")
print(f"Delta: {result.delta:.6f}")
print(f"Gamma: {result.gamma:.8f}")
print(f"Theta: {result.theta:.8f} (每秒)")
print(f"Vega: {result.vega:.6f}")
print(f"市場區域: {result.zone}")
print(f"描述: {result.zone_description}")
```

### 單獨計算價格

```python
# 計算 Up (Call) 價格
up_price = pricer.binary_call_price(
    S=95000,           # 現價
    K=95000,           # 行使價
    T_seconds=300,     # 到期秒數
    sigma=0.60         # 波動率
)

# 計算 Down (Put) 價格
down_price = pricer.binary_put_price(
    S=95000, K=95000, T_seconds=300, sigma=0.60
)
```

### 隱含波動率

從市場價格反推波動率。

```python
# 假設市場 Up 價格為 0.55
market_price = 0.55

iv = pricer.implied_volatility(
    market_price=market_price,
    S=95000,
    K=95000,
    T_seconds=300,
    is_call=True
)

if iv:
    print(f"隱含波動率: {iv:.2%}")
```

---

## Greeks 分析

### GreeksAnalyzer

進階 Greeks 分析與風險評估。

```python
from src.models import GreeksAnalyzer, BinaryOptionPricer

pricer = BinaryOptionPricer()
analyzer = GreeksAnalyzer(pricer)

# 完整 Greeks 快照
snapshot = analyzer.full_greeks(
    spot=95100,
    strike=95000,
    ttl_seconds=120,
    sigma=0.60
)

print(f"Up 價格: {snapshot.up_price:.4f}")
print(f"Down 價格: {snapshot.down_price:.4f}")
print(f"Delta (Up): {snapshot.delta_up:.6f}")
print(f"Delta (Down): {snapshot.delta_down:.6f}")
print(f"Gamma: {snapshot.gamma_up:.8f}")
```

### 風險分析

```python
# 風險概況
risk = analyzer.risk_profile(
    spot=95100,
    strike=95000,
    ttl_seconds=120,
    sigma=0.60
)

print(f"市場區域: {risk['zone']}")
print(f"價內/價外: {risk['moneyness']}")
print(f"距離行使價: {risk['distance_to_strike_pct']:.3f}%")
print(f"Gamma 風險分數: {risk['gamma_risk_score']:.1f}/100")
print(f"建議: {risk['recommendation']}")
```

### Delta 對沖計算

```python
# 計算對沖需求
hedge = analyzer.delta_hedge_ratio(
    position_size=100,     # 持有 100 份 Up 合約
    spot=95000,
    strike=95000,
    ttl_seconds=300,
    sigma=0.60
)

print(f"部位 Delta: {hedge['position_delta']:.4f}")
print(f"需對沖 BTC: {hedge['btc_to_hedge']:.6f}")
print(f"對沖價值: ${hedge['hedge_value_usd']:.2f}")
```

---

## 3D 視覺化

### SurfacePlotter

生成 3D 曲面圖表。

```python
from src.visualization import SurfacePlotter

# 建立繪圖器
plotter = SurfacePlotter(
    strike=95000,      # 行使價
    volatility=0.60    # 波動率
)

# 設定範圍（可選）
plotter.set_ranges(
    spot_pct=0.5,          # 價格範圍 ±0.5%
    time_max_seconds=900   # 時間範圍 0-15 分鐘
)

# 生成單一圖表
plotter.plot_price_surface(save=True, show=False)
plotter.plot_delta_surface(save=True, show=False)
plotter.plot_gamma_surface(save=True, show=False)
plotter.plot_theta_surface(save=True, show=False)

# 生成儀表板（四合一）
plotter.plot_dashboard(save=True, show=False)

# 生成區域熱力圖
plotter.plot_zone_heatmap(save=True, show=False)
```

### 一鍵生成所有圖表

```python
from src.visualization import generate_all_plots

# 生成所有圖表
results = generate_all_plots(
    strike=95000,
    volatility=0.60,
    spot_pct=0.5,
    show=False  # True 則互動顯示
)

for name, path in results.items():
    print(f"{name}: {path}")
```

### 圖表說明

| 圖表 | 說明 |
|------|------|
| price_surface | 期權價格隨現價和時間變化 |
| delta_surface | Delta 敏感度分布 |
| gamma_surface | Gamma 風險集中區（峰值=危險）|
| theta_surface | 時間衰減分布 |
| dashboard | 四合一儀表板 |
| zone_heatmap | 市場區域分類熱力圖 |

---

## 市場區域分類

本模型將市場狀態分為三個區域：

### 1. Linear Decay（線性衰減區）

- **條件**：距到期 > 3 分鐘
- **特徵**：Theta 主導，價格隨時間平穩衰減
- **風險**：低
- **顏色**：🟢 綠色

### 2. Lock-in（鎖定區）

- **條件**：距到期 1-3 分鐘，且價格遠離行使價
- **特徵**：價格變動極小，結果幾乎確定
- **風險**：低
- **顏色**：🟡 黃色

### 3. Gamma Risk（Gamma 風險區）

- **條件**：距到期 < 1 分鐘，且價格接近行使價
- **特徵**：極端敏感，價格可能劇烈波動
- **風險**：**極高**
- **顏色**：🔴 紅色

### 區域判斷程式碼

```python
from src.models import BinaryOptionPricer

pricer = BinaryOptionPricer()

zone, description = pricer.classify_zone(
    T_seconds=30,      # 距到期 30 秒
    S=95050,           # 現價
    K=95000            # 行使價
)

print(f"區域: {zone}")
print(f"描述: {description}")
```

---

## 完整範例

### 範例 1：即時定價監控

```python
import asyncio
from datetime import datetime
from src.data import BinanceClient
from src.models import BinaryOptionPricer

async def monitor_pricing():
    """即時監控 BTC 價格並計算期權價值"""

    client = BinanceClient()
    pricer = BinaryOptionPricer(default_volatility=0.60)

    strike = 95000  # 假設行使價
    ttl = 300       # 假設 5 分鐘到期

    print(f"監控中... 行使價: ${strike:,}, 到期: {ttl}秒")
    print("-" * 60)

    count = 0
    async for trade in client.stream_trades():
        result = pricer.price(
            spot=trade.price,
            strike=strike,
            ttl_seconds=ttl
        )

        print(
            f"[{datetime.now():%H:%M:%S}] "
            f"BTC: ${trade.price:,.2f} | "
            f"Up: {result.up_price:.2%} | "
            f"Down: {result.down_price:.2%} | "
            f"Delta: {result.delta:.4f} | "
            f"Zone: {result.zone}"
        )

        count += 1
        if count >= 10:  # 顯示 10 筆後停止
            break

        ttl -= 1  # 模擬時間流逝

    await client.disconnect()

asyncio.run(monitor_pricing())
```

### 範例 2：歷史資料分析

```python
import pandas as pd
from src.models import GreeksAnalyzer, analyze_historical_greeks

# 讀取收集的資料
df = pd.read_csv('output/btc_15min_btc_only_2026-01-14.csv')

# 假設行使價
strike = 95000

# 轉換為分析格式
data = df.to_dict('records')

# 分析 Greeks（需要有 time_to_expiry_seconds）
# 由於 BTC-only 模式沒有到期時間，這裡示範用固定值
for point in data[:10]:
    point['time_to_expiry_seconds'] = 300  # 假設 5 分鐘

results = analyze_historical_greeks(data[:10], strike=strike, sigma=0.60)

for r in results:
    print(
        f"時間: {r['timestamp'][:19]} | "
        f"BTC: ${r['btc_price']:,.2f} | "
        f"Up: {r['up_price']:.4f} | "
        f"Delta: {r['delta']:.6f}"
    )
```

### 範例 3：批量生成不同行使價的圖表

```python
from src.visualization import SurfacePlotter

strikes = [94000, 95000, 96000]

for strike in strikes:
    print(f"生成 Strike=${strike:,} 的圖表...")

    plotter = SurfacePlotter(strike=strike, volatility=0.60)
    plotter.plot_dashboard(save=True, show=False)

print("完成！")
```

---

## 常見問題

### Q1: 為什麼找不到 15 分鐘市場？

這些市場是定期出現的（大約每 15 分鐘開一個新的）。如果 `python -m src.main list` 沒有找到市場，請稍等幾分鐘再試。

### Q2: BTC-only 模式是什麼？

當沒有找到 Polymarket 15 分鐘市場時，收集器會進入 BTC-only 模式，只收集 Binance 的 BTC 價格資料。當市場出現時會自動切換。

### Q3: 如何調整波動率？

預設波動率為 60%（年化），可以在建立 Pricer 時調整：

```python
pricer = BinaryOptionPricer(default_volatility=0.80)  # 80%
```

### Q4: 圖表存在哪裡？

所有圖表存放在 `output/` 目錄，檔名格式為 `{類型}_{時間戳}.png`。

### Q5: 如何停止背景收集器？

```bash
# 找到進程 ID
ps aux | grep "src.main collect"

# 停止進程
kill <PID>
```

### Q6: 資料格式可以改成其他格式嗎？

目前只支援 CSV 格式。如需其他格式，可以使用 pandas 轉換：

```python
import pandas as pd

df = pd.read_csv('output/btc_15min_btc_only_2026-01-14.csv')
df.to_json('output/data.json')
df.to_parquet('output/data.parquet')
```

---

## 聯絡與貢獻

- GitHub: https://github.com/jambocoder159/Tool_premodel
- 問題回報: 請在 GitHub Issues 提交

---

*最後更新: 2026-01-14*
