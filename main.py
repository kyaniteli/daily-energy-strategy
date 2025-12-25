import akshare as ak
import pandas as pd
import requests
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 环境变量读取 =========================
# 这些敏感信息稍后在 GitHub 网页上配置，不要直接填在这里
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# ========================= 策略配置 =========================
PORTFOLIO_CFG = {
    "601088": {"name": "中国神华", "target": "40%", "dps": 3.245, "strategy": "dividend"},
    "003816": {"name": "中国广核", "target": "30%", "dps": 0.095, "strategy": "growth"},
    "600406": {"name": "国电南瑞", "target": "15%", "dps": 0.58,  "strategy": "tech"},
    "000333": {"name": "美的集团", "target": "15%", "dps": 3.50,  "strategy": "bond"}
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG

    def get_data(self):
        print("正在从云端获取 A 股行情...")
        try:
            df = ak.stock_zh_a_spot_em()
            codes = list(self.portfolio.keys())
            subset = df[df['代码'].isin(codes)].copy()
            return subset
        except Exception as e:
            print(f"数据获取失败: {e}")
            return None

    def analyze(self):
        df = self.get_data()
        if df is None: return None
        results = []
        for index, row in df.iterrows():
            code = row['代码']
            info = self.portfolio.get(code)
            if not info: continue
            
            name = info['name']
            price = row['最新价']
            pe = row['市盈率-动态']
            pb = row['市净率']
            dps = info['dps']
            div_yield = (dps / price * 100) if price > 0 else 0
            
            signal, color = "持有", "black"
            st_type = info['strategy']

            if st_type == "dividend": # 神华
                if div_yield >= 6.0: signal, color = "🔴强力买入", "red"
                elif div_yield <= 4.0: signal, color = "🟢止盈减仓", "green"
            elif st_type == "growth": # 广核
                if pb <= 1.4: signal, color = "🔴机会买入", "red"
                elif pb >= 2.2: signal, color = "⚪暂停定投", "gray"
                else: signal, color = "🔵维持定投", "blue"
            elif st_type == "tech": # 南瑞
                if pe <= 20: signal, color = "🔴黄金坑买入", "red"
                elif pe >= 30: signal, color = "🟢泡沫卖出", "green"
                else: signal, color = "🔵观察/持有", "blue"
            elif st_type == "bond": # 美的
                if div_yield >= 4.0 and pe < 15: signal, color = "🔵现金替代买入", "blue"

            results.append({
                "名称": name, "现价": price, "PE": pe, "PB": pb,
                "股息率%": round(div_yield, 2), "仓位": info['target'],
                "指令": signal, "_color": color
            })
        return pd.DataFrame(results)

    def generate_html(self, df):
        html = """<table border="1" style="border-collapse: collapse; width: 100%; text-align: center;">
        <tr style="background-color: #f2f2f2;"><th>名称</th><th>现价</th><th>股息率%</th><th>指令</th></tr>"""
        for _, row in df.iterrows():
            style = f"font-weight: bold; color: {row['_color']};"
            html += f"<tr><td>{row['名称']}</td><td>{row['现价']}</td><td>{row['股息率%']}%</td><td style='{style}'>{row['指令']}</td></tr>"
        html += "</table>"
        return html

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    print("正在推送到微信...")
    url = 'http://www.pushplus.plus/send'
    data = {"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "html"}
    requests.post(url, json=data)

def send_email(title, content):
    if not SENDER_PASSWORD: return
    print("正在发送邮件...")
    msg = MIMEText(content, 'html', 'utf-8')
    msg['From'] = Header("AI能源助理", 'utf-8')
    msg['Subject'] = Header(title, 'utf-8')
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465) # 默认QQ邮箱，其他请改host
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"邮件错误: {e}")

if __name__ == "__main__":
    print("🚀 开始执行策略分析...")
    bot = AutoStrategy()
    df = bot.analyze()
    if df is not None and not df.empty:
        title = f"【{datetime.now().strftime('%m-%d')}】能源组合日报"
        html = bot.generate_html(df)
        print(df[['名称', '现价', '指令']]) # 打印到日志
        send_pushplus(title, html)
        send_email(title, html)
        print("✅ 执行完毕")
    else:
        print("❌ 未获取到数据或休市")