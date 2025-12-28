import akshare as ak
import pandas as pd
import requests
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 1. 环境变量 (保留原配置) =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ========================= 2. 语录库 (十五五·生存版) =========================
QUOTES = [
    "“宁可错过紫金的暴涨，也不要在高位站岗。手里有现金，心中不慌。”",
    "“长江电力是养老金，中国神华是煤气罐，贵州茅台是传家宝。”",
    "“大秦铁路不是股票，它是你的一本每年发 6% 利息的存折。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”"
]

# ========================= 3. 终极持仓配置 (不删除，已完善) =========================
PORTFOLIO_CFG = {
    # --- 原有持仓 ---
    "600900": {
        "name": "长江电力",
        "role": "🏔️ 基石 (养老)",
        "buy_zone_pe": 20.0,
        "key_metric": "股息率/来水",
        "time_nodes": "💰分红: 7月 | 🌊丰水期: 6-9月",
        "report_focus": "关注【折旧计提完成】情况与【来水偏枯/偏丰】。",
        "mental": "它负责兜底。只要跌下来，就是加仓送分题。",
        "action": "有闲钱优先买它。"
    },
    "000858": {
        "name": "五粮液",
        "role": "🍷 现金 (价值)",
        "buy_price": 110.0,
        "key_metric": "PE < 15",
        "time_nodes": "🧧春节备货: 1月 | 🍂中秋: 9月",
        "report_focus": "关注【批价】波动与【合同负债】蓄水池。",
        "mental": "它是工具。110以下是黄金坑，130以上停止买入。",
        "action": "持有2手不动，现价极具性价比。"
    },
    "000333": {
        "name": "美的集团",
        "role": "🤖 成长 (制造)",
        "buy_zone_pe": 12.0,
        "key_metric": "海外营收/B端",
        "time_nodes": "🚢出口数据: 每月 | ❄️空调旺季: 5-7月",
        "report_focus": "关注【KUKA机器人】盈利改善与【外销占比】。",
        "mental": "中国制造业巅峰。代替京沪高铁和紫金。",
        "action": "分批买入，拿住3-5年。"
    },
    "300059": {
        "name": "东方财富",
        "role": "🧨 期权 (牛市)",
        "buy_zone_pe": 25.0,
        "key_metric": "两市成交额",
        "time_nodes": "📈行情爆发期",
        "report_focus": "关注【天天基金】保有量与【证券自营】波动。",
        "mental": "这是彩票。仓位锁死 10%，无论涨跌绝不加仓。",
        "action": "大跌买，大涨卖，不长拿。"
    },
    # --- 新增/深度规划持仓 ---
    "601088": {
        "name": "中国神华",
        "role": "⚫️ 底座 (资源)",
        "buy_zone_pe": 12.0,
        "key_metric": "股息率 > 6%",
        "time_nodes": "❄️冬储: 12-1月 | ☀️度夏: 7-8月",
        "report_focus": "关注【长协煤占比】与【煤电一体化】对冲效果。",
        "mental": "家里有矿，心中不慌。高股息是硬道理。",
        "action": "挂单低吸，不追高。"
    },
    "601006": {
        "name": "大秦铁路",
        "role": "🛤️ 存折 (现金)",
        "buy_zone_pe": 10.0,
        "key_metric": "股息率/运量",
        "time_nodes": "⚠️检修: 4月/10月 | 💰分红: 7月",
        "report_focus": "关注【大秦线运量】数据是否稳住。",
        "mental": "它是永续债。价格越低，年化利息越高。",
        "action": "地板价，直接填满底仓。"
    },
    "601985": {
        "name": "中国核电",
        "role": "⚛️ 引擎 (公用)",
        "buy_zone_pe": 18.0,
        "key_metric": "装机增速",
        "time_nodes": "🏗️新机组核准: 不定期",
        "report_focus": "关注【风光新能源】装机占比与【核电核准】节奏。",
        "mental": "它是还在长身体的孩子。工资定投首选。",
        "action": "无脑定投，利用波动摊薄成本。"
    },
    "600519": {
        "name": "贵州茅台",
        "role": "👑 股王 (护城)",
        "buy_price": 1400.0,
        "key_metric": "批价/直销比",
        "time_nodes": "🧧春节: 1月 | 💰分红: 6月",
        "report_focus": "关注【i茅台直销占比】与【提价预期】。",
        "mental": "它是A股的锚。跌破1400是上帝给的礼物。",
        "action": "极度稀缺，1400以下分批接。"
    },
    "601882": {
        "name": "海天精工",
        "role": "⚙️ 卫星 (制造)",
        "buy_zone_pe": 15.0,
        "key_metric": "PMI/设备更新",
        "time_nodes": "🏗️制造业周期",
        "report_focus": "关注【龙门加工中心】订单与【海外出口】增速。",
        "mental": "工业母机。赌中国制造业设备更新红利。",
        "action": "小仓位博弈，适合周期底部布局。"
    },
    "601816": {
        "name": "京沪高铁",
        "role": "🚄 动脉 (现金)",
        "buy_zone_pe": 20.0,
        "key_metric": "客座率",
        "time_nodes": "🚅春运/暑运 | 💰分红: 7月",
        "report_focus": "关注【浮动票价】执行力度与【路网服务费】。",
        "mental": "黄金通道。它是守成期的顶级资产。",
        "action": "回撤20%以上是极佳入场点。"
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
            
            # 数据清洗
            try: pe = float(pe)
            except: pe = 999
            
            # 智能信号生成 (基于您要求的逻辑修正)
            signal = "🔒 持仓"
            color = "#7f8c8d" 
            tip = cfg['action']

            # 特殊估值逻辑处理
            if code == "000858" and price < 115: # 五粮液现价战术
                signal = "🚨 黄金坑"
                color = "#c0392b"
                tip = "现价极度低估，未来5年自由的门票！"
            elif code == "600519" and price < 1400: # 茅台战术
                signal = "👑 扫货"
                color = "#d4af37"
                tip = "跌破心理防线，买入后请卸载软件。"
            elif pe < cfg.get('buy_zone_pe', 0): # 通用PE逻辑
                signal = "🟢 极佳"
                color = "#27ae60"
                tip = "进入击球区，大胆加仓。"
            
            results.append({
                "name": name, "role": cfg['role'], "price": price, "pe": pe,
                "signal": signal, "color": color, "tip": tip, "mental": cfg['mental'],
                "nodes": cfg['time_nodes'], "focus": cfg['report_focus'],
                "metric": cfg['key_metric']
            })
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        html = f"""<div style="font-family:'Helvetica Neue', Arial, sans-serif;max-width:650px;margin:0 auto;background:#e6e6e6;padding:20px;">
        <div style="background:#000;color:#fff;padding:25px;border-radius:12px;text-align:center;box-shadow:0 6px 15px rgba(0,0,0,0.3);">
            <h3 style="margin:0;font-size:24px;">🛡️ 十五五·资产监控看板</h3>
            <p style="margin:8px 0 0;font-size:13px;opacity:0.8;letter-spacing:1px;">{self.today.strftime("%Y-%m-%d %H:%M")} | 上班定投，未来自由</p>
        </div>
        <div style="margin:20px 0;background:#fff;padding:15px;border-left:5px solid #d93025;font-style:italic;color:#444;border-radius:4px;box-shadow:0 2px 5px rgba(0,0,0,0.1);">{quote}</div>"""
        
        for item in data:
            html += f"""
            <div style="background:#fff;margin-bottom:20px;padding:20px;border-radius:12px;box-shadow:0 4px 10px rgba(0,0,0,0.15);border:1px solid #ddd;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                    <div>
                        <b style="font-size:20px;color:#333;">{item['name']}</b>
                        <span style="font-size:12px;color:#777;margin-left:8px;">{item['role']}</span>
                    </div>
                    <div style="background:{item['color']};color:#fff;padding:6px 12px;border-radius:20px;font-size:13px;font-weight:bold;">{item['signal']}</div>
                </div>
                
                <div style="background:#f9f9f9;padding:12px;border-radius:8px;margin-bottom:15px;border:1px solid #eee;">
                    <div style="display:flex;justify-content:space-between;font-size:14px;color:#555;">
                        <span>现价: <b>¥{item['price']}</b></span>
                        <span>关注指标: <b>{item['metric']}</b> (PE: {item['pe']})</span>
                    </div>
                </div>

                <div style="font-size:13px;line-height:1.6;color:#444;">
                    <div style="margin-bottom:5px;"><span style="color:#e67e22;">📅 关键时间:</span> {item['nodes']}</div>
                    <div style="margin-bottom:10px;"><span style="color:#2980b9;">📊 研报重点:</span> {item['focus']}</div>
                    <div style="padding:12px;background:#e8f4fd;border-radius:8px;border:1px solid #c5e1f9;color:#004085;">
                        <b>🧠 决策心法:</b> {item['mental']}<br>
                        <b style="color:#d93025;font-size:14px;">👉 指令: {item['tip']}</b>
                    </div>
                </div>
            </div>"""
        
        html += """<div style="text-align:center;color:#888;font-size:12px;margin-top:20px;">Designed by Gemini for Mango Strategy</div></div>"""
        return html

    def run(self):
        analysis = self.analyze()
        if analysis:
            html = self.generate_html(analysis)
            # 推送逻辑 (保留您原有的代码逻辑)
            if PUSHPLUS_TOKEN:
                requests.post('http://www.pushplus.plus/send', json={
                    "token": PUSHPLUS_TOKEN,
                    "title": f"资产看板 {self.today.strftime('%m-%d')}",
                    "content": html,
                    "template": "html"
                })
            print("报告已生成并尝试推送。")

if __name__ == "__main__":
    AutoStrategy().run()
