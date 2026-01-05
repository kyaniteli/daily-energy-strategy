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
# 务必确保你的 GitHub Secrets 或本地环境变量里有名为 PUSHPLUS_TOKEN 的变量
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 1. 2026年·工程化建仓总表 =========================
PORTFOLIO_CFG = {
    # === 🧱 底仓层 (60%) ===
    "600900": { "name": "长江电力", "role": "🧱 永续现金", "type": "grid", "grids": [27.5, 26.5, 25.5], "dps": 0.95, "tip": "跌就是噪音" },
    "601088": { "name": "中国神华", "role": "🧱 能源底座", "type": "grid", "grids": [42.0, 40.0, 38.0], "dps": 2.62, "tip": "现金流不说谎" },
    "600941": { "name": "中国移动", "role": "🧱 现金奶牛", "type": "yield", "target_yield": 6.0, "dps": 4.80, "tip": "买的是现金" },
    # === ⚔️ 阿尔法层 (30%) ===
    "000568": { "name": "泸州老窖", "role": "⚔️ 均值回归", "type": "grid", "grids": [110.0, 105.0, 100.0], "dps": 6.30, "tip": "贵的时候别碰" },
    "000333": { "name": "美的集团", "role": "⚔️ 全球制造", "type": "grid", "grids": [75.0, 72.0, 70.0], "dps": 3.0, "tip": "必须等悲观" },
    "002415": { "name": "海康威视", "role": "⚔️ 进攻博弈", "type": "grid", "grids": [30.0, 28.0, 27.0], "dps": 0.40, "tip": "逻辑破坏即撤" }
}

# ========================= 2. 晨爷配置 (升级版) =========================
CHENYE_CFG = {
    "MAX_PRICE": 15.0,           
    "MAX_CAP_BILLION": 50,       
    "POSITION_THRESHOLD": 0.15,  
    "MA_WINDOW": 250,            
    "MA_DISTANCE_MAX": 0.20,     
    "INCLUDE_ST": True,          
    "BOOST_688": True,           
    "SCAN_LIMIT": 30             # [降级] 调低扫描数量，防止 GitHub Action 超时导致发不出消息
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
            # 增加重试机制，防止akshare偶尔连接失败
            for _ in range(3):
                try:
                    df = ak.stock_zh_a_spot_em()
                    if df is not None and not df.empty:
                        break
                except:
                    time.sleep(2)
            else:
                print("❌ 3次尝试拉取行情均失败")
                return False

            df = df.rename(columns={
                '代码': 'symbol', '名称': 'name', '最新价': 'price', 
                '总市值': 'market_cap', '市盈率-动态': 'pe_ttm', '涨跌幅': 'change'
            })
            df['symbol'] = df['symbol'].astype(str)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
            self.df_all = df
            print("✅ 行情获取成功")
            return True
        except Exception as e:
            print(f"❌ 数据获取严重错误: {e}")
            return False

    # === King Kong 逻辑 ===
    def analyze_kingkong(self):
        print("🛡️ [2/3] 执行2026建仓逻辑...")
        results = []
        if self.df_all is None or self.df_all.empty: return []
        
        codes = list(PORTFOLIO_CFG.keys())
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()
        
        for _, row in target_df.iterrows():
            code = row['symbol']
            cfg = PORTFOLIO_CFG.get(code)
            if not cfg: continue
            
            price = row['price']
            current_yield = (cfg['dps'] / price * 100) if price > 0 else 0
            
            status_text, status_color, bg_color, action_tip = "等待", "#999", "#fff", f"现价 {price}"

            if cfg['type'] == 'grid':
                g1, g2, g3 = cfg['grids']
                if price > g1:
                    status_text, status_color, action_tip = "⏸️ 观望", "#95a5a6", f"目标 < {g1}"
                elif g2 < price <= g1:
                    status_text, status_color, bg_color, action_tip = "🟢 试探", "#27ae60", "#f0f9f4", f"区间 {g2}-{g1}"
                elif g3 < price <= g2:
                    status_text, status_color, bg_color, action_tip = "🟡 加仓", "#f39c12", "#fffaf0", f"区间 {g3}-{g2}"
                elif price <= g3:
                    status_text, status_color, bg_color, action_tip = "🔴 击球", "#c0392b", "#fff5f5", f"黄金坑 < {g3}"
            elif cfg['type'] == 'yield':
                target_yield = cfg.get('target_yield', 6.0)
                if current_yield >= target_yield:
                    status_text, status_color, bg_color = "🔴 达标", "#c0392b", "#fff5f5"
                else:
                    status_text, status_color = "⏸️ 等待", "#95a5a6"
                action_tip = f"目标股息 > {target_yield}%"

            results.append({
                "name": cfg['name'], "role": cfg['role'], "price": price,
                "yield": f"{current_yield:.2f}", 
                "status": status_text, "color": status_color, "bg": bg_color,
                "tip": cfg['tip'], "action_tip": action_tip
            })
        return results

    # === 晨爷逻辑 ===
    def analyze_chenye(self):
        print("🏴‍☠️ [3/3] 扫描晨爷潜伏标的...")
        results = []
        if self.df_all is None: return []

        try:
            df = self.df_all.copy()
            df = df[
                (df['market_cap'] < CHENYE_CFG['MAX_CAP_BILLION'] * 100000000) & 
                (df['price'] < CHENYE_CFG['MAX_PRICE']) & 
                (df['price'] > 1.0) 
            ]
            
            def _is_bad_name(name):
                if not isinstance(name, str): return True
                if any(k in name for k in ["退", "N", "C"]): return True
                if not CHENYE_CFG['INCLUDE_ST'] and ("ST" in name): return True
                return False
                
            df = df[~df['name'].apply(_is_bad_name)]
            candidates = df.sort_values(by='market_cap').head(CHENYE_CFG['SCAN_LIMIT'])
            
            print(f"   - 初筛入围: {len(candidates)} 只")

            count = 0
            for _, row in candidates.iterrows():
                count += 1
                if count % 10 == 0: print(f"   - 扫描进度: {count}/{len(candidates)}")
                
                # 容错处理：如果单个股票分析失败，跳过，不要崩溃整个程序
                try:
                    tech_data = self._analyze_single_stock_depth(row['symbol'], row['price'])
                    if tech_data:
                        results.append({
                            "symbol": row['symbol'], "name": row['name'], "price": row['price'], 
                            "pos": tech_data['pos_rank'], "score": tech_data['score'], 
                            "status_tag": tech_data['status']
                        })
                except Exception as e:
                    continue # 跳过报错的个股
            
            return sorted(results, key=lambda x: x['score'], reverse=True)[:10]
        
        except Exception as e:
            print(f"⚠️ 晨爷策略整体运行出错: {e}")
            return [] # 返回空列表，保证后续流程继续

    def _analyze_single_stock_depth(self, code, current_price):
        try:
            start_date = (self.today - timedelta(days=365 * 4)).strftime("%Y%m%d")
            end_date = self.today.strftime("%Y%m%d")
            
            # AkShare 接口不稳定时重试一次
            for _ in range(2):
                try:
                    df_hist = ak.stock_zh_a_hist(symbol=code, start_date=start_date, end_date=end_date, adjust="qfq")
                    if df_hist is not None and not df_hist.empty: break
                except:
                    time.sleep(1)
            else:
                return None

            if len(df_hist) < CHENYE_CFG['MA_WINDOW']: return None

            df_hist["日期"] = pd.to_datetime(df_hist["日期"])
            df_hist = df_hist.set_index("日期").sort_index()
            
            # 月线重采样 (兼容性写法)
            try:
                # 尝试新版 pandas 写法
                resampler = df_hist.resample("ME") 
                df_month = pd.DataFrame({"最高": resampler["最高"].max(), "最低": resampler["最低"].min()}).dropna()
            except:
                # 回退旧版
                resampler = df_hist.resample("M")
                df_month = pd.DataFrame({"最高": resampler["最高"].max(), "最低": resampler["最低"].min()}).dropna()

            if len(df_month) < 12: return None

            hist_high = df_month["最高"].max()
            hist_low = df_month["最低"].min()
            
            if hist_high == hist_low: return None
            
            pos_rank = (current_price - hist_low) / (hist_high - hist_low)
            if pos_rank > CHENYE_CFG['POSITION_THRESHOLD']: return None

            ma250 = df_hist["收盘"].tail(CHENYE_CFG['MA_WINDOW']).mean()
            dist_to_ma250 = (current_price - ma250) / ma250
            if dist_to_ma250 > CHENYE_CFG['MA_DISTANCE_MAX']: return None

            macd_ok = self._check_macd(df_hist["收盘"])

            score = (1 - (pos_rank / CHENYE_CFG['POSITION_THRESHOLD'])) * 50
            score += (1 - min(abs(dist_to_ma250)/0.2, 1)) * 30
            if macd_ok: score += 10
            if CHENYE_CFG['BOOST_688'] and code.startswith("688"): score += 10
            
            status = "潜伏"
            if -0.05 <= dist_to_ma250 <= 0.05: status = "年线关键"
            if macd_ok: status += "/MACD优"

            return {"pos_rank": round(pos_rank * 100, 1), "score": round(score, 1), "status": status}

        except Exception:
            return None

    def _check_macd(self, close_series):
        try:
            if len(close_series) < 30: return False
            ema12 = close_series.ewm(span=12, adjust=False).mean()
            ema26 = close_series.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            macd_hist = (dif - dea) * 2
            
            tail = macd_hist.dropna().iloc[-3:]
            if len(tail) < 3: return False
            v1, v2, v3 = tail.iloc[-3], tail.iloc[-2], tail.iloc[-1]
            return ((v1 < 0 and v2 < 0 and v3 < 0) and (abs(v3) < abs(v2))) or ((v2 < 0) and (v3 > 0))
        except:
            return False

    def generate_report(self, kk_data, cy_data):
        # 如果数据为空，生成一个简易报告，防止报错
        if not kk_data and not cy_data:
            return "<h3>⚠️ 今日数据拉取失败</h3><p>请检查 GitHub Action 日志。</p>"

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
                        <th style="padding:8px; text-align:right;">信号</th>
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
                </td>
                <td style="padding:8px; text-align:center;">
                    <span style="background:{item['color']}; color:white; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:bold;">{item['status']}</span>
                </td>
            </tr>
            """
            
        html += """</table>"""

        if cy_data:
            cy_list_html = ""
            for x in cy_data[:5]: 
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
                <div style="font-size:10px; color:#999; margin-top:5px;">*基于天地战法(月线位置) + 年线 + MACD评分</div>
            </div>
            """
        else:
             html += """<div style="margin-top:20px; font-size:12px; color:#999; text-align:center;">(今日无晨爷策略入选或扫描未完成)</div>"""
            
        html += """
            <div style="text-align:center; margin-top:20px; font-size:10px; color:#ccc;">
                System 2026 v3.1 Stable
            </div>
            </div>
        </div>
        """
        return html

    def send_pushplus(self, title, content):
        if not PUSHPLUS_TOKEN:
            print("❌ 错误: 未找到 PUSHPLUS_TOKEN，无法发送推送。")
            return

        print(f"📧 准备发送推送，Token长度: {len(PUSHPLUS_TOKEN)}，内容长度: {len(content)}")
        
        # 支持多Token群发
        tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
        url = 'http://www.pushplus.plus/send'
        
        for token in tokens:
            t = token.strip()
            if not t: continue
            
            data = {
                "token": t, "title": title, "content": content, "template": "html"  
            }
            try:
                # 增加超时时间到15秒，并打印响应状态
                response = requests.post(url, json=data, timeout=15)
                print(f"📨 推送响应: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ 推送失败: {e}")

if __name__ == "__main__":
    strategy = FusionStrategy()
    
    # 增加容错：即使晨爷策略报错，也不影响底仓日报发送
    kk_res = []
    cy_res = []

    if strategy.get_market_data():
        # 1. 执行底仓逻辑 (最重要，优先执行)
        try:
            kk_res = strategy.analyze_kingkong()
        except Exception as e:
            print(f"❌ KingKong 策略出错: {e}")

        # 2. 执行晨爷逻辑 (放在 try 块中，防止耗时过长或报错导致全挂)
        try:
            cy_res = strategy.analyze_chenye()
        except Exception as e:
            print(f"❌ 晨爷策略出错 (已跳过): {e}")

        # 3. 生成报告并发送
        # 只要有任意数据就发送
        if kk_res or cy_res:
            report = strategy.generate_report(kk_res, cy_res)
            strategy.send_pushplus("🏗️ Mango投资日报", report)
        else:
            print("⚠️ 没有生成任何数据，取消发送。")
    else:
        print("❌ 无法获取行情数据，脚本终止。")
