import akshare as ak
import pandas as pd
import requests
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 1. 环境变量 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ========================= 2. 30年·本分语录 =========================
QUOTES = [
    "“宁可错过紫金的暴涨，也不要在高位站岗。手里有现金，心中不慌。”",
    "“长江电力是你的养老金，美的集团是你的印钞机，五粮液是你的存钱罐。”",
    "“不要预测牛市，要时刻准备好牛市不来我们也能赚钱。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”"
]

# ========================= 3. 4321 最终持仓配置 =========================
PORTFOLIO_CFG = {
    "600900": {
        "name": "长江电力",
        "role": "🏔️ 基石 (40%)",
        "strategy": "hold",
        "buy_zone": 22.0,      # PE < 22 可定投
        "sell_zone": 30.0,
        "key_metric": "股息率",
        "mental": "它负责兜底。只要跌下来，就是加仓送分题。",
        "action": "有闲钱优先买它。"
    },
    "000858": {
        "name": "五粮液",
        "role": "💰 现金 (30%)",
        "strategy": "value",
        "buy_price": 100.0,    # 绝对价格监控
        "sell_zone": 25.0,
        "key_metric": "PE(TTM)",
        "mental": "它是工具。100元以下是黄金坑，110以上是合理，130以上停止买入。",
        "action": "持有2手不动，跌破100买第3手。"
    },
    "000333": {
        "name": "美的集团",
        "role": "🤖 成长 (20%)",
        "strategy": "growth",
        "buy_zone": 13.0,      # PE < 13 极度低估
        "sell_zone": 20.0,
        "key_metric": "PE(TTM)",
        "mental": "代替京沪高铁和紫金。它是中国制造业的巅峰，也是机器人的未来。",
        "action": "分批买入，拿住3-5年。"
    },
    "300059": {
        "name": "东方财富",
        "role": "🧨 期权 (10%)",
        "strategy": "casino",
        "buy_zone": 20.0,
        "sell_zone": 35.0,     # 泡沫红线
        "key_metric": "PE(TTM)",
        "mental": "这是彩票。仓位锁死 10%，无论涨跌绝不加仓。",
        "action": "大跌买，大涨卖，不长拿。"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()

    def get_market_status(self):
        return "🛡️ 稳健建仓期", "#188038"

    def get_data(self):
        try:
            df = ak.stock_zh_a_spot_em()
            codes = list(self.portfolio.keys())
            return df[df['代码'].isin(codes)].copy()
        except: return None

    def analyze(self):
        df = self.get_data()
        if df is None: return None
        results = []
        
        for index, row in df.iterrows():
            code = row['代码']
            cfg = self.portfolio.get(code)
            name = cfg['name']
            price = row['最新价']
            pe = row['市盈率-动态']
            
            # 智能信号生成
            signal = "🔒 持仓"
            color = "#666"
            tip = cfg['action']

            # 长电逻辑
            if code == "600900":
                if pe < 20.7: 
                    signal = "💎 加仓"
                    color = "#d93025"
                    tip = "当前估值具备长期性价比，建议定投。"

            # 五粮液逻辑
            elif code == "000858":
                if price < cfg['buy_price']:
                    signal = "🚨 抄底警报"
                    color = "#d93025"
                    tip = f"股价跌破 {cfg['buy_price']}！动用备用金买入！"
                elif pe > 18:
                    signal = "🛑 停买"
                    color = "#f39c12"
                    tip = "估值修复过半，停止买入，仅持有。"

            # 美的逻辑
            elif code == "000333":
                if pe < 13.5:
                    signal = "🟢 买入区"
                    color = "#188038"
                    tip = "处于低估区间，适合分批建仓。"

            # 东财逻辑
            elif code == "300059":
                if pe > 30:
                    signal = "⚠️ 高危"
                    color = "#8e44ad"
                    tip = "估值过高，严禁加仓，考虑止盈换长电。"

            results.append({
                "name": name, "role": cfg['role'], "price": price, "pe": pe,
                "signal": signal, "color": color, "tip": tip, "mental": cfg['mental']
            })
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        html = f"""<div style="font-family:Arial;max-width:600px;margin:0 auto;background:#f4f4f4;padding:15px;">
        <div style="background:#000;color:#fff;padding:15px;border-radius:10px;text-align:center;">
            <h3>🛡️ Mango投资日记</h3>
            <p style="font-size:12px;opacity:0.8;">{self.today.strftime("%Y-%m-%d")}</p>
        </div>
        <div style="margin:15px 0;background:#fff;padding:15px;border-left:4px solid #d93025;font-style:italic;">{quote}</div>"""
        
        for item in data:
            html += f"""
            <div style="background:#fff;padding:15px;margin-bottom:10px;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div><b style="font-size:18px;">{item['name']}</b> <span style="font-size:12px;background:#eee;padding:2px 5px;">{item['role']}</span></div>
                    <div style="background:{item['color']};color:#fff;padding:3px 8px;border-radius:4px;font-size:12px;">{item['signal']}</div>
                </div>
                <div style="margin:10px 0;font-size:24px;font-weight:bold;">{item['price']} <span style="font-size:12px;color:#999;font-weight:normal;">PE: {item['pe']}</span></div>
                <div style="background:#f9f9f9;padding:8px;font-size:13px;color:#333;border-radius:4px;">⚡ <b>指令：</b>{item['tip']}</div>
                <div style="margin-top:8px;font-size:12px;color:#888;">🧠 {item['mental']}</div>
            </div>"""
        
        return html + "</div>"

# ========================= 发送逻辑 =========================
def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    token_list = PUSHPLUS_TOKEN.replace("，", ",").split(",")
    for token in token_list:
        if token.strip():
            try:
                url = 'http://www.pushplus.plus/send'
                data = {"token": token.strip(), "title": title, "content": content, "template": "html"}
                requests.post(url, json=data)
            except Exception as e: print(f"Pushplus发送失败: {e}")

def send_email(title, content):
    if not SENDER_PASSWORD or not RECEIVER_EMAIL: return
    receivers = RECEIVER_EMAIL.replace("，", ",").split(",")
    try:
        msg = MIMEText(content, 'html', 'utf-8')
        msg['From'] = Header("Mango投资助理", 'utf-8')
        msg['Subject'] = Header(title, 'utf-8')
        
        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, receivers, msg.as_string())
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    bot = AutoStrategy()
    data = bot.analyze()
    
    if data:
        # 标题修改为 Mango投资日记 + 具体日期
        title_date = datetime.now().strftime('%Y-%m-%d')
        title = f"Mango投资日记 {title_date}"
        
        html_content = bot.generate_html(data)
        
        # 多通道推送
        send_pushplus(title, html_content)
        send_email(title, html_content)
        
        print("✅ 任务执行完毕")
    else:
        print("❌ 无数据，未发送")
