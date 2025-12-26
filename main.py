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

# ========================= 2. 每日信仰语录 =========================
QUOTES = [
    "“巴菲特买了伯灵顿铁路，我们买了京沪高铁。逻辑是一样的：不可替代的物理垄断。”",
    "“阿段说：做对的事情，把事情做对。买垄断的好生意就是对的事。”",
    "“长江的水，大亚湾的核，京沪线的人流。这是中国经济的物理底座。”",
    "“不要去赌技术变化，要买那些100年后人们还在用的东西。”",
    "“定价权是投资的圣杯。京沪高铁和长江电力都有。”",
    "“奥卡姆剃刀：简单的才是最迷人的。这三家公司的生意，连小学生都听得懂。”"
]

# ========================= 3. 终极配置 (带核心指标定义) =========================
PORTFOLIO_CFG = {
    "600900": {
        "name": "长江电力",
        "role": "👑 永续水流 (40%)",
        "dps": 0.95,   
        "strategy": "bond",
        # key_metric: 最核心的指标，会放大显示
        "key_metric": "股息率",
        "other_metrics": ["PE(TTM)", "国债利差"], 
        "mental_check": "长江断流了吗？大坝塌了吗？都没有就睡觉。",
        "report_focus": "年报必看：长江流域来水数据。",
        "risk_point": "股息率 < 2.8% (太贵)"
    },
    "003816": {
        "name": "中国广核",
        "role": "⚓ 能源增量 (30%)",
        "dps": 0.095,
        "strategy": "growth",
        "key_metric": "PB",
        "other_metrics": ["PE(TTM)", "每股净资"],
        "mental_check": "核电是时间的复利，每月定投不要停。",
        "report_focus": "年报必看：新机组核准/投产进度。",
        "risk_point": "PB > 2.3倍"
    },
    "601816": {
        "name": "京沪高铁",
        "role": "🚄 交通垄断 (30%)",
        "dps": 0.13,
        "strategy": "toll",
        "key_metric": "PE(TTM)",
        "other_metrics": ["客座率", "票价"],
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
        msg, color = "📅 坚定持有期", "#555555"
        if month == 3: msg, color = "🇨🇳 两会窗口", "#d93025"
        elif month == 4: msg, color = "📊 年报体检期", "#f39c12"
        elif month in [1, 2]: msg, color = "🧧 春运旺季 (关注高铁)", "#d93025"
        elif month in [6, 7]: msg, color = "💰 分红到账期", "#188038"
        return msg, color

    def get_data(self):
        try:
            print("正在获取数据...")
            df = ak.stock_zh_a_spot_em()
            codes = list(self.portfolio.keys())
            return df[df['代码'].isin(codes)].copy()
        except Exception as e:
            print(f"数据获取失败: {e}")
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
            
            # --- 1. 核心指标处理 (C位展示) ---
            key_name = cfg['key_metric']
            key_value = ""
            key_color = "#333" # 默认黑色
            
            if key_name == "股息率":
                key_value = f"{div_yield:.2f}%"
                key_color = "#d93025" if div_yield > 3.5 else "#333"
            elif key_name == "PB":
                key_value = f"{pb}"
                key_color = "#d93025" if pb < 1.5 else "#333"
            elif key_name == "PE(TTM)":
                key_value = f"{pe}"
                key_color = "#d93025" if pe < 20 else "#333"

            # --- 2. 次要指标处理 (标签展示) ---
            tags = []
            for m in cfg.get('other_metrics', []):
                if m == "股息率": tags.append(f"股息:{div_yield:.2f}%")
                elif m == "PE(TTM)": tags.append(f"PE:{pe}")
                elif m == "PB": tags.append(f"PB:{pb}")
                elif m == "国债利差": tags.append(f"利差:{(div_yield - self.bond_yield):.2f}%")
                elif m == "PEG": tags.append(f"PEG:{(pe/15):.2f}")
                elif m == "客座率": tags.append(f"客流:稳")
                elif m == "票价": tags.append(f"票价:浮动")
                elif m == "每股净资": tags.append(f"净资:{(price/pb):.2f}")

            # --- 3. 信号逻辑 ---
            signal, color, tip = "🔒 锁仓", "#333", "知行合一"
            st_type = cfg['strategy']

            if st_type == "bond": # 长电
                if div_yield >= 4.0: signal, color, tip = "🔴 黄金机会", "#d93025", "可遇不可求"
                elif div_yield <= 2.8: signal, color, tip = "⚪ 略贵勿追", "#999", "底仓不动"
            elif st_type == "growth": # 广核
                if pb <= 1.45: signal, color, tip = "🔴 机会买入", "#d93025", "低估值"
            elif st_type == "toll": # 京沪高铁
                if pe <= 20: signal, color, tip = "🔴 黄金坑", "#d93025", "严重低估"
                elif pe >= 35: signal, color, tip = "🟢 止盈警戒", "#188038", "估值偏高"
            
            report_alert = ""
            status_msg, _ = self.get_market_status()
            if "年报" in status_msg:
                 report_alert = f"<div style='margin-top:5px; color:#d93025; font-size:12px; font-weight:bold;'>⚠️ 财报核查：{cfg['report_focus']}</div>"

            results.append({
                "base": {"name": name, "role": cfg['role'], "price": price},
                "key": {"name": key_name, "val": key_value, "color": key_color},
                "tags": tags,
                "core": {"signal": signal, "color": color, "tip": tip},
                "mind": {"check": cfg['mental_check'], "alert": report_alert}
            })
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        status_msg, status_color = self.get_market_status()
        
        # 头部样式
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f0f2f5; padding: 12px;">
            <div style="text-align: center; margin-bottom: 15px;">
                <div style="font-size: 18px; font-weight: 800; color: #1a1a1a;">🚄 物理垄断铁三角</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">{self.today.strftime("%Y-%m-%d %H:%M")}</div>
                <div style="margin-top: 8px; display: inline-block; background-color: {status_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">{status_msg}</div>
            </div>
            
            <div style="background: linear-gradient(135deg, #005bea 0%, #00c6fb 100%); color: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,91,234,0.3);">
                <div style="font-size: 15px; font-weight: 500; line-height: 1.5; font-style: italic;">{quote}</div>
            </div>
        """

        for item in data:
            base, key, tags, core, mind = item['base'], item['key'], item['tags'], item['core'], item['mind']
            
            # 标签生成
            tags_html = ""
            for tag in tags:
                tags_html += f"<span style='display:inline-block; background:#e4e6eb; color:#333; padding:2px 6px; border-radius:4px; font-size:12px; margin-right:5px; margin-bottom:4px;'>{tag}</span>"

            html += f"""
            <div style="background-color: #fff; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #e1e4e8;">
                
                <!-- 顶部：名称 + 信号 -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <span style="font-size: 18px; font-weight: 800; color: #000;">{base['name']}</span>
                        <span style="font-size: 12px; color: #666; background: #f0f0f0; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">{base['role']}</span>
                    </div>
                    <div style="background-color: {core['color']}; color: white; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold;">
                        {core['signal']}
                    </div>
                </div>

                <!-- 核心数据区 -->
                <div style="display: flex; justify-content: space-between; align-items: flex-end; padding-bottom: 12px; border-bottom: 1px solid #eee;">
                    <div>
                        <div style="font-size: 32px; font-weight: 900; color: #000; line-height: 1;">{base['price']}</div>
                        <div style="font-size: 12px; color: #888; margin-top: 4px;">最新价格</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 24px; font-weight: 800; color: {key['color']}; line-height: 1;">{key['val']}</div>
                        <div style="font-size: 12px; color: #888; margin-top: 4px;">核心指标: {key['name']}</div>
                    </div>
                </div>

                <!-- 次要指标 -->
                <div style="margin-top: 10px; margin-bottom: 12px;">
                    {tags_html}
                </div>
                
                <!-- 潜意识训练区 (加深对比度) -->
                <div style="background-color: #f1f8ff; border-left: 4px solid #005bea; padding: 10px; border-radius: 4px;">
                    <div style="font-size: 13px; color: #2c3e50; font-weight: 600; line-height: 1.4;">
                        🧠 {mind['check']}
                    </div>
                    {mind['alert']}
                </div>
            </div>"""
            
        html += """<div style='text-align: center; margin-top: 20px; font-size: 12px; color: #999;'><p>Simple. Safe. Certain.</p></div></div>"""
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
        title = f"🚄 铁三角日报 {datetime.now().strftime('%m-%d')}"
        html = bot.generate_html(data)
        send_pushplus(title, html)
        send_email(title, html)
        print("✅ 增强版发送完毕")
