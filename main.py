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

# ========================= 1. 信仰语录库 (每日随机) =========================
QUOTES = [
    "“股市在短期是投票机，在长期是称重机。” —— 本杰明·格雷厄姆",
    "“如果你不愿意持有一只股票十年，由于你就不要持有它十分钟。” —— 巴菲特",
    "“投资的本质是买这门生意的未来现金流。” —— 段永平",
    "“别人贪婪我恐惧，别人恐惧我贪婪。” —— 巴菲特",
    "“原本甚至能赚 500% 的交易，最后亏钱离场，往往是因为那个‘波段操作’的念头。” —— 费雪",
    "“不要亏钱。不要亏钱。不要亏钱。” —— 投资第一原则",
    "“好公司，好价格，长期持有。难的是‘长期’二字。”",
    "“股价下跌是市场在给你打折，你应该高兴才对。” —— 彼得·林奇",
    "“最困难的事情是什么都不做（坐得住）。”",
    "“我们买的是电厂和电网的股权，不是代码。”",
    "“每天盯盘的人，最终都给券商打工了。”",
    "“反脆弱：火电对冲干旱，核电对冲通胀，电网对冲波动。”"
]

# ========================= 2. 深度配置表 =========================
PORTFOLIO_CFG = {
    "601088": {
        "name": "中国神华",
        "role": "🛡️ 现金奶牛",
        "target": "40%",
        "dps": 3.245,  # 预期分红(元)
        "strategy": "value",
        # 定制展示指标：
        "metrics": ["PE(TTM)", "股息率", "国债利差"], 
        "mental_check": "煤价只要不腰斩，这就是印钞机。",
        "report_focus": "年报必看：分红比例是否 > 65%？"
    },
    "003816": {
        "name": "中国广核",
        "role": "⚓ 养老基石",
        "target": "30%",
        "dps": 0.095,
        "strategy": "growth",
        "metrics": ["PB", "PE(TTM)", "每股净资"],
        "mental_check": "核电建设周期是5年，请保持耐心。",
        "report_focus": "年报必看：新机组核准和投产进度。"
    },
    "600406": {
        "name": "国电南瑞",
        "role": "⚔️ 科技进攻",
        "target": "30%",
        "dps": 0.58,
        "strategy": "tech",
        "metrics": ["PE(TTM)", "PEG(预)", "ROE"],
        "mental_check": "AI 越发展，电网调度越重要。",
        "report_focus": "年报必看：经营性现金流净额是否转正？"
    },
    "600900": {
        "name": "长江电力",
        "role": "👀 静待时机",
        "target": "观察",
        "dps": 0.95,
        "strategy": "bond",
        "metrics": ["股息率", "PE(TTM)", "来水"],
        "mental_check": "等它跌下来，我就把神华换成它。",
        "report_focus": "关注长江流域来水数据。"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.action_count = 0
        self.bond_yield = 2.10 # 假设10年期国债收益率，用于计算利差

    def get_market_status(self):
        """获取当前的时间窗口（日历提醒）"""
        month = self.today.month
        msg = "📅 常规交易期"
        color = "#666"
        
        if month == 3:
            msg = "🇨🇳 两会窗口期 (关注能源政策/电网投资)"
            color = "#d93025"
        elif month == 4:
            msg = "📊 年报/一季报密集披露 (必查现金流/分红)"
            color = "#f39c12"
        elif month in [6, 7]:
            msg = "💰 分红实施窗口 (注意除权/填权)"
            color = "#188038"
        elif month == 10:
            msg = "📊 三季报窗口 (关注全年业绩预告)"
            color = "#f39c12"
        elif month == 12:
            msg = "❄️ 冬季保供期 (关注煤价/火电负荷)"
            color = "#3498db"
            
        return msg, color

    def get_data(self):
        try:
            df = ak.stock_zh_a_spot_em()
            codes = list(self.portfolio.keys())
            subset = df[df['代码'].isin(codes)].copy()
            return subset
        except Exception:
            return None

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
            pb = row['市净率']
            
            # 基础计算
            dps = cfg['dps']
            div_yield = (dps / price * 100) if price > 0 else 0
            
            # --- 个性化指标展示逻辑 ---
            extra_info = []
            metrics_list = cfg.get('metrics', [])
            
            for m in metrics_list:
                if m == "股息率":
                    extra_info.append(f"股息: <b>{div_yield:.2f}%</b>")
                elif m == "PE(TTM)":
                    extra_info.append(f"PE: {pe}")
                elif m == "PB":
                    extra_info.append(f"PB: {pb}")
                elif m == "国债利差":
                    spread = div_yield - self.bond_yield
                    extra_info.append(f"利差: <b>+{spread:.2f}%</b>")
                elif m == "PEG(预)":
                    # 简单估算：假设南瑞增长15%
                    peg = pe / 15 
                    extra_info.append(f"PEG: {peg:.2f}")
                elif m == "每股净资":
                    bps = price / pb if pb > 0 else 0
                    extra_info.append(f"净资: {bps:.2f}")
                elif m == "ROE":
                    # 简单估算
                    roe = (pb / pe * 100) if pe > 0 else 0
                    extra_info.append(f"ROE: {roe:.1f}%")
            
            extra_str = " | ".join(extra_info)

            # --- 信号判断 (保持之前的严谨逻辑) ---
            signal, color, tip = "🧘 持有/定投", "#333", "积累筹码"
            st_type = cfg['strategy']

            if st_type == "value": # 神华
                if div_yield >= 7.0: 
                    signal, color, tip = "🔴 强力买入", "#d93025", "股息率极具吸引力"
                    self.action_count += 1
                elif div_yield <= 4.0: 
                    signal, color, tip = "🟢 止盈警戒", "#188038", "性价比下降"
            elif st_type == "growth": # 广核
                if pb <= 1.45: 
                    signal, color, tip = "🔴 机会买入", "#d93025", "低估值区间"
                    self.action_count += 1
                elif pb >= 2.2: 
                    signal, color, tip = "🟢 暂停定投", "#188038", "估值偏高"
            elif st_type == "tech": # 南瑞
                if pe <= 20: 
                    signal, color, tip = "🔴 黄金坑", "#d93025", "错杀机会"
                    self.action_count += 1
                elif pe >= 30: 
                    signal, color, tip = "🟢 泡沫止盈", "#188038", "透支未来"
            
            # 财报季提醒
            status_msg, _ = self.get_market_status()
            report_alert = ""
            if "年报" in status_msg or "季报" in status_msg:
                 report_alert = f"<div style='margin-top:5px; color:#d35400; font-size:12px; font-weight:bold;'>⚠️ 财报核查：{cfg['report_focus']}</div>"

            results.append({
                "base": {"name": name, "role": cfg['role'], "price": price},
                "core": {"signal": signal, "color": color, "tip": tip, "data_str": extra_str},
                "mind": {"check": cfg['mental_check'], "alert": report_alert}
            })
            
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        status_msg, status_color = self.get_market_status()
        
        # 头部：日期 + 投资日历
        html = f"""
        <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f4f6f9; padding: 15px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 18px; font-weight: bold; color: #2c3e50;">⚡ AI 能源组合日报</div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">{self.today.strftime("%Y-%m-%d %H:%M")}</div>
                <div style="margin-top: 8px; display: inline-block; background-color: {status_color}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">
                    {status_msg}
                </div>
            </div>

            <!-- 每日信仰 -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; font-style: italic; line-height: 1.5;">{quote}</div>
            </div>
        """

        # 个股卡片
        for item in data:
            base, core, mind = item['base'], item['core'], item['mind']
            
            # 卡片背景色：如果有买入信号，稍微泛红
            card_bg = "#ffffff"
            if "买入" in core['signal'] or "黄金坑" in core['signal']:
                card_bg = "#fff5f5" # 浅红背景提示机会

            html += f"""
            <div style="background-color: {card_bg}; border-radius: 10px; padding: 15px; margin-bottom: 15px; border: 1px solid #e1e4e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <!-- 抬头：名称 + 信号 -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>
                        <span style="font-size: 16px; font-weight: bold; color: #2c3e50;">{base['name']}</span>
                        <span style="font-size: 12px; color: #95a5a6; margin-left: 5px;">{base['role']}</span>
                    </div>
                    <div style="background-color: {core['color']}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                        {core['signal']}
                    </div>
                </div>

                <!-- 数据区：价格 + 个性化指标 -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">{base['price']}</div>
                    <div style="font-size: 12px; color: #7f8c8d; text-align: right; line-height: 1.6;">
                        {core['data_str']}
                    </div>
                </div>
                
                <!-- 提示区 -->
                <div style="font-size: 12px; color: {core['color']}; margin-bottom: 8px; font-weight: bold;">
                    💡 策略提示：{core['tip']}
                </div>

                <!-- 潜意识训练区 -->
                <div style="background-color: #f8f9fa; border-left: 3px solid #bdc3c7; padding: 8px; font-size: 12px; color: #555;">
                    <div>🧠 <b>潜意识：</b>{mind['check']}</div>
                    {mind['alert']}
                </div>
            </div>
            """

        html += """
            <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #95a5a6;">
                <p>Stay Rational. Stay Invested.</p>
            </div>
        </div>
        """
        return html

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
    for token in tokens:
        if not token.strip(): continue
        try:
            requests.post('http://www.pushplus.plus/send', json={"token": token.strip(), "title": title, "content": content, "template": "html"})
        except: pass

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
        title = f"⚡ 能源策略日报 {datetime.now().strftime('%m-%d')}"
        html = bot.generate_html(data)
        send_pushplus(title, html)
        send_email(title, html)
        print("✅ 深度日报已发送")
