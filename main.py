import akshare as ak
import pandas as pd
import requests
import os
import random
import time
from datetime import datetime, timedelta

# ========================= 环境变量 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 1. 金刚配置 (防守/信仰) =========================
QUOTES = [
    "“长江的水，神华的煤，广核的电，茅台的酒。这是中国最硬的物理资产。”",
    "“太贵了就不买，哪怕它涨到天上去。错失不是亏损。”",
    "“不要羡慕泡沫，泡沫破裂时，只有我们的水电站还在印钞。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“流水不争先，争的是滔滔不绝。”"
]

PORTFOLIO_CFG = {
    "600900": {"name": "长江电力","role": "🏔️ 养老基石","dps": 0.95,"strategy": "bond"},
    "601088": {"name": "中国神华","role": "⚫️ 能源底座","dps": 2.62,"strategy": "bond"},
    "601006": {"name": "大秦铁路","role": "🛤️ 国家存折","dps": 0.44,"strategy": "bond"},
    "601985": {"name": "中国核电","role": "⚛️ 绿色引擎","dps": 0.17,"strategy": "growth"},
    "600519": {"name": "贵州茅台","role": "👑 A股之王","dps": 30.8,"strategy": "value"},
    "000858": {"name": "五粮液","role": "🍷 价值前锋","dps": 4.67,"strategy": "value"},
    "000333": {"name": "美的集团","role": "🤖 全球制造","dps": 3.0,"strategy": "growth"},
    "000568": {"name": "泸州老窖","role": "🚀 进攻核心","dps": 6.30,"strategy": "offensive"},
    "002415": {"name": "海康威视","role": "📹 智能监控","dps": 0.40,"strategy": "growth"}
}

# ========================= 2. 晨爷配置 (进攻/投机) =========================
CHENYE_CFG = {
    "MAX_PRICE": 15.0,        
    "MAX_CAP_BILLION": 60,    
    "POSITION_THRESHOLD": 20, 
    "HISTORY_YEARS": 4        
}

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
            df['pe_ttm'] = pd.to_numeric(df['pe_ttm'], errors='coerce')
            self.df_all = df
            return True
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            return False

    def analyze_kingkong(self):
        print("🛡️ [2/3] 分析金刚配置...")
        results = []
        codes = list(PORTFOLIO_CFG.keys())
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()
        
        for _, row in target_df.iterrows():
            code = row['symbol']
            cfg = PORTFOLIO_CFG.get(code)
            price = row['price']
            
            current_yield = (cfg['dps'] / price * 100) if price > 0 else 0
            spread = current_yield - self.bond_yield
            
            # 状态逻辑 & 颜色定义 (用于HTML)
            status_text = "观望"
            status_color = "#999999" # 灰色
            bg_color = "#f8f9fa"     # 默认背景
            
            if cfg['strategy'] == 'bond':
                if spread >= 1.5: 
                    status_text, status_color, bg_color = "💎 低估", "#d93025", "#fff5f5" # 红字淡红底
                elif spread >= 0.5: 
                    status_text, status_color, bg_color = "✅ 合理", "#188038", "#f0f9f4" # 绿字淡绿底
                else: 
                    status_text, status_color = "⚠️ 略贵", "#f1c40f"
            else:
                pe = row['pe_ttm']
                if pe > 0 and pe < 20: 
                    status_text, status_color, bg_color = "✅ 击球区", "#d93025", "#fff5f5"
                elif pe > 35: 
                    status_text, status_color = "⚠️ 过热", "#f1c40f"
            
            results.append({
                "name": cfg['name'], "role": cfg['role'], "price": price,
                "yield": f"{current_yield:.2f}", "spread": f"{spread:.2f}",
                "status": status_text, "color": status_color, "bg": bg_color
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
            time.sleep(0.3) # 保持延时防止封IP
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
        
        # HTML 头部样式
        html = f"""
        <div style="font-family:'Helvetica Neue',sans-serif; max-width:600px; margin:0 auto; color:#333;">
            <div style="background: linear-gradient(135deg, #d93025 0%, #c0392b 100%); color:white; padding:15px; border-radius:10px 10px 0 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size:18px; font-weight:bold;">🛡️ 融合策略日报</div>
                <div style="font-size:12px; opacity:0.9; margin-top:5px;">{date_str} {week_day} | 10年国债: {self.bond_yield}%</div>
            </div>
            <div style="background:#fff; padding:15px; border:1px solid #eee; border-top:none; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <div style="font-style:italic; color:#666; font-size:13px; margin-bottom:15px; border-left:3px solid #d93025; padding-left:10px;">
                    {quote}
                </div>
                
                <div style="font-weight:bold; color:#d93025; margin-bottom:10px; border-bottom:1px dashed #eee; padding-bottom:5px;">
                    🛡️ 十五五·金刚配置
                </div>
                <table style="width:100%; border-collapse:collapse; font-size:13px;">
                    <tr style="background:#f1f1f1; color:#666;">
                        <th style="padding:8px; text-align:left;">资产</th>
                        <th style="padding:8px; text-align:right;">现价</th>
                        <th style="padding:8px; text-align:right;">股息%</th>
                        <th style="padding:8px; text-align:center;">状态</th>
                    </tr>
        """
        
        # 生成金刚表格
        for item in kk_data:
            row_style = f"background-color:{item['bg']}; border-bottom:1px solid #eee;"
            html += f"""
            <tr style="{row_style}">
                <td style="padding:8px; color:#2c3e50;">
                    <div style="font-weight:bold;">{item['name']}</div>
                    <div style="font-size:10px; color:#999;">{item['role']}</div>
                </td>
                <td style="padding:8px; text-align:right; font-family:monospace; font-size:14px;">{item['price']}</td>
                <td style="padding:8px; text-align:right; color:#d93025;">{item['yield']}</td>
                <td style="padding:8px; text-align:center;">
                    <span style="background:{item['color']}; color:white; padding:2px 6px; border-radius:4px; font-size:10px;">{item['status']}</span>
                </td>
            </tr>
            """
            
        html += "</table>"
        
        # 生成晨爷表格
        if cy_data:
            html += f"""
            <div style="font-weight:bold; color:#2c3e50; margin-top:20px; margin-bottom:10px; border-bottom:1px dashed #eee; padding-bottom:5px;">
                🏴‍☠️ 晨爷潜伏 (市值<60亿 | 低位<20%)
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:12px;">
                <tr style="background:#f1f1f1; color:#666;">
                    <th style="padding:6px; text-align:left;">代码/名称</th>
                    <th style="padding:6px; text-align:right;">现价</th>
                    <th style="padding:6px; text-align:center;">位置%</th>
                    <th style="padding:6px; text-align:right;">市值(亿)</th>
                </tr>
            """
            for item in cy_data:
                html += f"""
                <tr style="border-bottom:1px solid #eee;">
                    <td style="padding:6px;">
                        <div style="font-weight:bold; color:#333;">{item['name']}</div>
                        <div style="font-size:10px; color:#999;">{item['symbol']}</div>
                    </td>
                    <td style="padding:6px; text-align:right;">{item['price']}</td>
                    <td style="padding:6px; text-align:center;">
                        <div style="background:#e3f2fd; color:#1976d2; padding:2px 0; border-radius:3px;">{item['pos']}%</div>
                    </td>
                    <td style="padding:6px; text-align:right; color:#666;">{item['cap']}</td>
                </tr>
                """
            html += "</table>"
        else:
            html += """<div style="text-align:center; padding:20px; color:#999; font-size:12px;">今日无符合严格标准(20%低位)的标的</div>"""
            
        html += """
            <div style="text-align:center; margin-top:20px; font-size:10px; color:#ccc;">
                AI Strategy Assistant
            </div>
            </div>
        </div>
        """
        return html

    def send_pushplus(self, title, content):
        if not PUSHPLUS_TOKEN:
            print("⚠️ Token未配置")
            return

        tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
        url = 'http://www.pushplus.plus/send'
        
        for token in tokens:
            t = token.strip()
            if not t: continue
            
            # 这里改为了 template: html
            data = {
                "token": t, 
                "title": title, 
                "content": content, 
                "template": "html"  
            }
            
            try:
                res = requests.post(url, json=data, timeout=10)
                print(f"✅ 推送结果 ({t[:4]}***): {res.json().get('msg')}")
            except Exception as e:
                print(f"❌ 推送异常: {e}")

if __name__ == "__main__":
    strategy = FusionStrategy()
    if strategy.get_market_data():
        kk_res = strategy.analyze_kingkong()
        cy_res = strategy.analyze_chenye()
        report = strategy.generate_report(kk_res, cy_res)
        strategy.send_pushplus("🛡️ 融合策略日报", report)
