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
    "“奥卡姆剃刀：如无必要，勿增实体。水、核、网，足矣。”",
    "“长江电力不是股票，它是上帝发行的永续债券。”",
    "“我们卖出了煤炭的周期，买入了流水的永恒。”",
    "“南瑞是电网的大脑，广核是电网的心脏，长电是电网的血液。”",
    "“不预测煤价，不预测风光。只相信物理常识。”",
    "“每天盯着股价看，不如去江边看看水流，它每秒都在为你赚钱。”",
    "“在这个不确定的世界里，垄断且必须的基荷能源是唯一的确定性。”"
]

# ========================= 铁三角配置 =========================
PORTFOLIO_CFG = {
    "600900": {
        "name": "长江电力", "role": "👑 永续水流 (40%)", "dps": 0.95, "strategy": "bond",
        "metrics": ["股息率", "PE(TTM)", "国债利差"],
        "mental_check": "长江断流了吗？没断就睡觉。", "report_focus": "年报必看：长江流域来水数据。"
    },
    "003816": {
        "name": "中国广核", "role": "⚓ 原子基石 (30%)", "dps": 0.095, "strategy": "growth",
        "metrics": ["PB", "PE(TTM)", "每股净资"],
        "mental_check": "没出核事故吧？那就继续拿着当养老金。", "report_focus": "年报必看：新机组核准进度。"
    },
    "600406": {
        "name": "国电南瑞", "role": "⚔️ 电网大脑 (30%)", "dps": 0.58, "strategy": "tech",
        "metrics": ["PE(TTM)", "PEG", "ROE"],
        "mental_check": "AI 只要还用电，就需要南瑞来调度。", "report_focus": "年报必看：经营性现金流。"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.bond_yield = 2.10 

    def get_market_status(self):
        month = self.today.month
        msg, color = "📅 坚定持有期", "#666"
        if month == 3: msg, color = "🇨🇳 两会/十五五规划窗口", "#d93025"
        elif month == 4: msg, color = "📊 年报体检期", "#f39c12"
        elif month in [6, 7]: msg, color = "💰 分红季", "#188038"
        return msg, color

    def get_data(self):
        try:
            print("正在获取数据...")
            df = ak.stock_zh_a_spot_em()
            codes = list(self.portfolio.keys())
            return df[df['代码'].isin(codes)].copy()
        except Exception as e:
            print(f"数据获取错误: {e}")
            return None

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
            
            extra_info = []
            for m in cfg.get('metrics', []):
                if m == "股息率": extra_info.append(f"股息: <b>{div_yield:.2f}%</b>")
                elif m == "PE(TTM)": extra_info.append(f"PE: {pe}")
                elif m == "PB": extra_info.append(f"PB: {pb}")
                elif m == "国债利差": extra_info.append(f"利差: <b>+{(div_yield - self.bond_yield):.2f}%</b>")
                elif m == "PEG": extra_info.append(f"PEG: {(pe/15):.2f}")
            extra_str = " | ".join(extra_info)

            signal, color, tip = "🧘 锁仓持有", "#333", "知行合一"
            st_type = cfg['strategy']

            if st_type == "bond": 
                if div_yield >= 4.0: signal, color, tip = "🔴 黄金机会", "#d93025", "可遇不可求"
            elif st_type == "growth":
                if pb <= 1.45: signal, color, tip = "🔴 机会买入", "#d93025", "低估值"
            elif st_type == "tech":
                if pe <= 20: signal, color, tip = "🔴 黄金坑", "#d93025", "严重错杀"
            
            results.append({"base": {"name": name, "role": cfg['role'], "price": price}, "core": {"signal": signal, "color": color, "tip": tip, "data_str": extra_str}, "mind": {"check": cfg['mental_check'], "alert": ""}})
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        status_msg, status_color = self.get_market_status()
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f4f6f9; padding: 15px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 18px; font-weight: bold; color: #2c3e50;">⛰️ 铁三角 · 能源日报</div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">{self.today.strftime("%Y-%m-%d %H:%M")}</div>
            </div>
            <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <div style="font-size: 14px; font-style: italic;">{quote}</div>
            </div>"""
        for item in data:
            base, core, mind = item['base'], item['core'], item['mind']
            html += f"""
            <div style="background-color: #fff; border-radius: 10px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div><span style="font-weight: bold;">{base['name']}</span> <span style="font-size: 12px; color: #999;">{base['role']}</span></div>
                    <div style="color: {core['color']}; font-weight: bold; font-size: 12px;">{core['signal']}</div>
                </div>
                <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">{base['price']} <span style="font-size: 12px; color: #7f8c8d; font-weight: normal;">{core['data_str']}</span></div>
                <div style="background: #f8f9fa; padding: 8px; font-size: 12px; border-left: 3px solid #ccc;">🧠 <b>潜意识：</b>{mind['check']}</div>
            </div>"""
        return html + "</div>"

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: 
        print("❌ 未检测到 PUSHPLUS_TOKEN")
        return
    # === 关键修正：处理逗号分隔的多Token ===
    tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
    print(f"检测到 {len(tokens)} 个接收者")
    
    for token in tokens:
        token = token.strip()
        if not token: continue
        try:
            url = 'http://www.pushplus.plus/send'
            data = {"token": token, "title": title, "content": content, "template": "html"}
            resp = requests.post(url, json=data)
            print(f"✅ 发送给 {token[:4]}... 结果: {resp.text}")
        except Exception as e:
            print(f"❌ 发送失败: {e}")

def send_email(title, content):
    if not SENDER_PASSWORD or not RECEIVER_EMAIL: return
    # === 关键修正：处理逗号分隔的多邮箱 ===
    receivers = RECEIVER_EMAIL.replace("，", ",").split(",")
    receivers = [r.strip() for r in receivers if r.strip()]
    
    msg = MIMEText(content, 'html', 'utf-8')
    msg['From'] = Header("AI能源助理", 'utf-8')
    msg['Subject'] = Header(title, 'utf-8')
    try:
        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, receivers, msg.as_string())
        print(f"✅ 邮件已发给 {len(receivers)} 人")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

if __name__ == "__main__":
    bot = AutoStrategy()
    data = bot.analyze()
    if data:
        title = f"⛰️ 铁三角日报 {datetime.now().strftime('%m-%d')}"
        html = bot.generate_html(data)
        send_pushplus(title, html)
        send_email(title, html)
        print("执行结束")
