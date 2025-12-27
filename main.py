import akshare as ak
import pandas as pd
import requests
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

# ========================= 1. 环境变量配置 =========================
# 请在 Github Secrets 或本地环境变量中配置这些信息
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")

# ========================= 2. 信仰语录 (30年传世版) =========================
QUOTES = [
    "“长电是用来养老的，五粮液是用来抗通胀的，东财是用来做梦的。分工明确，心态才稳。”",
    "“卖出广核换长电，是用‘白银’换‘黄金’。不要看价格，要看生意的寿命。”",
    "“五粮液只是工具，不是信仰。跌到 100 以下是机会，涨上去是红利，别动感情。”",
    "“东财涨到天上去也别加仓，那是赌博；长电跌到地板上要敢加仓，那是机会。”",
    "“本分就是：不赚看不懂的钱，不接高估值的盘，不信一夜暴富的神话。”",
    "“如果你无法持有长江电力 10 年，就不要持有它 10 分钟。”"
]

# ========================= 3. 4321 阵型终极配置 =========================
# 逻辑核心：基于 2025.12.27 复盘结论
PORTFOLIO_CFG = {
    "600900": {
        "name": "长江电力",
        "role": "🏔️ 基石 (40%)",
        "strategy": "hold_forever", # 永久持有策略
        "target_pe": 20.0,          # 合理PE锚点
        "buy_zone": 22.0,           # 低于此PE可无脑定投
        "sell_zone": 30.0,          # 极度高估线
        "key_metric": "股息率",
        "report_focus": "关注乌东德、白鹤滩折旧政策及来水情况。",
        "mental": "只要水还在流，你的养老金就在印。跌了是送钱，别慌。"
    },
    "000858": {
        "name": "五粮液",
        "role": "💰 现金牛 (30%)",
        "strategy": "value_pick",   # 捡烟蒂策略
        "target_pe": 15.0,
        "buy_price": 100.0,         # 绝对价格买入线
        "sell_zone": 30.0,          # 泡沫线
        "key_metric": "PE(TTM)",
        "report_focus": "关注合同负债（蓄水池）是否下降，分红率是否提升。",
        "mental": "它是工具。跌破 100 块是上帝给的机会，买了就拿分红，别幻想它成科技股。"
    },
    "601816": {
        "name": "京沪高铁",
        "role": "🛡️ 防线 (20%)",
        "strategy": "bond_proxy",   # 类债券策略
        "target_pe": 20.0,
        "buy_zone": 20.0,
        "sell_zone": 35.0,
        "key_metric": "PE(TTM)",
        "report_focus": "关注票价浮动机制及客流恢复情况。",
        "mental": "收租公就要有收租公的觉悟。不指望翻倍，只指望跑赢通胀。"
    },
    "300059": {
        "name": "东方财富",
        "role": "🧨 期权 (10%)",
        "strategy": "casino",       # 赌场策略
        "target_pe": 25.0,
        "buy_zone": 20.0,           # 极度低估才买
        "sell_zone": 40.0,          # 疯狂泡沫必卖
        "key_metric": "PE(TTM)",
        "report_focus": "关注日均成交额（牛市风向标）。",
        "mental": "这是彩票。赢了把钱换长电，输了就当看戏。严禁加仓超过 10%！"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()

    def get_market_status(self):
        # 简单的市场温度计
        return "🤖 4321 纪律执行中", "#188038"

    def get_data(self):
        try:
            print("正在连接交易所获取实时数据...")
            # akshare 接口：获取A股实时行情
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
            
            # 基础数据
            name = cfg['name']
            price = row['最新价']
            pe = row['市盈率-动态'] # 注意：这里取动态PE，也可换成TTM
            pb = row['市净率']
            change_pct = row['涨跌幅']
            
            # --- 智能诊断逻辑 ---
            signal = "🔒 持仓不动"
            signal_color = "#666" # 灰色
            action_tip = "当前价格处于合理区间，安心持有收息。"
            
            # 1. 长江电力逻辑
            if code == "600900":
                if pe < cfg['buy_zone']:
                    signal = "💎 贪婪加仓"
                    signal_color = "#d93025" # 红色
                    action_tip = f"PE低于{cfg['buy_zone']}，这是送分题，有闲钱务必买入。"
                elif pe > cfg['sell_zone']:
                    signal = "⚠️ 估值过热"
                    signal_color = "#f39c12" # 橙色
                    action_tip = "估值偏高，停止定投，享受泡沫，不要卖出核心仓位。"
            
            # 2. 五粮液逻辑 (绝对价格 + PE)
            elif code == "000858":
                if price < cfg['buy_price']:
                    signal = "💰 黄金大坑"
                    signal_color = "#d93025"
                    action_tip = f"股价跌破 {cfg['buy_price']} 元！动用最后备用金买入第3手！"
                elif pe < 15:
                    signal = "📥 低吸区域"
                    signal_color = "#188038" # 绿色
                    action_tip = "15倍PE以下，只买不卖，慢慢定投。"
                elif pe > 25:
                    signal = "🛑 停止买入"
                    signal_color = "#f39c12"
                    action_tip = "估值修复完成，把它当债券拿，一股都别加。"

            # 3. 京沪高铁逻辑
            elif code == "601816":
                if pe < 20:
                    signal = "📥 定投区间"
                    signal_color = "#188038"
                    action_tip = "PE回归20倍以下，具备防御价值，可配置。"
            
            # 4. 东方财富逻辑 (止盈风控)
            elif code == "300059":
                if pe > cfg['sell_zone']:
                    signal = "🚀 止盈警报"
                    signal_color = "#8e44ad" # 紫色
                    action_tip = "市盈率过高！请考虑卖出本金，转投长江电力！"
                elif pe < 20:
                    signal = "🎭 极度低估"
                    action_tip = "虽然便宜，但切记仓位锁死 10%，不要贪。"

            # 核心指标展示
            metrics_html = f"""
            <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:12px; color:#555;">
                <span>PE: <b>{pe}</b></span>
                <span>PB: <b>{pb}</b></span>
                <span>涨跌: <b style="color:{'#d93025' if change_pct > 0 else '#188038'}">{change_pct}%</b></span>
            </div>
            """

            results.append({
                "name": name,
                "role": cfg['role'],
                "price": price,
                "signal": signal,
                "signal_color": signal_color,
                "action_tip": action_tip,
                "metrics_html": metrics_html,
                "mental": cfg['mental'],
                "report_focus": cfg['report_focus']
            })
            
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        html = f"""
        <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
            <div style="background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 0 0 15px 15px; color: white; text-align: center;">
                <div style="font-size: 20px; font-weight: bold; letter-spacing: 1px;">🛡️ 30年传世阵型 · 监控日报</div>
                <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">{self.today.strftime("%Y-%m-%d %H:%M")}</div>
            </div>

            <div style="margin: 15px; background: #fff; padding: 15px; border-radius: 10px; border-left: 5px solid #d93025; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 14px; color: #333; font-style: italic; line-height: 1.6;">{quote}</div>
            </div>

            <div style="padding: 0 15px;">
        """
        
        for item in data:
            html += f"""
            <div style="background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); position: relative; overflow: hidden;">
                <div style="position: absolute; top: 0; right: 0; background: #f1f3f5; color: #666; font-size: 10px; padding: 4px 8px; border-radius: 0 12px 0 10px;">
                    {item['role']}
                </div>
                
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <div>
                        <span style="font-size: 18px; font-weight: 800; color: #2c3e50;">{item['name']}</span>
                    </div>
                    <div style="background-color: {item['signal_color']}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">
                        {item['signal']}
                    </div>
                </div>

                <div style="display: flex; align-items: baseline;">
                    <span style="font-size: 28px; font-weight: 900; color: #2c3e50; margin-right: 10px;">{item['price']}</span>
                    <span style="font-size: 12px; color: #999;">人民币</span>
                </div>
                {item['metrics_html']}

                <div style="margin-top: 12px; background-color: #fcf6f5; border: 1px dashed #e0e0e0; padding: 10px; border-radius: 8px;">
                    <div style="font-size: 13px; color: #c0392b; font-weight: bold;">⚡ 操作指令：</div>
                    <div style="font-size: 13px; color: #555; margin-top: 4px; line-height: 1.4;">{item['action_tip']}</div>
                </div>

                <div style="margin-top: 8px; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 8px;">
                    🧠 <b>心态锚定：</b>{item['mental']}
                </div>
            </div>
            """

        html += """
            <div style="text-align: center; font-size: 12px; color: #aaa; margin: 20px 0;">
                Build with Python & Logic by Gemini Strategy
            </div>
        </div>
        """
        return html

# ========================= 发送逻辑 =========================
def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    token_list = PUSHPLUS_TOKEN.replace("，", ",").split(",")
    for token in token_list:
        if token.strip():
            try:
                url = 'http://www.pushplus.plus/send'
                data = {"token": token.strip(), "title": title, "content": content, "template": "html"}
                requests.post(url, json=data)
            except Exception as e: print(f"Pushplus发送失败: {e}")

def send_email(title, content):
    if not SENDER_PASSWORD or not RECEIVER_EMAIL: return
    receivers = RECEIVER_EMAIL.replace("，", ",").split(",")
    try:
        msg = MIMEText(content, 'html', 'utf-8')
        msg['From'] = Header("AI投资助理", 'utf-8')
        msg['Subject'] = Header(title, 'utf-8')
        
        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, receivers, msg.as_string())
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    bot = AutoStrategy()
    data = bot.analyze()
    
    if data:
        # 标题带上日期
        title_date = datetime.now().strftime('%m-%d')
        title = f"🛡️ 4321传世持仓日报 {title_date}"
        
        html_content = bot.generate_html(data)
        
        # 多通道推送
        send_pushplus(title, html_content)
        send_email(title, html_content)
        
        print("✅ 所有任务执行完毕")
    else:
        print("❌ 无数据，未发送")
