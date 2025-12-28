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

# ========================= 信仰语录 =========================
QUOTES = [
    "“长江的水，神华的煤，广核的电，茅台的酒。这是中国最硬的物理资产。”",
    "“阿段说：太贵了就不买，哪怕它涨到天上去。错失不是亏损。”",
    "“不要羡慕泡沫，泡沫破裂时，只有我们的水电站还在印钞。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”"
]

# ========================= 十五五 · 金刚配置 =========================
PORTFOLIO_CFG = {
    "600900": {"name": "长江电力","role": "🏔️ 养老基石","dps": 0.95,"strategy": "bond",
               "key_metric": "股息率","other_metrics": ["PE(TTM)", "利差"],
               "mental_check": "它负责兜底。只要跌下来，就是加仓送分题。",
               "report_focus": "关注：来水情况与折旧完结进度。","risk_point": "股息率 < 2.8%"},
    "601088": {"name": "中国神华","role": "⚫️ 能源底座","dps": 2.26,"strategy": "bond",
               "key_metric": "股息率","other_metrics": ["煤价", "长协比"],
               "mental_check": "家里有矿，心中不慌。高位不追，回调加仓。",
               "report_focus": "关注：煤电一体化对冲效果。","risk_point": "股息率 < 5.0%"},
    "601006": {"name": "大秦铁路","role": "🛤️ 国家存折","dps": 0.44,"strategy": "bond",
               "key_metric": "股息率","other_metrics": ["PB", "运量"],
               "mental_check": "这是甚至不需要看K线的股票。把它当成永续债。",
               "report_focus": "关注：大秦线日均运量。","risk_point": "股息率 < 5.5%"},
    "601985": {"name": "中国核电","role": "⚛️ 绿色引擎","dps": 0.17,"strategy": "growth",
               "key_metric": "PE(TTM)","other_metrics": ["PB", "装机量"],
               "mental_check": "还在长身体的孩子。工资定投的首选对象。",
               "report_focus": "关注：新能源装机增速与电价弹性。","risk_point": "PE > 25倍"},
    "600519": {"name": "贵州茅台","role": "👑 A股之王","dps": 30.8,"strategy": "value",
               "key_metric": "PE(TTM)","other_metrics": ["批价", "直销比"],
               "mental_check": "它是社交货币。跌破1400是上帝给的礼物。",
               "report_focus": "关注：i茅台直销占比与提价预期。","risk_point": "PE > 40倍"},
    "000858": {"name": "五粮液","role": "🍷 价值前锋","dps": 4.67,"strategy": "value",
               "key_metric": "PE(TTM)","other_metrics": ["预收款", "动销"],
               "mental_check": "这是翻身仗。110左右极度低估，125以下只买不卖。",
               "report_focus": "关注：合同负债蓄水池深度。","risk_point": "PE > 25倍"},
    "000333": {"name": "美的集团","role": "🤖 全球制造","dps": 3.0,"strategy": "growth",
               "key_metric": "PE(TTM)","other_metrics": ["分红率", "外销比"],
               "mental_check": "代替京沪高铁和紫金，中国制造业巅峰。",
               "report_focus": "关注：B端业务(机器人/楼宇)增速。","risk_point": "PE > 20倍"},
    "601882": {"name": "海天精工","role": "⚙️ 工业母机","dps": 0.5,"strategy": "cyclical",
               "key_metric": "PE(TTM)","other_metrics": ["PB", "订单"],
               "mental_check": "赌中国制造业设备更新红利。",
               "report_focus": "关注：龙门加工中心出口订单。","risk_point": "PE > 30倍"},
    "002415": {"name": "海康威视","role": "📹 智能监控","dps": 0.40,"strategy": "growth",
               "key_metric": "PE(TTM)","other_metrics": ["PB", "营收增速", "毛利率"],
               "mental_check": "专注全球安防与AI增长，估值合理时是长期定投标的。",
               "report_focus": "关注：安防业务增速、海外市场占比及AI视频智能化落地。","risk_point": "PE > 30倍"}
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.bond_yield = 2.10 

    def get_market_status(self):
        month = self.today.month
        msg, color = "📅 资产积累期", "#666"
        if month == 3: msg, color = "🇨🇳 两会/安全月", "#d93025"
        elif month == 4: msg, color = "📊 财报体检期", "#f39c12"
        elif month in [1, 2]: msg, color = "🧧 消费/春运旺季", "#d93025"
        elif month in [6, 7]: msg, color = "💰 分红复投期", "#188038"
        return msg, color

    def get_data(self):
        try:
            print("正在调用 AKShare 接口...")
            df = ak.stock_zh_a_spot_em()
            df['代码'] = df['代码'].astype(str)
            codes = list(self.portfolio.keys())
            return df[df['代码'].isin(codes)].copy()
        except Exception as e:
            print(f"数据获取失败: {e}")
            return None

    def analyze(self):
        df = self.get_data()
        if df is None or df.empty: return None
        results = []
        for _, row in df.iterrows():
            code = row['代码']
            cfg = self.portfolio.get(code)
            
            def clean(val):
                try: return float(val) if val not in ['-', '--', None] else 0.0
                except: return 0.0

            price = clean(row.get('最新价', 0))
            pe = clean(row.get('市盈率-动态', 0))
            pb = clean(row.get('市净率', 0))
            div_yield = (cfg['dps'] / price * 100) if price > 0 else 0

            key_name, key_value, key_color = cfg['key_metric'], "", "#333"
            if key_name == "股息率": key_value, key_color = f"{div_yield:.2f}%", "#d93025" if div_yield > 4.5 else "#333"
            elif key_name == "PB": key_value, key_color = f"{pb}", "#d93025" if pb < 1.3 else "#333"
            elif key_name == "PE(TTM)": key_value, key_color = f"{pe}", "#d93025" if 0 < pe < 16 else "#333"

            tags = []
            for m in cfg.get('other_metrics', []):
                if m == "股息率": tags.append(f"股息:{div_yield:.2f}%")
                elif m == "PE(TTM)": tags.append(f"PE:{pe}")
                elif m == "PB": tags.append(f"PB:{pb}")
                elif m == "利差": tags.append(f"利差:{(div_yield - self.bond_yield):.2f}%")
                elif m == "营收增速": tags.append("营收增速:NA")
                elif m == "毛利率": tags.append("毛利率:NA")
                elif m == "装机量": tags.append(f"核+绿")
                elif m == "批价": tags.append("价稳")
                elif m == "运量": tags.append("运稳")
                elif m == "分红率": tags.append(f"分红率:{div_yield:.2f}%")
                elif m == "外销比": tags.append("外销比:NA")
                elif m == "订单": tags.append("订单:NA")

            signal, color, tip = "🔒 锁仓", "#333", "拒绝诱惑"
            st_type = cfg['strategy']
            if st_type == "bond": 
                if div_yield >= 5.5: signal, color, tip = "🔴 黄金红利", "#d93025", "捡钱"
            elif st_type == "growth": 
                if key_name == "PE(TTM)" and 0 < pe <= 25: 
                    signal, color, tip = "🔴 长线机会", "#d93025", "关注并定投"
            elif st_type == "value": 
                if 0 < pe <= 14: signal, color, tip = "🔴 价值回归", "#d93025", "重仓"

            report_alert = f"<div style='margin-top:5px; color:#d35400; font-size:12px; font-weight:bold;'>📊 研报重点：{cfg['report_focus']}</div>"
            
            results.append({
                "base": {"name": cfg['name'], "role": cfg['role'], "price": price},
                "key": {"name": key_name, "val": key_value, "color": key_color},
                "tags": tags,
                "core": {"signal": signal, "color": color, "tip": tip},
                "mind": {"check": cfg['mental_check'], "alert": report_alert}
            })
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        status_msg, status_color = self.get_market_status()
        html = f"""<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f0f2f5; padding: 15px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 20px; font-weight: 900; color: #1a1a1a; letter-spacing: 1px;">🛡️ 十五五 · 生存资产看板</div>
                <div style="font-size: 12px; color: #888; margin-top: 4px;">{self.today.strftime("%Y-%m-%d %H:%M")} | 上班定投 · 下班收息</div>
                <div style="margin-top: 8px; display: inline-block; background-color: {status_color}; color: white; padding: 3px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">{status_msg}</div>
            </div>
            <div style="background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); color: white; padding: 18px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                <div style="font-size: 14px; font-weight: 400; line-height: 1.6; font-style: italic; opacity: 0.9;">{quote}</div>
            </div>"""
        for item in data:
            base, key, tags, core, mind = item['base'], item['key'], item['tags'], item['core'], item['mind']
            html += f"""
            <div style="background-color: #fff; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #e1e4e8;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div><span style="font-size: 18px; font-weight: 800; color: #111;">{base['name']}</span><span style="font-size: 11px; color: #005bea; background: #e8f4ff; padding: 2px 6px; border-radius: 4px; margin-left: 6px; font-weight: bold;">{base['role']}</span></div>
                    <div style="background-color: {core['color']}; color: white; padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: bold;">{core['signal']}</div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: flex-end; padding-bottom: 12px; border-bottom: 1px dashed #eee;">
                    <div><div style="font-size: 28px; font-weight: 900; color: #000; line-height: 1;">{base['price']}</div><div style="font-size: 11px; color: #aaa; margin-top: 4px;">最新价</div></div>
                    <div style="text-align: right;"><div style="font-size: 22px; font-weight: 800; color: {key['color']}; line-height: 1;">{key['val']}</div><div style="font-size: 11px; color: #aaa; margin-top: 4px;">核心指标: {key['name']}</div></div>
                </div>
                <div style="margin-top: 10px; margin-bottom: 12px;">{''.join([f"<span style='display:inline-block; background:#f5f7f9; color:#47525d; padding:2px 8px; border-radius:4px; font-size:11px; margin-right:5px; margin-bottom:4px; border:1px solid #edf2f7;'>{tag}</span>" for tag in tags])}</div>
                <div style="background-color: #f8faff; border-left: 4px solid #005bea; padding: 10px; border-radius: 6px;">
                    <div style="font-size: 12px; color: #2c3e50; font-weight: 500; line-height: 1.5;">🧠 {mind['check']}</div>{mind['alert']}
                </div>
            </div>"""
        return html + "<div style='text-align:center; color:#bbb; font-size:10px; margin-top:20px;'>🛡️ 十五五生存系统 By AI Strategy</div></div>"

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: 
        print("跳过 PushPlus：Token 未配置")
        return
    tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
    for token in tokens:
        t = token.strip()
        if t:
            try:
                res = requests.post('http://www.pushplus.plus/send', 
                                    json={"token": t, "title": title, "content": content, "template": "html"},
                                    timeout=10)
                print(f"PushPlus 状态: {res.json().get('msg')}")
            except Exception as e:
                print(f"PushPlus 发送异常: {e}")

def send_email(title, content):
    if not SENDER_PASSWORD or not RECEIVER_EMAIL: 
        print("跳过 Email：账号或密码未配置")
        return
    receivers = RECEIVER_EMAIL.replace("，", ",").split(",")
    msg = MIMEText(content, 'html', 'utf-8')
    msg['From'], msg['Subject'] = Header("十五五资产助理", 'utf-8'), Header(title, 'utf-8')
    try:
        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, receivers, msg.as_string())
        s.close()
        print("Email 发送成功")
    except Exception as e:
        print(f"Email 发送失败: {e}")

if __name__ == "__main__":
    bot = AutoStrategy()
    data = bot.analyze()
    if data:
        title = f"🛡️ 生存资产报告 {datetime.now().strftime('%m-%d')}"
        html = bot.generate_html(data)
        send_pushplus(title, html)
        send_email(title, html)
    else:
        print("❌ 数据分析为空，请检查接口或网络")
