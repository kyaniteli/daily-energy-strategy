import akshare as ak
import pandas as pd
import requests
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 1. 环境变量 (保留原版配置) =========================
# 您不需要修改代码，继续使用您服务器/本地的环境变量配置即可
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ========================= 2. 语录库 (十五五·生存版) =========================
QUOTES = [
    "“宁可错过紫金的暴涨，也不要在高位站岗。手里有现金，心中不慌。”",
    "“大秦铁路不是股票，它是你的一本每年发 6% 利息的存折。”",
    "“五粮液跌下来是送钱，涨上去是送心跳。只有在没人的时候买，才能在人多的时候卖。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“如果你不愿意持有它十年，那就不要持有它十分钟。”",
    "“十五五期间，活得久比赚得多更重要。”"
]

# ========================= 3. 战术配置地图 (2026 终极版) =========================
PORTFOLIO_CFG = {
    # -------- 核心四角堡垒 --------
    "000858": {
        "name": "五粮液",
        "role": "🍷 主力 (25%)",
        "buy_price": 115.0,     # 黄金坑红线
        "key_metric": "PE < 15",
        "time_nodes": "🧧春节备货: 1月 | 💰分红: 6月",
        "report_focus": "关注【合同负债】蓄水池，关注【批发价】是否坚挺。",
        "mental": "这是翻身仗。110左右是极度低估，125以下只买不卖。",
        "action": "现价极具吸引力，优先配置，博取估值修复。"
    },
    "601006": {
        "name": "大秦铁路",
        "role": "🛤️ 存折 (30%)",
        "buy_zone_pb": 0.8,
        "key_metric": "股息率 > 5%",
        "time_nodes": "💰分红季: 7月 | ⚠️检修: 4月/10月",
        "report_focus": "关注【运量】数据，关注【分红率】是否维持高位。",
        "mental": "这是保命钱。把它当成永续债，价格越低，利息越高。",
        "action": "地板价，直接填满底仓，不要看K线。"
    },
    "601088": {
        "name": "中国神华",
        "role": "⚫️ 底座 (25%)",
        "buy_zone_pb": 1.2,
        "key_metric": "股息率 > 6%",
        "time_nodes": "❄️冬储: 12-1月 | ☀️迎峰度夏: 7-8月",
        "report_focus": "关注【煤炭成本】与【发电利润】的对冲效果。",
        "mental": "家里有矿，心中不慌。高位不追，回调加仓。",
        "action": "挂单在 -2% 到 -5% 的位置分批接货。"
    },
    "601985": {
        "name": "中国核电",
        "role": "⚛️ 引擎 (20%)",
        "buy_zone_pe": 18.0,
        "key_metric": "装机增速",
        "time_nodes": "🏗️新机组核准: 不定期",
        "report_focus": "关注【新能源装机】增速，关注【核电利用小时】。",
        "mental": "它是还在长身体的孩子。工资定投的首选对象。",
        "action": "无脑定投。利用工资结余，每月买一点。"
    },

    # -------- 观察清单 (卫星/备选) --------
    "601398": {
        "name": "工商银行",
        "role": "🏦 备胎",
        "buy_zone_pb": 0.55,
        "key_metric": "PB < 0.5",
        "mental": "如果大秦或者神华太贵，就买工行替代。",
        "action": "超级防守，随时可买。"
    },
    "600519": {
        "name": "贵州茅台",
        "role": "👑 股王",
        "buy_price": 1350.0,
        "key_metric": "批价",
        "mental": "如果跌破1350，砸锅卖铁也要买。",
        "action": "极度稀缺，保持关注。"
    },
    "000333": {
        "name": "美的集团",
        "role": "🤖 制造",
        "buy_zone_pe": 11.0,
        "key_metric": "海外营收",
        "mental": "中国制造的颜面。低估时可替代五粮液。",
        "action": "分红回购大户，稳健之选。"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()

    def get_data(self):
        try:
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
            
            name = cfg['name']
            price = row['最新价']
            pe = row['市盈率-动态']
            pb = row['市净率']
            change_pct = row['涨跌幅']
            
            # 数据清洗
            try: pe = float(pe)
            except: pe = 999.0
            try: pb = float(pb)
            except: pb = 999.0

            # --- 智能战术分析逻辑 ---
            signal = "🔒 持仓"
            color = "#95a5a6" # 默认灰
            tip = "价格在合理区间，按兵不动。"

            # 1. 五粮液战术 (绝对价格狙击)
            if code == "000858":
                if price < 115:
                    signal = "🔥 黄金坑"
                    color = "#c0392b" # 深红
                    tip = f"现价 {price}！低于115元，优先把子弹打这里！"
                elif price > 130:
                    signal = "🛑 观望"
                    color = "#e67e22"
                    tip = "脱离底部，停止追高。"

            # 2. 神华/大秦战术 (PB与红利)
            elif code in ["601088", "601006"]:
                target_pb = cfg.get('buy_zone_pb', 1.0)
                if pb < target_pb:
                    signal = "💎 捡钱"
                    color = "#27ae60" # 深绿
                    tip = f"PB仅 {pb}，处于低估区，填满底仓。"
                elif pb > target_pb * 1.3:
                    signal = "⚠️ 略贵"
                    color = "#f39c12"
                    tip = "估值偏高，不要一次买完，挂单低吸。"

            # 3. 核电/茅台/美的战术 (PE与定投)
            elif code in ["601985", "600519", "000333"]:
                target_pe = cfg.get('buy_zone_pe', 20)
                if code == "600519" and price < cfg['buy_price']:
                    signal = "👑 抄底"
                    color = "#d4af37"
                    tip = "茅台跌破心理价位，机会难得。"
                elif pe < target_pe:
                    signal = "🟢 定投"
                    color = "#2ecc71"
                    tip = "估值合理，适合工资结余定投。"

            # 暴跌加仓提示
            if change_pct < -3:
                tip += " 【今日大跌，适合加仓！】"
                color = "#c0392b"

            results.append({
                "name": name, "role": cfg['role'], "price": price, "change": change_pct,
                "pe": pe, "pb": pb, "signal": signal, "color": color, "tip": tip,
                "mental": cfg['mental'], "key_metric": cfg['key_metric'],
                "time_nodes": cfg.get('time_nodes', ''), "report_focus": cfg.get('report_focus', '')
            })
        
        # 排序：五粮液优先展示
        results.sort(key=lambda x: x['name'] != "五粮液")
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        
        html = f"""
        <div style="font-family:'Helvetica Neue', sans-serif;max-width:600px;margin:0 auto;background:#f0f2f5;padding:15px;">
        <div style="background:#2c3e50;color:#fff;padding:20px;border-radius:10px;text-align:center;box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            <h2 style="margin:0;font-size:20px;">🛡️ 十五五·生存战报</h2>
            <p style="margin:5px 0 0;font-size:12px;opacity:0.8;">{self.today.strftime("%Y-%m-%d %H:%M")}</p>
        </div>
        <div style="margin:15px 0;background:#fff;padding:12px;border-left:4px solid #e74c3c;font-size:14px;color:#555;border-radius:4px;">{quote}</div>
        """
        
        for item in data:
            change_color = "red" if item['change'] > 0 else "green"
            change_sign = "+" if item['change'] > 0 else ""
            
            html += f"""
            <div style="background:#fff;margin-bottom:15px;border-radius:8px;overflow:hidden;box-shadow:0 2px 5px rgba(0,0,0,0.05);">
                <div style="padding:12px;border-bottom:1px solid #eee;display:flex;justify_content:space-between;align-items:center;">
                    <div><strong style="font-size:16px;color:#333;">{item['name']}</strong><span style="font-size:12px;background:#eee;color:#666;padding:2px 5px;border-radius:3px;margin-left:5px;">{item['role']}</span></div>
                    <div style="text-align:right;"><div style="font-size:16px;font-weight:bold;">¥{item['price']}</div><div style="font-size:12px;color:{change_color};">{change_sign}{item['change']}%</div></div>
                </div>
                <div style="padding:12px;display:flex;background:#fafafa;">
                    <div style="flex:1;"><div style="font-size:12px;color:#999;">核心指标</div><div style="font-weight:bold;color:#333;">{item['key_metric']}</div><div style="font-size:11px;color:#666;">PE:{item['pe']} | PB:{item['pb']}</div></div>
                    <div style="text-align:center;"><span style="background:{item['color']};color:#fff;padding:5px 10px;border-radius:15px;font-size:12px;font-weight:bold;">{item['signal']}</span></div>
                </div>
                <div style="padding:12px;border-top:1px solid #eee;">
                    <div style="font-size:12px;color:#e67e22;margin-bottom:4px;">📅 {item['time_nodes']}</div>
                    <div style="background:#e8f4fd;color:#2c3e50;padding:10px;border-radius:5px;font-size:13px;"><strong>👉 行动指令：</strong><br>{item['tip']}</div>
                    <div style="margin-top:8px;font-size:12px;color:#7f8c8d;">💡 心法：{item['mental']}</div>
                </div>
            </div>
            """
        html += "</div>"
        return html

# ========================= 4. 推送服务 (保留原版配置) =========================
def send_pushplus(content):
    if not PUSHPLUS_TOKEN: return
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"股市策略日报 {datetime.now().strftime('%m-%d')}",
        "content": content,
        "template": "html"
    }
    requests.post(url, json=data)

def send_email(content):
    if not SENDER_EMAIL or not SENDER_PASSWORD: return
    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = Header(f"股市策略日报 {datetime.now().strftime('%m-%d')}", 'utf-8')
    msg['From'] = Header("Gemini", 'utf-8')
    msg['To'] = RECEIVER_EMAIL
    try:
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
    except: pass

if __name__ == "__main__":
    strategy = AutoStrategy()
    report = strategy.run()
    if report:
        if PUSHPLUS_TOKEN: send_pushplus(report)
        if SENDER_EMAIL: send_email(report)
        print("策略已生成并推送")
