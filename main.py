import akshare as ak
import pandas as pd
import requests
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timedelta

# ========================= 环境变量 (保持你原有的) =========================
# 必须在 GitHub Secrets 配置：SENDER_EMAIL (发件箱), SENDER_PASSWORD (授权码), RECEIVER_EMAIL (收件箱)
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ========================= 1. 金刚配置 (你的原有配置) =========================
QUOTES = [
    "“长江的水，神华的煤，广核的电，茅台的酒。这是中国最硬的物理资产。”",
    "“太贵了就不买，哪怕它涨到天上去。错失不是亏损。”",
    "“不要羡慕泡沫，泡沫破裂时，只有我们的水电站还在印钞。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”"
]

PORTFOLIO_CFG = {
    "600900": {"name": "长江电力","role": "🏔️ 养老基石","dps": 0.95,"strategy": "bond","risk_point": "股息率<2.8%"},
    "601088": {"name": "中国神华","role": "⚫️ 能源底座","dps": 2.62,"strategy": "bond","risk_point": "股息率<5.0%"},
    "601006": {"name": "大秦铁路","role": "🛤️ 国家存折","dps": 0.44,"strategy": "bond","risk_point": "股息率<5.5%"},
    "601985": {"name": "中国核电","role": "⚛️ 绿色引擎","dps": 0.17,"strategy": "growth","risk_point": "PE>25"},
    "600519": {"name": "贵州茅台","role": "👑 A股之王","dps": 30.8,"strategy": "value","risk_point": "PE>40"},
    "000858": {"name": "五粮液","role": "🍷 价值前锋","dps": 4.67,"strategy": "value","risk_point": "PE>25"},
    "000333": {"name": "美的集团","role": "🤖 全球制造","dps": 3.0,"strategy": "growth","risk_point": "PE>20"},
    "000568": {"name": "泸州老窖","role": "🚀 进攻核心","dps": 6.30,"strategy": "offensive","risk_point": "PE>30"},
    "002415": {"name": "海康威视","role": "📹 智能监控","dps": 0.40,"strategy": "growth","risk_point": "PE>30"}
}

# ========================= 2. 晨爷配置 (新增部分) =========================
CHENYE_CFG = {
    "MAX_PRICE": 15.0,        # 价格上限
    "MAX_CAP_BILLION": 60,    # 市值上限(亿)
    "POSITION_THRESHOLD": 20, # 位置水位(%)
    "HISTORY_YEARS": 4        # 回溯历史(年)
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.bond_yield = 2.10 # 十年期国债收益率
        self.df_all = None     # 全市场数据缓存

    def get_market_status(self):
        month = self.today.month
        msg, color = "📅 资产积累期", "#666"
        if month == 3: msg, color = "🇨🇳 两会/安全月", "#d93025"
        elif month == 4: msg, color = "📊 财报体检期", "#f39c12"
        elif month in [1, 2]: msg, color = "🧧 消费/春运旺季", "#d93025"
        elif month in [6, 7]: msg, color = "💰 分红复投期", "#188038"
        return msg, color

    def get_all_data(self):
        """一次性拉取全市场数据，给两边用"""
        try:
            print("📡 拉取全市场实时行情...")
            df = ak.stock_zh_a_spot_em()
            # 统一列名方便操作
            df = df.rename(columns={
                '代码': 'symbol', '名称': 'name', '最新价': 'price', 
                '总市值': 'market_cap', '市盈率-动态': 'pe_ttm', '涨跌幅': 'change'
            })
            # 简单清洗
            df['symbol'] = df['symbol'].astype(str)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
            df['pe_ttm'] = pd.to_numeric(df['pe_ttm'], errors='coerce')
            self.df_all = df
            return True
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            return False

    def analyze_portfolio(self):
        """分析金刚配置 (你的原有逻辑补全)"""
        if self.df_all is None: return []
        print("🛡️ 分析金刚配置...")
        results = []
        codes = list(self.portfolio.keys())
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()

        for _, row in target_df.iterrows():
            code = row['symbol']
            cfg = self.portfolio.get(code)
            price = row['price']
            
            # 计算股息和利差
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
                "yield": round(current_yield, 2), "spread": round(spread, 2),
                "status": status, "mental": cfg['mental_check']
            })
        return results

    def scan_chenye(self):
        """扫描晨爷策略 (新增逻辑)"""
        if self.df_all is None: return []
        print("🏴‍☠️ 扫描晨爷潜伏标的...")
        
        # 1. 粗筛
        df = self.df_all.copy()
        df = df[~df['name'].str.contains('ST|退|北')] # 去除垃圾
        df = df[
            (df['market_cap'] < CHENYE_CFG['MAX_CAP_BILLION'] * 100000000) & 
            (df['price'] < CHENYE_CFG['MAX_PRICE']) & 
            (df['price'] > 2.0)
        ]
        
        # 为了速度，只取符合初筛条件的前80个小市值的去算历史位置
        # (GitHub Actions 如果全跑几千只历史K线会超时，这里做个折中)
        candidates = df.sort_values(by='market_cap').head(80)
        results = []

        end_date = self.today.strftime("%Y%m%d")
        start_date = (self.today - timedelta(days=365 * CHENYE_CFG['HISTORY_YEARS'])).strftime("%Y%m%d")

        for _, row in candidates.iterrows():
            try:
                # 获取历史K线计算位置
                hist = ak.stock_zh_a_hist(symbol=row['symbol'], start_date=start_date, end_date=end_date, adjust="qfq")
                if hist.empty or len(hist) < 100: continue
                
                high = hist['最高'].max()
                low = hist['最低'].min()
                if high == low: continue
                
                pos = round(((row['price'] - low) / (high - low)) * 100, 2)
                
                if pos <= CHENYE_CFG['POSITION_THRESHOLD']:
                    results.append({
                        "symbol": row['symbol'], "name": row['name'], 
                        "price": row['price'], "pos": pos,
                        "cap": round(row['market_cap']/100000000, 2)
                    })
            except:
                continue
        
        # 按位置排序
        return sorted(results, key=lambda x: x['pos'])[:10]

    def send_email(self, subject, html_content):
        """发送邮件 (恢复你的 SMTP 逻辑)"""
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            print("⚠️ 未配置邮箱密码，跳过邮件发送")
            return

        msg = MIMEText(html_content, 'html', 'utf-8')
        msg['From'] = Header(SENDER_EMAIL)
        msg['To'] = Header(RECEIVER_EMAIL)
        msg['Subject'] = Header(subject, 'utf-8')

        try:
            # 尝试 SSL 端口 465 (QQ/163/Gmail 常用)
            server = smtplib.SMTP_SSL("smtp.qq.com", 465)
            # 如果是 163 邮箱，用: server = smtplib.SMTP_SSL("smtp.163.com", 465)
            # 如果是 Gmail，用: server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            server.quit()
            print("📧 邮件发送成功！")
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            # 如果 SSL 失败，可以尝试 TLS (587)
            try:
                print("🔄 尝试 TLS 发送...")
                server = smtplib.SMTP("smtp.qq.com", 587)
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
                server.quit()
                print("📧 TLS 邮件发送成功！")
            except Exception as e2:
                print(f"❌ TLS 也失败了: {e2}")

    def run(self):
        if not self.get_all_data(): return

        # 1. 跑结果
        kk_res = self.analyze_portfolio()
        cy_res = self.scan_chenye()

        # 2. 生成 HTML 报告 (邮件用 HTML 表格最清晰)
        quote = random.choice(QUOTES)
        mkt_msg, mkt_color = self.get_market_status()
        
        html = f"""
        <h2>📊 投资策略日报 ({self.today.strftime('%Y-%m-%d')})</h2>
        <p><i>{quote}</i></p>
        <p>市场周期: <b style="color:{mkt_color}">{mkt_msg}</b> | 国债锚: {self.bond_yield}%</p>
        <hr>
        <h3>🛡️ 金刚配置 (防守)</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;"><th>资产</th><th>现价</th><th>股息率</th><th>股债差</th><th>状态</th></tr>
        """
        
        for item in kk_res:
            color = "red" if "低估" in item['status'] or "击球" in item['status'] else "black"
            html += f"""
            <tr>
                <td>{item['role']} {item['name']}</td>
                <td>{item['price']}</td>
                <td>{item['yield']}%</td>
                <td>{item['spread']}</td>
                <td style="color:{color}"><b>{item['status']}</b></td>
            </tr>
            """
        html += "</table>"

        html += """
        <h3>🏴‍☠️ 晨爷潜伏 (进攻 - 3D战法)</h3>
        <p><small>标准: 市值<60亿 | 单价<15元 | 历史位置<20%</small></p>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;"><th>代码</th><th>名称</th><th>现价</th><th>位置%</th><th>市值(亿)</th></tr>
        """
        
        if cy_res:
            for item in cy_res:
                html += f"""
                <tr>
                    <td>{item['symbol']}</td>
                    <td>{item['name']}</td>
                    <td>{item['price']}</td>
                    <td>{item['pos']}%</td>
                    <td>{item['cap']}</td>
                </tr>
                """
        else:
            html += "<tr><td colspan='5'>今日无符合严格标准的标的</td></tr>"
        
        html += "</table>"
        html += "<p>⚠️ <small>注：机器筛选仅供参考，晨爷策略需人工复核[题材]与[压力位]。</small></p>"

        # 3. 发送
        self.send_email("投资日报: 金刚+晨爷", html)
        
        # 4. (可选) 如果你还想要 Pushplus 作为备用，解开下面这行
        # self.send_pushplus(...) 

if __name__ == "__main__":
    app = AutoStrategy()
    app.run()
