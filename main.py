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

# ========================= 每日信仰语录 (物理垄断版) =========================
QUOTES = [
    "“巴菲特买了铁路(BNSF)，我们买了京沪高铁。逻辑是一样的：不可替代。”",
    "“阿段说：做对的事情，把事情做对。买垄断的好生意就是对的事。”",
    "“长江的水，大亚湾的核，京沪线的人流。这是中国经济的物理底座。”",
    "“不要去赌技术变化，要买那些100年后人们还在用的东西。”",
    "“定价权是投资的圣杯。京沪高铁和长江电力都有。”",
    "“简单就是美。这三家公司的生意，连小学生都听得懂。”"
]

# ========================= 大师级铁三角配置 =========================
PORTFOLIO_CFG = {
    "600900": {
        "name": "长江电力",
        "role": "👑 永续水流 (40%)",
        "dps": 0.95,   
        "strategy": "bond",
        "metrics": ["股息率", "PE(TTM)", "国债利差"], 
        "mental_check": "长江断流了吗？大坝还在吗？在就睡觉。",
        "report_focus": "年报必看：长江流域来水数据。",
        "risk_point": "股息率 < 2.8% (太贵)"
    },
    "003816": {
        "name": "中国广核",
        "role": "⚓ 能源增量 (30%)",
        "dps": 0.095,
        "strategy": "growth",
        "metrics": ["PB", "PE(TTM)", "每股净资"],
        "mental_check": "核电是时间的复利，每月定投不要停。",
        "report_focus": "年报必看：新机组核准/投产进度。",
        "risk_point": "PB > 2.3倍"
    },
    "601816": {
        "name": "京沪高铁",
        "role": "🚄 交通垄断 (30%)", # 替换南瑞
        "dps": 0.13, # 假设分红
        "strategy": "toll", # 收费站策略
        "metrics": ["PE(TTM)", "客座率", "票价"],
        "mental_check": "北京和上海之间，还有比高铁更好的交通方式吗？",
        "report_focus": "年报必看：本线客运量 & 票价调整。",
        "risk_point": "经济大萧条导致商务出行崩盘"
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
        if month == 3: msg, color = "🇨🇳 两会窗口", "#d93025"
        elif month == 4: msg, color = "📊 年报体检期", "#f39c12"
        elif month in [1, 2]: msg, color = "🧧 春运旺季 (关注高铁)", "#d93025"
        elif month in [6, 7]: msg, color = "💰 分红到账期", "#188038"
        return msg, color

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
                elif m == "客座率": extra_info.append(f"客流: 稳")
                elif m == "票价": extra_info.append(f"票价: 浮动")
            extra_str = " | ".join(extra_info)

            signal, color, tip = "🧘 锁仓持有", "#333", "积累股份"
            st_type = cfg['strategy']

            if st_type == "bond": # 长电
                if div_yield >= 4.0: signal, color, tip = "🔴 黄金机会", "#d93025", "可遇不可求"
            elif st_type == "growth": # 广核
                if pb <= 1.45: signal, color, tip = "🔴 机会买入", "#d93025", "低估值"
            elif st_type == "toll": # 京沪高铁
                # 击球区：PE < 20倍
                if pe <= 20: signal, color, tip = "🔴 黄金坑", "#d93025", "严重低估"
                elif pe >= 35: signal, color, tip = "🟢 止盈警戒", "#188038", "估值偏高"
            
            report_alert = ""
            status_msg, _ = self.get_market_status()
            if "年报" in status_msg:
                 report_alert = f"<div style='margin-top:5px; color:#d35400; font-size:12px; font-weight:bold;'>⚠️ 财报核查：{cfg['report_focus']}</div>"

            results.append({"base": {"name": name, "role": cfg['role'], "price": price}, "core": {"signal": signal, "color": color, "tip": tip, "data_str": extra_str}, "mind": {"check": cfg['mental_check'], "alert": report_alert}})
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        status_msg, status_color = self.get_market_status()
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f4f6f9; padding: 15px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 18px; font-weight: bold; color: #2c3e50;">🚄 物理垄断铁三角日报</div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">{self.today.strftime("%Y-%m-%d %H:%M")}</div>
                <div style="margin-top: 8px; display: inline-block; background-color: {status_color}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">{status_msg}</div>
            </div>
            <div style="background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                <div style="font-size: 14px; font-style: italic;">{quote}</div>
            </div>"""
        for item in data:
            base, core, mind = item['base'], item['core'], item['mind']
            card_bg = "#fff5f5" if "买入" in core['signal'] or "黄金" in core['signal'] else "#ffffff"
            html += f"""
            <div style="background-color: {card_bg}; border-radius: 10px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div><span style="font-weight: bold;">{base['name']}</span> <span style="font-size: 12px; color: #999;">{base['role']}</span></div>
                    <div style="color: {core['color']}; font-weight: bold; font-size: 12px;">{core['signal']}</div>
                </div>
                <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">{base['price']} <span style="font-size: 12px; color: #7f8c8d; font-weight: normal;">{core['data_str']}</span></div>
                <div style="background: #f8f9fa; padding: 8px; font-size: 12px; border-left: 3px solid #ccc;">🧠 <b>潜意识：</b>{mind['check']}</div>
                {mind['alert']}
            </div>"""
        return html + "</div>"

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
        title = f"🚄 铁三角日报 {datetime.now().strftime('%m-%d')}"
        html = bot.generate_html(data)
        send_pushplus(title, html)
        send_email(title, html)
        print("✅ 终极版执行完毕")
