import akshare as ak
import pandas as pd
import numpy as np
import requests
import os
import random
import time
import warnings
from datetime import datetime, timedelta

# 屏蔽 Pandas 的 FutureWarning (保持日志清爽)
warnings.simplefilter(action='ignore', category=FutureWarning)

# ========================= 环境变量 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 1. 2026年·工程化建仓总表 (保持不变) =========================
PORTFOLIO_CFG = {
    # === 🧱 底仓层 (60%) ===
    "600900": {
        "name": "长江电力", "role": "🧱 永续现金", "type": "grid",
        "grids": [27.5, 26.5, 25.5], 
        "dps": 0.95, 
        "tip": "跌就是噪音"
    },
    "601088": {
        "name": "中国神华", "role": "🧱 能源底座", "type": "grid",
        "grids": [42.0, 40.0, 38.0],
        "dps": 2.62,
        "tip": "现金流不说谎"
    },
    "600941": {
        "name": "中国移动", "role": "🧱 现金奶牛", "type": "yield",
        "target_yield": 6.0, 
        "dps": 4.80, 
        "tip": "买的是现金"
    },
    
    # === ⚔️ 阿尔法层 (30%) ===
    "000568": {
        "name": "泸州老窖", "role": "⚔️ 均值回归", "type": "grid",
        "grids": [110.0, 105.0, 100.0], 
        "dps": 6.30,
        "tip": "贵的时候别碰"
    },
    "000333": {
        "name": "美的集团", "role": "⚔️ 全球制造", "type": "grid",
        "grids": [75.0, 72.0, 70.0], 
        "dps": 3.0,
        "tip": "必须等悲观"
    },
    "002415": {
        "name": "海康威视", "role": "⚔️ 进攻博弈", "type": "grid",
        "grids": [30.0, 28.0, 27.0], 
        "dps": 0.40,
        "tip": "逻辑破坏即撤"
    }
}

# ========================= 2. 晨爷配置 (升级版) =========================
CHENYE_CFG = {
    "MAX_PRICE": 15.0,           # 股价上限
    "MAX_CAP_BILLION": 50,       # 市值上限 (亿)
    "POSITION_THRESHOLD": 0.15,  # 天地战法位置 (15%分位)
    "MA_WINDOW": 250,            # 年线周期
    "MA_DISTANCE_MAX": 0.20,     # 距离年线最大偏离度
    "INCLUDE_ST": True,          # 是否包含ST (晨爷策略: 是)
    "BOOST_688": True,           # 是否给科创板加分 (晨爷策略: 是)
    "SCAN_LIMIT": 50             # [重要] 限制深度扫描数量，防止GitHub Action超时
}

QUOTES = [
    "“你不是在赌对错，而是在用规则，把人性的不稳定外包给系统。”",
    "“不追涨：不在表格区间内 = 什么都不做。”",
    "“只要水在流、电在卖，股价跌 = 噪音。”",
    "“只做两件事：把底仓建稳，把阿尔法仓买在明显错价。”",
    "“新增资金优先补底仓。”"
]

class FusionStrategy:
    def __init__(self):
        self.today = datetime.now()
        self.df_all = None      

    def get_market_data(self):
        try:
            print("📡 [1/3] 拉取全市场实时行情...")
            df = ak.stock_zh_a_spot_em()
            df = df.rename(columns={
                '代码': 'symbol', '名称': 'name', '最新价': 'price', 
                '总市值': 'market_cap', '市盈率-动态': 'pe_ttm', '涨跌幅': 'change'
            })
            df['symbol'] = df['symbol'].astype(str)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
            self.df_all = df
            return True
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            return False

    # === King Kong 逻辑 (保持不变) ===
    def analyze_kingkong(self):
        print("🛡️ [2/3] 执行2026建仓逻辑...")
        results = []
        codes = list(PORTFOLIO_CFG.keys())
        # 容错：防止部分代码没取到
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()
        
        for _, row in target_df.iterrows():
            code = row['symbol']
            cfg = PORTFOLIO_CFG.get(code)
            if not cfg: continue
            
            price = row['price']
            
            # 计算股息率
            current_yield = (cfg['dps'] / price * 100) if price > 0 else 0
            
            status_text = "等待"
            status_color = "#999"
            bg_color = "#fff"
            action_tip = f"现价 {price}"

            if cfg['type'] == 'grid':
                g1, g2, g3 = cfg['grids']
                if price > g1:
                    status_text = "⏸️ 观望"
                    status_color = "#95a5a6"
                    action_tip = f"目标 < {g1}"
                elif g2 < price <= g1:
                    status_text = "🟢 试探"
                    status_color = "#27ae60" 
                    bg_color = "#f0f9f4"
                    action_tip = f"区间 {g2}-{g1}"
                elif g3 < price <= g2:
                    status_text = "🟡 加仓"
                    status_color = "#f39c12" 
                    bg_color = "#fffaf0"
                    action_tip = f"区间 {g3}-{g2}"
                elif price <= g3:
                    status_text = "🔴 击球"
                    status_color = "#c0392b" 
                    bg_color = "#fff5f5"
                    action_tip = f"黄金坑 < {g3}"
                    
            elif cfg['type'] == 'yield':
                target_yield = cfg.get('target_yield', 6.0)
                if current_yield >= target_yield:
                    status_text = "🔴 达标"
                    status_color = "#c0392b"
                    bg_color = "#fff5f5"
                else:
                    status_text = "⏸️ 等待"
                    status_color = "#95a5a6"
                action_tip = f"目标股息 > {target_yield}%"

            results.append({
                "name": cfg['name'], "role": cfg['role'], "price": price,
                "yield": f"{current_yield:.2f}", 
                "status": status_text, "color": status_color, "bg": bg_color,
                "tip": cfg['tip'], "action_tip": action_tip
            })
        return results

    # === 晨爷逻辑 (深度融合版) ===
    def analyze_chenye(self):
        print("🏴‍☠️ [3/3] 扫描晨爷潜伏标的 (深度技术分析)...")
        results = []
        df = self.df_all.copy()
        
        # 1. 基础过滤 (Cap & Price)
        # 注意：这里先不剔除ST，因为晨爷策略可能包含ST
        df = df[
            (df['market_cap'] < CHENYE_CFG['MAX_CAP_BILLION'] * 100000000) & 
            (df['price'] < CHENYE_CFG['MAX_PRICE']) & 
            (df['price'] > 1.0) 
        ]
        
        # 2. 名称过滤
        def _is_bad_name(name):
            if not isinstance(name, str): return True
            # 必杀名单
            if any(k in name for k in ["退", "N", "C"]): return True
            # ST 策略开关
            if not CHENYE_CFG['INCLUDE_ST'] and ("ST" in name): return True
            return False
            
        df = df[~df['name'].apply(_is_bad_name)]
        
        # 3. 排序并截取 (防止 Github Action 超时)
        # 优先扫描市值最小的 Top N
        candidates = df.sort_values(by='market_cap').head(CHENYE_CFG['SCAN_LIMIT'])
        
        print(f"   - 初筛入围: {len(candidates)} 只，开始深度扫描...")

        count = 0
        for _, row in candidates.iterrows():
            count += 1
            if count % 10 == 0: print(f"   - 扫描进度: {count}/{len(candidates)}")
            
            # 这里的延时是为了礼貌，Github环境下如果并发低可以适当缩短
            time.sleep(0.2) 
            
            # 获取深度技术面评分
            tech_data = self._analyze_single_stock_depth(row['symbol'], row['price'])
            
            if tech_data:
                # 最终入选逻辑
                results.append({
                    "symbol": row['symbol'], 
                    "name": row['name'], 
                    "price": row['price'], 
                    "pos": tech_data['pos_rank'], # 用于显示位置百分比
                    "score": tech_data['score'],  # 用于排序
                    "status_tag": tech_data['status'],
                    "cap": round(row['market_cap'] / 100000000, 2)
                })
        
        # 按晨式评分降序排列，取前 10
        return sorted(results, key=lambda x: x['score'], reverse=True)[:10]

    def _analyze_single_stock_depth(self, code, current_price):
        """单只股票的深度技术分析 (核心融合部分)"""
        try:
            # 拉取历史K线 (最近4年足够计算月线位置)
            start_date = (self.today - timedelta(days=365 * 4)).strftime("%Y%m%d")
            end_date = self.today.strftime("%Y%m%d")
            
            # 失败重试一次
            try:
                df_hist = ak.stock_zh_a_hist(symbol=code, start_date=start_date, end_date=end_date, adjust="qfq")
            except:
                time.sleep(1)
                df_hist = ak.stock_zh_a_hist(symbol=code, start_date=start_date, end_date=end_date, adjust="qfq")

            if df_hist is None or len(df_hist) < CHENYE_CFG['MA_WINDOW']: 
                return None

            # 1. 天地战法 (月线位置)
            df_hist["日期"] = pd.to_datetime(df_hist["日期"])
            df_hist = df_hist.set_index("日期").sort_index()
            
            # 重采样为月线 (兼容新旧 Pandas)
            try:
                resampler = df_hist.resample("ME") # 新版
                df_month = pd.DataFrame({
                    "最高": resampler["最高"].max(),
                    "最低": resampler["最低"].min()
                }).dropna()
            except:
                resampler = df_hist.resample("M") # 旧版回退
                df_month = pd.DataFrame({
                    "最高": resampler["最高"].max(),
                    "最低": resampler["最低"].min()
                }).dropna()

            if len(df_month) < 12: return None

            hist_high = df_month["最高"].max()
            hist_low = df_month["最低"].min()
            
            if hist_high == hist_low: return None
            
            # 位置百分比 (0.15 = 15%)
            pos_rank = (current_price - hist_low) / (hist_high - hist_low)
            
            # ❌ 硬过滤：位置太高直接淘汰
            if pos_rank > CHENYE_CFG['POSITION_THRESHOLD']: 
                return None

            # 2. 年线逻辑
            ma250 = df_hist["收盘"].tail(CHENYE_CFG['MA_WINDOW']).mean()
            dist_to_ma250 = (current_price - ma250) / ma250
            
            # ❌ 硬过滤：离年线太远淘汰
            if dist_to_ma250 > CHENYE_CFG['MA_DISTANCE_MAX']:
                return None

            # 3. MACD 动能检查 (辅助加分项)
            macd_ok = self._check_macd(df_hist["收盘"])

            # 4. 晨式打分 (用于最终排序)
            score = 0
            # 位置分 (越低分越高, 权重50)
            score += (1 - (pos_rank / CHENYE_CFG['POSITION_THRESHOLD'])) * 50
            # 年线分 (越近分越高, 权重30)
            score += (1 - min(abs(dist_to_ma250)/0.2, 1)) * 30
            # MACD分 (权重10)
            if macd_ok: score += 10
            # 科创板加分 (权重10)
            if CHENYE_CFG['BOOST_688'] and code.startswith("688"): score += 10
            
            # 状态标签
            status = "潜伏"
            if -0.05 <= dist_to_ma250 <= 0.05: status = "年线关键"
            if macd_ok: status += "/金叉"

            return {
                "pos_rank": round(pos_rank * 100, 1),
                "score": round(score, 1),
                "status": status
            }

        except Exception as e:
            # print(f"Err {code}: {e}")
            return None

    def _check_macd(self, close_series):
        """MACD 简化判断: 绿柱衰竭 或 刚刚金叉"""
        if len(close_series) < 30: return False
        ema12 = close_series.ewm(span=12, adjust=False).mean()
        ema26 = close_series.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_hist = (dif - dea) * 2
        
        tail = macd_hist.dropna().iloc[-3:]
        if len(tail) < 3: return False
        v1, v2, v3 = tail.iloc[-3], tail.iloc[-2], tail.iloc[-1]
        
        # 绿柱缩小 OR 金叉
        cond_easing = (v1 < 0 and v2 < 0 and v3 < 0) and (abs(v3) < abs(v2))
        cond_cross = (v2 < 0) and (v3 > 0)
        return cond_easing or cond_cross

    def generate_report(self, kk_data, cy_data):
        quote = random.choice(QUOTES)
        date_str = self.today.strftime("%m-%d")
        week_day = ["周一","周二","周三","周四","周五","周六","周日"][self.today.weekday()]
        
        html = f"""
        <div style="font-family:'Helvetica Neue',sans-serif; max-width:600px; margin:0 auto; color:#333;">
            <div style="background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); color:white; padding:15px; border-radius:10px 10px 0 0;">
                <div style="font-size:18px; font-weight:bold;">🏗️ Mango投资日报</div>
                <div style="font-size:12px; opacity:0.8; margin-top:5px;">{date_str} {week_day} | 执行规则，做正确的事</div>
            </div>
            <div style="background:#fff; padding:15px; border:1px solid #eee; border-top:none;">
                <div style="background:#f8f9fa; padding:10px; border-radius:5px; font-size:13px; color:#555; margin-bottom:15px; border-left:4px solid #2c3e50;">
                    {quote}
                </div>
                
                <table style="width:100%; border-collapse:collapse; font-size:13px; margin-bottom:20px;">
                    <tr style="background:#f1f1f1; color:#666;">
                        <th style="padding:8px; text-align:left;">资产</th>
                        <th style="padding:8px; text-align:right;">执行信号</th>
                        <th style="padding:8px; text-align:center;">状态</th>
                    </tr>
        """
        
        for item in kk_data:
            row_style = f"background-color:{item['bg']}; border-bottom:1px solid #eee;"
            html += f"""
            <tr style="{row_style}">
                <td style="padding:8px; color:#2c3e50;">
                    <div style="font-weight:bold;">{item['name']}</div>
                    <div style="font-size:10px; color:#999;">{item['role']}</div>
                </td>
                <td style="padding:8px; text-align:right;">
                    <div style="font-family:monospace; font-size:13px; font-weight:bold; color:#333;">{item['action_tip']}</div>
                    <div style="font-size:10px; color:#aaa;">{item['tip']}</div>
                </td>
                <td style="padding:8px; text-align:center;">
                    <span style="background:{item['color']}; color:white; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:bold;">{item['status']}</span>
                </td>
            </tr>
            """
            
        html += """</table>"""

        # 硬纪律模块
        html += """
        <div style="border:1px solid #e74c3c; border-radius:8px; padding:12px; margin-top:20px; background-color:#fff5f5;">
            <div style="font-weight:bold; color:#c0392b; font-size:14px; margin-bottom:8px; text-align:center;">⚠️ 2026 三条硬纪律</div>
            <ul style="margin:0; padding-left:20px; font-size:12px; color:#c0392b; line-height:1.6;">
                <li><b>不追涨</b>：不在表格区间内 = 什么都不做</li>
                <li><b>不动摇</b>：不因短期浮亏修改计划</li>
                <li><b>补底仓</b>：新增资金优先补入底仓层</li>
            </ul>
        </div>
        """

        # 晨爷模块 (格式化输出)
        if cy_data:
            # 格式化列表为HTML
            cy_list_html = ""
            for x in cy_data[:5]: # 只展示前5个最好的
                st_mark = "⚠️" if "ST" in x['name'] else ""
                kc_mark = "🚀" if x['symbol'].startswith("688") else ""
                cy_list_html += f"""
                <div style="display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px dotted #eee;">
                    <span>{st_mark}{kc_mark}<b>{x['name']}</b> <span style="font-size:10px;color:#999">({x['symbol']})</span></span>
                    <span style="color:#2980b9;">位置:{x['pos']}% <span style="font-size:10px;color:#ccc">| {x['status_tag']}</span></span>
                </div>
                """
            
            html += f"""
            <div style="margin-top:20px; font-size:12px; color:#555; border-top:1px dashed #eee; padding-top:10px;">
                <b style="color:#2c3e50">🏴‍☠️ 晨爷潜伏池 (Top 5):</b>
                <div style="margin-top:5px; background:#f4f6f7; padding:10px; border-radius:5px;">
                    {cy_list_html}
                </div>
                <div style="font-size:10px; color:#999; margin-top:5px;">*基于天地战法(月线位置) + 年线 + MACD综合评分</div>
            </div>
            """
            
        html += """
            <div style="text-align:center; margin-top:20px; font-size:10px; color:#ccc;">
                System 2026 v3.0 Fusion
            </div>
            </div>
        </div>
        """
        return html

    def send_pushplus(self, title, content):
        if not PUSHPLUS_TOKEN: return
        tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
        url = 'http://www.pushplus.plus/send'
        
        for token in tokens:
            t = token.strip()
            if not t: continue
            data = {
                "token": t, "title": title, "content": content, "template": "html"  
            }
            try:
                requests.post(url, json=data, timeout=10)
            except Exception:
                pass

if __name__ == "__main__":
    strategy = FusionStrategy()
    if strategy.get_market_data():
        kk_res = strategy.analyze_kingkong()
        cy_res = strategy.analyze_chenye()
        report = strategy.generate_report(kk_res, cy_res)
        strategy.send_pushplus("🏗️ Mango投资日报", report)
