import akshare as ak
import pandas as pd
import requests
import os
import random
import time
import traceback
from datetime import datetime, timedelta

# ========================= 环境变量 =========================
# 记得在 GitHub Secrets 里配置 PUSHPLUS_TOKEN
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 1. 金刚配置 (核心持仓) =========================
QUOTES = [
    "“长江的水，神华的煤，广核的电，茅台的酒。这是中国最硬的物理资产。”",
    "“太贵了就不买，哪怕它涨到天上去。错失不是亏损。”",
    "“不要羡慕泡沫，泡沫破裂时，只有我们的水电站还在印钞。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”"
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

# ========================= 2. 晨爷配置 (潜伏策略) =========================
CHENYE_CFG = {
    "MAX_PRICE": 20.0,        # 价格上限
    "MAX_CAP_BILLION": 50,    # 市值上限(亿)
    "POSITION_THRESHOLD": 15, # 位置水位(%) - 只有在地板上的才看
    "HISTORY_YEARS": 3,       # 回溯3年数据
    "SCAN_LIMIT": 15          # ⚠️关键：限制每次只深度扫描15个，防止GitHub超时
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.bond_yield = 2.10 # 十年期国债收益率
        self.df_all = None

    def get_market_status(self):
        month = self.today.month
        msg, color = "📅 资产积累期", "#666"
        if month == 3: msg, color = "🇨🇳 两会/安全月", "#d93025"
        elif month == 4: msg, color = "📊 财报体检期", "#f39c12"
        elif month in [1, 2]: msg, color = "🧧 消费/春运旺季", "#d93025"
        elif month in [6, 7]: msg, color = "💰 分红复投期", "#188038"
        return msg, color

    def get_all_data(self):
        """一次性拉取全市场数据 (带重试机制)"""
        print("📡 正在连接 AKShare 接口...")
        try:
            # 尝试拉取实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 检查关键列是否存在，防止接口变动
            if '代码' not in df.columns or '最新价' not in df.columns:
                print("❌ AKShare 返回数据格式异常，缺少关键列")
                return False

            # 统一列名
            rename_map = {
                '代码': 'symbol', '名称': 'name', '最新价': 'price', 
                '总市值': 'market_cap', '市盈率-动态': 'pe_ttm', '涨跌幅': 'change'
            }
            # 只重命名存在的列
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            
            # 数据清洗：转成数字格式
            df['symbol'] = df['symbol'].astype(str)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
            
            # 处理PE (有的可能是 - 或者 NaN)
            if 'pe_ttm' in df.columns:
                df['pe_ttm'] = pd.to_numeric(df['pe_ttm'], errors='coerce')
            else:
                df['pe_ttm'] = 0.0

            self.df_all = df
            print(f"✅ 获取成功，共 {len(df)} 条数据")
            return True
        except Exception as e:
            print(f"❌ 数据获取严重失败: {e}")
            traceback.print_exc()
            return False

    def analyze_portfolio(self):
        """分析金刚配置"""
        if self.df_all is None: return []
        print("🛡️ 分析持仓...")
        results = []
        codes = list(self.portfolio.keys())
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()

        for _, row in target_df.iterrows():
            try:
                code = row['symbol']
                cfg = self.portfolio.get(code)
                price = row['price']
                
                # 股息率计算
                current_yield = (cfg['dps'] / price * 100) if price > 0 else 0
                spread = current_yield - self.bond_yield
                
                # 状态判定
                status = "😐"
                if cfg['strategy'] == 'bond':
                    if spread >= 1.5: status = "💎 低估"
                    elif spread >= 0.5: status = "✅ 合理"
                    else: status = "⚠️ 略贵"
                else:
                    pe = row['pe_ttm']
                    if pe > 0 and pe < 20: status = "✅ 击球区"
                    elif pe > 35: status = "⚠️ 过热"

                results.append({
                    "name": cfg['name'], "role": cfg['role'], "price": price,
                    "yield": round(current_yield, 2), "status": status
                })
            except Exception as e:
                print(f"⚠️ 处理 {code} 时出错: {e}")
                continue
        return results

    def scan_chenye(self):
        """扫描晨爷策略 (高风险操作，增加保护)"""
        if self.df_all is None: return []
        print("🏴‍☠️ 扫描潜伏标的...")
        
        results = []
        try:
            df = self.df_all.copy()
            # 基础过滤: 去掉ST、退市、北交所(8/4/92开头)
            df = df[~df['name'].str.contains('ST|退')]
            df = df[~df['symbol'].str.startswith(('8', '4', '92'))]
            
            # 价格和市值过滤
            df = df[
                (df['market_cap'] < CHENYE_CFG['MAX_CAP_BILLION'] * 100000000) & 
                (df['price'] < CHENYE_CFG['MAX_PRICE']) & 
                (df['price'] > 2.0)
            ]
            
            # !!! 关键修改：只取市值最小的 N 个，防止超时 !!!
            # 晨爷策略核心就是小市值，所以我们先按市值排序，只看最小的那批
            candidates = df.sort_values(by='market_cap').head(CHENYE_CFG['SCAN_LIMIT'])
            
            end_date = self.today.strftime("%Y%m%d")
            start_date = (self.today - timedelta(days=365 * CHENYE_CFG['HISTORY_YEARS'])).strftime("%Y%m%d")

            print(f"🔍 深度扫描 {len(candidates)} 只候选股 (每只暂停0.5秒)...")
            
            for i, (_, row) in enumerate(candidates.iterrows()):
                try:
                    # 避免请求太快被封 IP
                    time.sleep(0.5) 
                    
                    hist = ak.stock_zh_a_hist(symbol=row['symbol'], start_date=start_date, end_date=end_date, adjust="qfq")
                    if hist is None or hist.empty or len(hist) < 50: continue
                    
                    high = hist['最高'].max()
                    low = hist['最低'].min()
                    if high == low: continue
                    
                    # 计算位置分位数
                    pos = round(((row['price'] - low) / (high - low)) * 100, 2)
                    
                    if pos <= CHENYE_CFG['POSITION_THRESHOLD']:
                        results.append({
                            "name": row['name'], "symbol": row['symbol'], 
                            "price": row['price'], "pos": pos,
                            "cap": round(row['market_cap']/100000000, 2)
                        })
                except Exception as inner_e:
                    # 单个股票失败不影响整体
                    continue
                    
        except Exception as e:
            print(f"⚠️ 晨爷策略扫描中断: {e}")
        
        # 返回前8个位置最低的
        return sorted(results, key=lambda x: x['pos'])[:8]

    def run(self):
        try:
            if not self.get_all_data():
                return "❌ 数据获取失败，请查看 Action 日志"

            kk_res = self.analyze_portfolio()
            cy_res = self.scan_chenye() 

            # 生成 HTML
            quote = random.choice(QUOTES)
            mkt_msg, mkt_color = self.get_market_status()
            
            html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 500px;">
                <h3 style="border-left: 5px solid #d93025; padding-left: 10px;">📊 策略日报 {self.today.strftime('%m-%d')}</h3>
                <p style="background: #f4f4f4; padding: 8px; font-size: 12px; color: #555;">{quote}</p>
                <p style="font-size: 12px;">状态: <b style="color:{mkt_color}">{mkt_msg}</b> | 国债: {self.bond_yield}%</p>
                
                <h4 style="background: #eee; padding: 5px;">🛡️ 核心持仓</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <tr style="background: #333; color: white;"><th>名称</th><th>现价</th><th>股息%</th><th>评价</th></tr>
            """
            for item in kk_res:
                # 评价颜色：低估用红(喜庆/机会)，略贵用绿/黑
                color = "red" if "低估" in item['status'] or "击球" in item['status'] else "black"
                html += f"""
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding:5px;">{item['name']}</td>
                        <td style="text-align:center;">{item['price']}</td>
                        <td style="text-align:center;">{item['yield']}</td>
                        <td style="text-align:center; color:{color}; font-weight:bold;">{item['status']}</td>
                    </tr>"""
            
            html += """</table><h4 style="background: #eee; padding: 5px; margin-top: 15px;">🏴‍☠️ 潜伏扫描 (进攻)</h4>"""
            
            if cy_res:
                html += """<table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                           <tr style="background: #666; color: white;"><th>名称</th><th>现价</th><th>位置%</th><th>市值</th></tr>"""
                for item in cy_res:
                    html += f"""
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding:5px;">{item['name']}<br><span style="color:#999">{item['symbol']}</span></td>
                            <td style="text-align:center;">{item['price']}</td>
                            <td style="text-align:center; color:red; font-weight:bold;">{item['pos']}</td>
                            <td style="text-align:center;">{item['cap']}亿</td>
                        </tr>"""
                html += "</table>"
            else:
                html += "<p style='font-size:12px; text-align:center;'>😴 今日无符合严格标准的标的</p>"
            
            html += "</div>"
            return html
            
        except Exception as e:
            traceback.print_exc()
            return f"❌ 程序运行崩溃: {str(e)}"

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN")
        return
    try:
        url = 'http://www.pushplus.plus/send'
        # template="html" 很重要，否则表格会乱
        data = {"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "html"}
        requests.post(url, json=data, timeout=10)
        print("✅ PushPlus 请求已发送")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

if __name__ == "__main__":
    print("🚀 任务开始...")
    strategy = AutoStrategy()
    content = strategy.run()
    
    if content:
        send_pushplus(f"复盘 {datetime.now().strftime('%m-%d')}", content)
    
    print("🏁 任务结束")
