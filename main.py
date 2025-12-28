import akshare as ak
import pandas as pd
import requests
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 1. 环境变量 (保留原逻辑) =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ========================= 2. 十五五·生存语录 (升级版) =========================
QUOTES = [
    "“长江的水，神华的煤，广核的电，茅台的酒。这是中国最硬的物理底座。”",
    "“阿段说：太贵了就不买，哪怕它涨到天上去。错失不是亏损。”",
    "“如果你不愿意持有它十年，那就不要持有它一分钟。”",
    "“不要羡慕泡沫，泡沫破裂时，只有分红能让你睡得着觉。”",
    "“守正出奇：守正就是买不倒的垄断公司，出奇是交给时间。”"
]

# ========================= 3. 2026 战略持仓图谱 =========================
PORTFOLIO_CFG = {
    "600900": {
        "name": "长江电力", "role": "🏔️ 养老基石", "dps": 0.95, "strategy": "bond", 
        "key_metric": "股息率", "other_metrics": ["利差:2.1%", "来水"],
        "mental": "它负责兜底。只要跌下来，就是加仓送分题。",
        "report_focus": "关注【乌东德/白鹤滩】折旧与电价波动。", "risk_point": "股息率 < 2.8%"
    },
    "601088": {
        "name": "中国神华", "role": "⚫️ 能源底座", "dps": 2.26, "strategy": "bond",
        "key_metric": "股息率", "other_metrics": ["煤价", "长协比"],
        "mental": "家里有矿，心中不慌。高位不追，回调加仓。",
        "report_focus": "关注【煤电一体化】对冲效果。", "risk_point": "股息率 < 5.0%"
    },
    "601006": {
        "name": "大秦铁路", "role": "🛤️ 国家存折", "dps": 0.44, "strategy": "bond",
        "key_metric": "股息率", "other_metrics": ["PB", "运量"],
        "mental": "这是甚至不需要看K线的股票。把它当成永续债。",
        "report_focus": "关注【大秦线运量】数据。", "risk_point": "股息率 < 5.5%"
    },
    "601985": {
        "name": "中国核电", "role": "⚛️ 绿色引擎", "dps": 0.17, "strategy": "growth",
        "key_metric": "PE(TTM)", "other_metrics": ["ROE", "装机量"],
        "mental": "还在长身体的孩子。工资定投的首选对象。",
        "report_focus": "关注【新能源（风光）】装机增速。", "risk_point": "PE > 25倍"
    },
    "600519": {
        "name": "贵州茅台", "role": "👑 A股之王", "dps": 30.8, "strategy": "value",
        "key_metric": "PE(TTM)", "other_metrics": ["批价", "直销比"],
        "mental": "它是社交货币。跌破1400是上帝给的礼物。",
        "report_focus": "关注【i茅台】直销占比。", "risk_point": "PE > 40倍"
    },
    "000858": {
        "name": "五粮液", "role": "🍷 价值前锋", "dps": 4.67, "strategy": "value",
        "key_metric": "PE(TTM)", "other_metrics": ["批价", "预收款"],
        "mental": "这是翻身仗。110左右极度低估，125以下只买不卖。",
        "report_focus": "关注【合同负债】蓄水池。", "risk_point": "PE > 25倍"
    },
    "000333": {
        "name": "美的集团", "role": "🤖 全球制造", "dps": 3.0, "strategy": "value",
        "key_metric": "PE(TTM)", "other_metrics": ["外销比", "B端增速"],
        "mental": "中国制造的颜面。低估值+高分红+回购注销。",
        "report_focus": "关注【库卡机器人】盈利改善。", "risk_point": "PE > 20倍"
    },
    "601882": {
        "name": "海天精工", "role": "⚙️ 工业母机", "dps": 0.5, "strategy": "cyclical",
        "key_metric": "PE(TTM)", "other_metrics": ["订单", "出口"],
        "mental": "赌中国制造业设备更新红利。",
        "report_focus": "关注【龙门加工中心】订单。", "risk_point": "PE > 30倍"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.bond_yield = 2.10 # 10年期国债收益率基准

    def get_market_status(self):
        month = self.today.month
        msg, color = "📅 常规持仓期", "#666"
        if month == 3: msg, color = "🇨🇳 两会/安全月", "#d93025"
        elif month == 4: msg, color = "📊 财报大考期", "#f39c12"
        elif month in [1, 2]: msg, color = "🧧 消费旺季/春运", "#d93025"
        elif month in [6, 7]: msg, color = "💰 分红复投期", "#188038"
        elif month == 10: msg, color = "🍂 三季报核查", "#f39c12"
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
        status_msg, _ = self.get_market_status()
        
        for _, row in df.iterrows():
            code = row['代码']
            cfg = self.portfolio.get(code)
            price, pe, pb = row['最新价'], row['市盈率-动态'], row['市净率']
            div_yield = (cfg['dps'] / price * 100) if price > 0 else 0
            
            # 核心C位指标逻辑
            key_name, key_value, key_color = cfg['key_metric'], "", "#333"
            if key_name == "股息率":
                key_value = f"{div_yield:.2f}%"
                key_color = "#d93025" if div_yield > 4.5 else "#333"
            else:
                target_val = pe if key_name == "PE(TTM)" else pb
                key_value = f"{target_val}"
                key_color = "#d93025" if (key_name=="PE(TTM)" and pe<15) or (key_name=="PB" and pb<1.2) else "#333"

            # 信号生成
            signal, color, tip = "🔒 锁仓", "#7f8c8d", "耐心是最高的美德"
            st_type = cfg['strategy']
            if st_type == "bond":
                if div_yield >= 5.5: signal, color, tip = "🔴 极佳红利", "#d93025", "捡钱时刻"
            elif st_type == "value":
                if pe <= 13: signal, color, tip = "🔴 价值回归", "#d93025", "黄金坑位"
            elif st_type == "growth":
                if pe <= 18: signal, color, tip = "🟢 定投买入", "#27ae60", "长期布局"

            # 附加标签
            tags = []
            for m in cfg.get('other_metrics', []):
                if "利差" in m: tags.append(f"利差:{(div_yield - self.bond_yield):.2f}%")
                else: tags.append(m)
            tags.append(f"PE:{pe}")

            results.append({
                "name": cfg['name'], "role": cfg['role'], "price": price,
                "key_name": key_name, "key_val": key_value, "key_color": key_color,
                "tags": tags, "signal": signal, "color": color, "tip": tip,
                "mind": cfg['mental'], "report": cfg['report_focus']
            })
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        status_msg, status_color = self.get_market_status()
        
        html = f"""<div style="font-family:'Helvetica Neue', Arial, sans-serif; max-width:600px; margin:0 auto; background:#f4f4f4; padding:20px;">
            <div style="background:#000; color:#fff; padding:20px; border-radius:12px; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.2);">
                <h3 style="margin:0; font-size:22px;">🛡️ 十五五·生存战报</h3>
                <p style="margin:5px 0 0; font-size:12px; opacity:0.8;">{self.today.strftime("%Y-%m-%d")} | <span style="color:{status_color}; font-weight:bold;">{status_msg}</span></p>
            </div>
            <div style="margin:20px 0; background:#fff; padding:15px; border-left:5px solid #d93025; font-style:italic; color:#444; border-radius:4px;">{quote}</div>"""
        
        for item in data:
            tags_html = "".join([f"<span style='background:#eee; padding:2px 6px; border-radius:4px; margin-right:5px; font-size:11px; color:#666;'>{t}</span>" for t in item['tags']])
            html += f"""
            <div style="background:#fff; border-radius:12px; padding:15px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.05); border:1px solid #ddd;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <div style="font-size:18px; font-weight:bold; color:#333;">{item['name']} <span style="font-size:12px; color:#888; font-weight:normal;">{item['role']}</span></div>
                        <div style="margin-top:5px;">{tags_html}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:12px; color:#999;">{item['key_name']}</div>
                        <div style="font-size:20px; font-weight:bold; color:{item['key_color']};">{item['key_val']}</div>
                    </div>
                </div>
                <div style="margin-top:15px; padding:10px; background:#eef6fc; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:14px; font-weight:bold; color:{item['color']};">{item['signal']}</div>
                        <div style="font-size:12px; color:#5d6d7e;">{item['tip']}</div>
                    </div>
                    <div style="text-align:right; font-size:16px; font-weight:bold; color:#2c3e50;">¥{item['price']}</div>
                </div>
                <div style="margin-top:10px; font-size:12px; color:#7f8c8d; line-height:1.5;">
                    <div>🧠 <b>心法：</b>{item['mind']}</div>
                    <div style="color:#d35400; margin-top:3px;">📊 <b>研报关注点：</b>{item['report']}</div>
                </div>
            </div>"""
        
        html += """<div style="text-align:center; color:#999; font-size:12px; margin-top:20px;">Designed by Gemini for Mango</div></div>"""
        return html

    def run(self):
        analysis = self.analyze()
        if analysis:
            html = self.generate_html(analysis)
            # 发送 PushPlus
            if PUSHPLUS_TOKEN:
                requests.post('http://www.pushplus.plus/send', json={"token": PUSHPLUS_TOKEN, "title": f"战术看板 {self.today.strftime('%m-%d')}", "content": html, "template": "html"})
            # 发送 Email (代码逻辑保持不变)
            if SENDER_EMAIL and RECEIVER_EMAIL:
                msg = MIMEText(html, 'html', 'utf-8')
                msg['From'], msg['To'], msg['Subject'] = Header("Mango Investment", 'utf-8'), Header("Owner", 'utf-8'), Header(f"战术看板 {self.today.strftime('%m-%d')}", 'utf-8')
                server = smtplib.SMTP_SSL('smtp.qq.com', 465)
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
                server.quit()
            print("Done.")

if __name__ == "__main__":
    AutoStrategy().run()
