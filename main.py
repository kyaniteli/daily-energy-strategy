import akshare as ak
import pandas as pd
import requests
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 环境变量 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ========================= 每日信仰语录 =========================
QUOTES = [
    "“简单比复杂更难：你必须努力工作，让思维变得清晰简单。” —— 乔布斯",
    "“长江电力不是股票，它是上帝发行的债券。”",
    "“奥卡姆剃刀：如果两个投资看起来差不多，选那个商业模式更简单的。”",
    "“流水不争先，争的是滔滔不绝。”",
    "“我们拥有了中国最核心的资产：长江的水、沿海的核、全国的网。”",
    "“不要为了高一点点的股息，去承担看不懂的风险。”",
    "“长期主义就是：即使明天股市关门，你也睡得着觉。”"
]

# ========================= 深度配置表 (水核网版) =========================
PORTFOLIO_CFG = {
    "600900": {
        "name": "长江电力",
        "role": "👑 永续债王", # 替代神华
        "target": "40%",
        "dps": 0.95,   # 假设分红(元)
        "strategy": "bond", # 纯债策略
        "metrics": ["股息率", "PE(TTM)", "国债利差"], 
        "mental_check": "只要长江还在流，这笔钱就丢不了。",
        "report_focus": "年报必看：来水偏枯还是偏丰？",
        "risk_point": "股息率 < 3.0% (太贵)"
    },
    "003816": {
        "name": "中国广核",
        "role": "⚓ 增量基石",
        "target": "30%",
        "dps": 0.095,
        "strategy": "growth",
        "metrics": ["PB", "PE(TTM)", "每股净资"],
        "mental_check": "核电是时间的玫瑰，慢慢存。",
        "report_focus": "年报必看：新机组投产进度。",
        "risk_point": "PB > 2.3倍"
    },
    "600406": {
        "name": "国电南瑞",
        "role": "⚔️ 科技进攻",
        "target": "30%",
        "dps": 0.58,
        "strategy": "tech",
        "metrics": ["PE(TTM)", "PEG", "ROE"],
        "mental_check": "AI 算力越强，电网越要升级。",
        "report_focus": "年报必看：经营性现金流净额。",
        "risk_point": "PE > 35倍 / 现金流恶化"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.action_count = 0
        self.bond_yield = 2.10 # 10年期国债收益率基准

    def get_market_status(self):
        month = self.today.month
        msg, color = "📅 长期持有期", "#666"
        if month == 3: msg, color = "🇨🇳 两会关注期", "#d93025"
        elif month == 4: msg, color = "📊 年报披露期", "#f39c12"
        elif month == 7: msg, color = "💰 分红到账期", "#188038"
        elif month == 12: msg, color = "❄️ 冬季枯水期 (关注水电出力)", "#3498db"
        return msg, color

    def get_data(self):
        try:
            df = ak.stock_zh_a_spot_em()
            codes = list(self.portfolio.keys())
            subset = df[df['代码'].isin(codes)].copy()
            return subset
        except: return None

    def analyze(self):
        df = self.get_data()
        if df is None: return None
        results = []
        
        for index, row in df.iterrows():
            code = row['代码']
            cfg = self.portfolio.get(code)
            
            name, price, pe, pb = cfg['name'], row['最新价'], row['市盈率-动态'], row['市净率']
            dps = cfg['dps']
            div_yield = (dps / price * 100) if price > 0 else 0
            
            # 指标生成
            extra_info = []
            for m in cfg.get('metrics', []):
                if m == "股息率": extra_info.append(f"股息: <b>{div_yield:.2f}%</b>")
                elif m == "PE(TTM)": extra_info.append(f"PE: {pe}")
                elif m == "PB": extra_info.append(f"PB: {pb}")
                elif m == "国债利差": extra_info.append(f"利差: <b>+{(div_yield - self.bond_yield):.2f}%</b>")
                elif m == "PEG": extra_info.append(f"PEG: {(pe/15):.2f}")
            extra_str = " | ".join(extra_info)

            # 信号逻辑 (长电/广核/南瑞)
            signal, color, tip = "🧘 持有/定投", "#333", "安心持有"
            st_type = cfg['strategy']

            if st_type == "bond": # 长电逻辑
                if div_yield >= 4.0: signal, color, tip = "🔴 黄金机会", "#d93025", "股息率极高"
                elif div_yield <= 3.0: signal, color, tip = "⚪ 略贵勿追", "#999", "性价比一般"
            elif st_type == "growth": # 广核逻辑
                if pb <= 1.45: signal, color, tip = "🔴 机会买入", "#d93025", "低估值"
                elif pb >= 2.2: signal, color, tip = "🟢 暂停定投", "#188038", "高估值"
            elif st_type == "tech": # 南瑞逻辑
                if pe <= 20: signal, color, tip = "🔴 黄金坑", "#d93025", "错杀"
                elif pe >= 30: signal, color, tip = "🟢 止盈", "#188038", "泡沫"
            
            # 财报季
            status_msg, _ = self.get_market_status()
            report_alert = ""
            if "年报" in status_msg:
                 report_alert = f"<div style='margin-top:5px; color:#d35400; font-size:12px; font-weight:bold;'>⚠️ 财报核查：{cfg['report_focus']}</div>"

            results.append({"base": {"name": name, "role": cfg['role'], "price": price}, "core": {"signal": signal, "color": color, "tip": tip, "data_str": extra_str}, "mind": {"check": cfg['mental_check'], "alert": report_alert}})
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        status_msg, status_color = self.get_market_status()
        html = f"""
        <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f4f6f9; padding: 15px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 18px; font-weight: bold; color: #2c3e50;">💧 ⚡ AI 能源组合日报</div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">{self.today.strftime("%Y-%m-%d %H:%M")}</div>
                <div style="margin-top: 8px; display: inline-block; background-color: {status_color}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">{status_msg}</div>
            </div>
            <div style="background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; font-style: italic; line-height: 1.5;">{quote}</div>
            </div>
        """
        for item in data:
            base, core, mind = item['base'], item['core'], item['mind']
            card_bg = "#fff5f5" if "买入" in core['signal'] or "黄金" in core['signal'] else "#ffffff"
            html += f"""
            <div style="background-color: {card_bg}; border-radius: 10px; padding: 15px; margin-bottom: 15px; border: 1px solid #e1e4e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div><span style="font-size: 16px; font-weight: bold; color: #2c3e50;">{base['name']}</span><span style="font-size: 12px; color: #95a5a6; margin-left: 5px;">{base['role']}</span></div>
                    <div style="background-color: {core['color']}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{core['signal']}</div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">{base['price']}</div>
                    <div style="font-size: 12px; color: #7f8c8d; text-align: right; line-height: 1.6;">{core['data_str']}</div>
                </div>
                <div style="font-size: 12px; color: {core['color']}; margin-bottom: 8px; font-weight: bold;">💡 策略提示：{core['tip']}</div>
                <div style="background-color: #f8f9fa; border-left: 3px solid #bdc3c7; padding: 8px; font-size: 12px; color: #555;">
                    <div>🧠 <b>潜意识：</b>{mind['check']}</div>{mind['alert']}
                </div>
            </div>"""
        html += "<div style='text-align: center; margin-top: 20px; font-size: 12px; color: #95a5a6;'><p>Simplicity is the ultimate sophistication.</p></div></div>"
        return html

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    for token in PUSHPLUS_TOKEN.replace("，", ",").split(","):
        if token.strip(): requests.post('http://www.pushplus.plus/send', json={"token": token.strip(), "title": title, "content": content, "template": "html"})

def send_email(title, content):
    if not SENDER_PASSWORD or not RECEIVER_EMAIL: return
    receivers = RECEIVER_EMAIL.replace("，", ",").split(",")
    msg = MIMEText(content, 'html', 'utf-8')
    msg['From'], msg['Subject'] = Header("AI能源助理", 'utf-8'), Header(title, 'utf-8')
    try:
        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, receivers, msg.as_string())
    except: pass

if __name__ == "__main__":
    bot = AutoStrategy()
    data = bot.analyze()
    if data:
        title = f"💧 能源策略日报 {datetime.now().strftime('%m-%d')}"
        html = bot.generate_html(data)
        send_pushplus(title, html)
        send_email(title, html)
