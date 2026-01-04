import akshare as ak
import pandas as pd
import requests
import os
import random
import time
from datetime import datetime, timedelta

# ========================= 环境变量 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 1. 2026年·工程化建仓总表 =========================
# 核心原则：底仓60% (稳) + 阿尔法30% (错价)
# type: "grid" (按价格网格) | "yield" (按股息率)
# grids: [第一笔(试探), 第二笔(加仓), 第三笔(击球/极限)]
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
        "target_yield": 6.0, # 目标股息率
        "dps": 4.80, # 2024预估分红(参考)
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

# ========================= 2. 晨爷配置 (保持不变) =========================
CHENYE_CFG = {
    "MAX_PRICE": 15.0,        
    "MAX_CAP_BILLION": 60,    
    "POSITION_THRESHOLD": 20, 
    "HISTORY_YEARS": 4        
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
        self.bond_yield = 2.10  
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

    def analyze_kingkong(self):
        print("🛡️ [2/3] 执行2026建仓逻辑...")
        results = []
        codes = list(PORTFOLIO_CFG.keys())
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()
        
        for _, row in target_df.iterrows():
            code = row['symbol']
            cfg = PORTFOLIO_CFG.get(code)
            price = row['price']
            
            # 计算股息率
            current_yield = (cfg['dps'] / price * 100) if price > 0 else 0
            
            # === 2026 核心判断逻辑 ===
            status_text = "等待"
            status_color = "#999" # 默认灰
            bg_color = "#fff"     # 默认白
            action_tip = f"现价 {price}"

            if cfg['type'] == 'grid':
                # 网格策略：比对 [试探, 加仓, 击球]
                g1, g2, g3 = cfg['grids']
                
                if price > g1:
                    status_text = "⏸️ 观望" # 高于第一笔
                    status_color = "#95a5a6"
                    action_tip = f"目标 < {g1}"
                elif g2 < price <= g1:
                    status_text = "🟢 试探" # 进入第一区间 (轻仓)
                    status_color = "#27ae60" 
                    bg_color = "#f0f9f4"
                    action_tip = f"区间 {g2}-{g1}"
                elif g3 < price <= g2:
                    status_text = "🟡 加仓" # 进入第二区间 (加重)
                    status_color = "#f39c12" 
                    bg_color = "#fffaf0"
                    action_tip = f"区间 {g3}-{g2}"
                elif price <= g3:
                    status_text = "🔴 击球" # 低于极限价 (黄金坑)
                    status_color = "#c0392b" 
                    bg_color = "#fff5f5"
                    action_tip = f"黄金坑 < {g3}"
                    
            elif cfg['type'] == 'yield':
                # 股息策略 (如中移动)
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

    def analyze_chenye(self):
        print("🏴‍☠️ [3/3] 扫描晨爷潜伏标的...")
        results = []
        df = self.df_all.copy()
        df = df[~df['name'].str.contains('ST|退|北')]
        df = df[
            (df['market_cap'] < CHENYE_CFG['MAX_CAP_BILLION'] * 100000000) & 
            (df['price'] < CHENYE_CFG['MAX_PRICE']) & 
            (df['price'] > 2.5) 
        ]
        candidates = df.sort_values(by='market_cap').head(80)
        
        for _, row in candidates.iterrows():
            time.sleep(0.3) # 保持延时，防止封号
            pos_data = self.calculate_position(row['symbol'], row['price'])
            if pos_data and pos_data['pos'] <= CHENYE_CFG['POSITION_THRESHOLD']:
                results.append({
                    "symbol": row['symbol'], "name": row['name'], 
                    "price": row['price'], "pos": pos_data['pos'],
                    "cap": round(row['market_cap'] / 100000000, 2)
                })
        return sorted(results, key=lambda x: x['pos'])[:10]

    def calculate_position(self, symbol, current_price):
        end_date = self.today.strftime("%Y%m%d")
        start_date = (self.today - timedelta(days=365 * CHENYE_CFG['HISTORY_YEARS'])).strftime("%Y%m%d")
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
            if df.empty or len(df) < 100: return None
            high = df['最高'].max()
            low = df['最低'].min()
            if high == low: return None
            pos = round(((current_price - low) / (high - low)) * 100, 2)
            return {'pos': pos}
        except:
            return None

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

        # 硬纪律模块 (红框)
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

        # 晨爷模块
        if cy_data:
            html += f"""
            <div style="margin-top:20px; font-size:12px; color:#999; border-top:1px dashed #eee; padding-top:10px;">
                <b>🏴‍☠️ 晨爷潜伏观察：</b><br>
                {' · '.join([f"{x['name']}({x['pos']}%)" for x in cy_data[:5]])}
            </div>
            """
            
        html += """
            <div style="text-align:center; margin-top:20px; font-size:10px; color:#ccc;">
                System 2026 v2.0
            </div>
            </div>
        </div>
        """
        return html

    def send_pushplus(self, title, content):
        # 1. 检查 Token
        if not PUSHPLUS_TOKEN: return

        # 2. 清洗逻辑 (防报错)
        tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
        url = 'http://www.pushplus.plus/send'
        
        for token in tokens:
            t = token.strip()
            if not t: continue
            
            data = {
                "token": t, 
                "title": title, 
                "content": content, 
                "template": "html"  
            }
            
            try:
                # 增加 timeout 防止卡死
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
