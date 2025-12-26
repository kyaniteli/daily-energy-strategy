import akshare as ak
import pandas as pd
import requests
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 环境变量读取 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# ========================= 深度策略配置 (含潜意识训练) =========================
PORTFOLIO_CFG = {
    "601088": {
        "name": "中国神华",
        "role": "🛡️ 绝对防御",
        "target": "40%",
        "dps": 3.245,  # 预期每股分红(需每年4月更新)
        "strategy": "dividend",
        "mental_check": "煤价崩盘了吗？股息率还在6%以上吗？",
        "risk_point": "动力煤期货 < 700元/吨",
        "report_focus": "关注年报中的【分红比例】是否承诺 > 65%"
    },
    "003816": {
        "name": "中国广核",
        "role": "⚓ 长期基石",
        "target": "30%",
        "dps": 0.095,
        "strategy": "growth",
        "mental_check": "出安全事故了吗？没出就死拿。",
        "risk_point": "PB > 2.2倍 (过热)",
        "report_focus": "关注在建机组的【工程进度】是否延期"
    },
    "600406": {
        "name": "国电南瑞",
        "role": "⚔️ 进攻先锋",
        "target": "30%",
        "dps": 0.58,
        "strategy": "tech",
        "mental_check": "电网给钱了吗？现金流是正的吗？",
        "risk_point": "PE > 35倍 (泡沫) / 经营现金流 < 0",
        "report_focus": "必查年报【经营性现金流净额】与净利润的比值"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()

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
        
        # 判断是否是财报季 (通常1月预告，4月年报)
        is_report_season = self.today.month in [1, 4, 8, 10]
        
        for index, row in df.iterrows():
            code = row['代码']
            cfg = self.portfolio.get(code)
            if not cfg: continue
            
            name = cfg['name']
            price = row['最新价']
            pe = row['市盈率-动态']
            pb = row['市净率']
            
            # 计算股息率
            dps = cfg['dps']
            div_yield = (dps / price * 100) if price > 0 else 0
            
            # --- 策略逻辑判定 ---
            signal = "🧘 持有/定投"
            color = "black"
            note = ""

            st_type = cfg['strategy']

            # 神华逻辑
            if st_type == "dividend": 
                if div_yield >= 7.0: 
                    signal, color = "🔴 黄金坑 (捡钱)", "red"
                    note = "股息极高，甚至可加杠杆"
                elif div_yield <= 4.0: 
                    signal, color = "🟢 止盈警戒", "green"
                    note = "性价比不如国债"
            
            # 广核逻辑
            elif st_type == "growth":
                if pb <= 1.45: 
                    signal, color = "🔴 贪婪买入", "red"
                elif pb >= 2.2: 
                    signal, color = "🟢 暂停投入", "green"

            # 南瑞逻辑
            elif st_type == "tech":
                if pe <= 20: 
                    signal, color = "🔴 机会买入", "red"
                    note = "戴维斯双击起点"
                elif pe >= 30: 
                    signal, color = "🟢 泡沫减仓", "green"
                    note = "估值透支"

            # --- 财报季特殊提醒 ---
            report_alert = ""
            if is_report_season:
                report_alert = f"<br><span style='background-color:yellow; color:red; font-weight:bold;'>⚠️ 财报季核查：{cfg['report_focus']}</span>"

            results.append({
                "基础信息": {
                    "name": name, "role": cfg['role'], "price": price, 
                    "pe": pe, "pb": pb, "yield": round(div_yield, 2)
                },
                "核心数据": {
                    "target": cfg['target'], "signal": signal, "color": color, "note": note
                },
                "潜意识训练": {
                    "check": cfg['mental_check'],
                    "risk": cfg['risk_point'],
                    "report": report_alert
                }
            })
            
        return results

    def generate_html(self, data):
        html = """
        <div style="font-family: Arial, sans-serif; max-width: 600px;">
            <h2 style="color: #333;">🛡️ 能源组合每日心法</h2>
            <p style="color: #666; font-size: 14px;">日期：{date} | 状态：监控中</p>
            <hr style="border: 0; border-top: 1px solid #eee;">
        """.format(date=self.today.strftime("%Y-%m-%d"))

        for item in data:
            base = item['基础信息']
            core = item['核心数据']
            mental = item['潜意识训练']
            
            html += f"""
            <div style="background-color: #f9f9f9; padding: 15px; margin-bottom: 15px; border-left: 5px solid {core['color']}; border-radius: 5px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #333;">{base['name']} <span style="font-size: 12px; color: #888;">{base['role']}</span></h3>
                    <span style="font-weight: bold; color: {core['color']};">{core['signal']}</span>
                </div>
                
                <div style="margin-top: 10px; font-size: 14px; color: #555;">
                    <table style="width: 100%;">
                        <tr>
                            <td>现价: <b>{base['price']}</b></td>
                            <td>PE: {base['pe']}</td>
                            <td>股息率: <b>{base['yield']}%</b></td>
                        </tr>
                    </table>
                </div>

                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd; font-size: 13px;">
                    <p style="margin: 5px 0;">🧠 <b>每日一问：</b>{mental['check']}</p>
                    <p style="margin: 5px 0; color: #d9534f;">☠️ <b>死穴监控：</b>{mental['risk']}</p>
                    {mental['report']}
                </div>
            </div>
            """
        
        html += "<p style='font-size:12px; color:gray; text-align:center;'>投资是认知的变现，请知行合一。</p></div>"
        return html

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    url = 'http://www.pushplus.plus/send'
    data = {"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "html"}
    requests.post(url, json=data)

def send_email(title, content):
    if not SENDER_PASSWORD: return
    msg = MIMEText(content, 'html', 'utf-8')
    msg['From'] = Header("AI能源基金", 'utf-8')
    msg['Subject'] = Header(title, 'utf-8')
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    except Exception: pass

if __name__ == "__main__":
    bot = AutoStrategy()
    data = bot.analyze()
    if data:
        title = f"能源日报 {datetime.now().strftime('%m-%d')}"
        html = bot.generate_html(data)
        # 打印简单版到日志以便查看
        for i in data:
            print(f"{i['基础信息']['name']}: {i['核心数据']['signal']} (现价{i['基础信息']['price']})")
        send_pushplus(title, html)
        send_email(title, html)
