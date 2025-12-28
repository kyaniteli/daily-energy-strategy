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

# ========================= 2. 30年·本分语录 (扩充版) =========================
QUOTES = [
    "“宁可错过紫金的暴涨，也不要在高位站岗。手里有现金，心中不慌。”",
    "“长江电力是你的养老金，中国神华是你的煤气罐，贵州茅台是你的传家宝。”",
    "“不要预测牛市，要时刻准备好牛市不来我们也能赚钱。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“大秦铁路不是股票，它是你的一本每年发 6% 利息的存折。”",
    "“下跌是上帝给价值投资者的礼物，而不是惩罚。”"
]

# ========================= 3. 终极持仓配置 (8大金刚) =========================
# 财报季通用提醒：4月(年报+一季报), 8月(半年报), 10月(三季报)
PORTFOLIO_CFG = {
    # -------- 核心底座 (现金流/能源) --------
    "601088": {
        "name": "中国神华",
        "role": "⚫️ 能源底座",
        "strategy": "dividend",
        "buy_zone_pb": 1.2,     # 周期股看PB，1.2倍以下安全
        "key_metric": "股息率 > 6%",
        "time_nodes": "💰分红季: 6-7月 | 🔥旺季: 夏/冬",
        "report_focus": "关注【煤炭单位生产成本】是否上升，【长协煤占比】是否稳定。",
        "mental": "它是家里的粮仓。只要股息率超过6%，就比银行理财强两倍。不用看煤价波动，只看分红到账。",
        "action": "分批建仓，越跌越买，拿分红复投。"
    },
    "601006": {
        "name": "大秦铁路",
        "role": "🛤️ 国家存折",
        "strategy": "dividend",
        "buy_zone_pb": 0.8,     # 极其保守的PB
        "key_metric": "股息率 > 6.5%",
        "time_nodes": "💰分红季: 6-7月 | ⚠️检修: 春/秋",
        "report_focus": "关注【大秦线运量】数据，关注【分红率】是否维持在50%以上。",
        "mental": "它是甚至不需要看K线的股票。把它当成永续债，价格越低，利息越高。",
        "action": "地板价，直接填满底仓，当做打新门票。"
    },
    "600900": {
        "name": "长江电力",
        "role": "🏔️ 养老基石",
        "strategy": "hold",
        "buy_zone_pe": 20.0,
        "key_metric": "股息率/来水",
        "time_nodes": "💰分红季: 7月 | 🌊丰水期: 6-9月",
        "report_focus": "关注【乌东德/白鹤滩】注入后的折旧情况，关注【来水偏枯/偏丰】。",
        "mental": "它负责兜底。水电是时间的朋友，折旧完后全是利润。",
        "action": "有闲钱优先买它，这是留给孙子的。"
    },
    
    # -------- 核心成长 (护城河/垄断) --------
    "601985": {
        "name": "中国核电",
        "role": "⚛️ 绿色引擎",
        "strategy": "growth",
        "buy_zone_pe": 15.0,
        "key_metric": "核准/装机量",
        "time_nodes": "🏗️投产: 全年关注公告",
        "report_focus": "关注【新能源（风光）装机增速】，关注【核电机组核准】进度。",
        "mental": "它是还在长身体的孩子。十五五期间缺电+双碳，核电是唯一解。",
        "action": "工资定投首选，利用波动摊低成本。"
    },
    "600519": {
        "name": "贵州茅台",
        "role": "👑 A股之王",
        "strategy": "value",
        "buy_price": 1400.0,    # 心理锚点
        "key_metric": "批价/直销比",
        "time_nodes": "🧧春节: 1-2月 | 💰分红: 6月",
        "report_focus": "关注【i茅台/直销占比】（利润释放动力），关注【批发价】是否稳住。",
        "mental": "它是社交货币。如果跌到1300-1400，那是可能会绝迹的黄金坑。",
        "action": "极度珍稀。跌破关键价位必须敢于出手，买一手锁仓。"
    },
    
    # -------- 弹性/进攻 (消费/制造/金融) --------
    "000858": {
        "name": "五粮液",
        "role": "🍷 弹性前锋",
        "strategy": "value",
        "buy_price": 110.0,     # 黄金坑位
        "key_metric": "PE < 15",
        "time_nodes": "🧧春节: 1-2月 | 🍂中秋: 9月",
        "report_focus": "关注【合同负债】（蓄水池），关注【八代五粮液】动销情况。",
        "mental": "它是工具。100元以下是黄金坑，110左右是合理，130以上停止买入。",
        "action": "当前性价比极高，优先配置，博取戴维斯双击。"
    },
    "000333": {
        "name": "美的集团",
        "role": "🤖 全球制造",
        "strategy": "growth",
        "buy_zone_pe": 11.0,
        "key_metric": "海外营收/ToB",
        "time_nodes": "🌍出口数据: 每月海关",
        "report_focus": "关注【B端业务（机器人/楼宇）】增速，关注【海外毛利率】。",
        "mental": "它是中国制造业的巅峰。低估值+高分红+回购注销，不仅是家电，更是机器人。",
        "action": "分批买入，拿住3-5年。"
    },
    "300059": {
        "name": "东方财富",
        "role": "🧨 牛市期权",
        "strategy": "casino",
        "buy_zone_pe": 20.0,
        "key_metric": "日成交额",
        "time_nodes": "📈行情爆发期",
        "report_focus": "关注【基金销售保有量】，关注【证券自营业务】波动。",
        "mental": "这是彩票。仓位锁死 10%，无论涨跌绝不加仓。只在没人谈论股票时买。",
        "action": "大跌买，大涨卖，不长拿。"
    }
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()

    def get_market_status(self):
        # 这里可以扩展为真实的指数判断
        return "🛡️ 蛰伏积累期", "#2c3e50"

    def get_data(self):
        try:
            # 获取A股实时行情，包含PE(TTM), PB等
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
            
            name = row['名称'] # 使用接口返回的名称或配置名称均可
            price = row['最新价']
            pe = row['市盈率-动态'] # 注意：这里用动态PE作为参考
            pb = row['市净率']
            
            # 基础数据清洗
            try: pe = float(pe)
            except: pe = 999.0
            try: pb = float(pb)
            except: pb = 999.0
            
            # --- 智能信号核心逻辑 ---
            signal = "🔒 持仓"
            color = "#7f8c8d" # 默认灰
            tip = "当前价格处于中性区间，耐心持有。"

            # 1. 茅台逻辑 (看绝对价格和PE)
            if code == "600519":
                if price < 1400 or pe < 22:
                    signal = "👑 抄底茅台"
                    color = "#d4af37" # 金色
                    tip = "茅台跌入击球区！这是极为罕见的机会。"
                elif price > 1800:
                    signal = "🛑 观望"
                    color = "#e74c3c"
                    tip = "价格偏高，不如去买五粮液。"

            # 2. 神华/大秦逻辑 (看PB和红利属性)
            elif code in ["601088", "601006"]:
                target_pb = cfg.get('buy_zone_pb', 1.0)
                if pb < target_pb:
                    signal = "💎 捡烟蒂"
                    color = "#27ae60" # 深绿
                    tip = f"PB低于{target_pb}！股息率性价比极高，闭眼买入。"
                elif pb > target_pb * 1.5:
                    signal = "⚠️ 偏贵"
                    color = "#f39c12"
                    tip = "作为红利股估值略高，暂停买入，只拿分红。"
                else:
                    tip = f"价格合理，{cfg['action']}"

            # 3. 核电/长电/美的 (看PE成长)
            elif code in ["601985", "600900", "000333"]:
                target_pe = cfg.get('buy_zone_pe', 20)
                if pe < target_pe:
                    signal = "🟢 定投"
                    color = "#2ecc71"
                    tip = f"估值低于{target_pe}倍，适合利用工资结余定投。"
                elif pe > target_pe * 1.4:
                    signal = "🛑 暂缓"
                    color = "#e67e22"
                    tip = "短期涨幅过大，等待回调再加仓。"

            # 4. 五粮液 (黄金坑逻辑)
            elif code == "000858":
                if price < 115:
                    signal = "🚨 黄金坑"
                    color = "#c0392b" # 深红
                    tip = "价格极度低估！目前性价比全场最高，优先加仓。"
                elif price > 130:
                    signal = "🔒 锁仓"
                    color = "#95a5a6"
                    tip = "脱离底部区域，持有不动。"

            # 5. 东财 (赌场逻辑)
            elif code == "300059":
                if pe > 35:
                    signal = "💣 高危"
                    color = "#8e44ad" # 紫色警示
                    tip = "情绪过热，随时可能杀跌，建议止盈。"

            results.append({
                "name": cfg['name'],
                "role": cfg['role'],
                "price": price,
                "pe": pe,
                "pb": pb,
                "signal": signal,
                "color": color,
                "tip": tip,
                "mental": cfg['mental'],
                "key_metric": cfg['key_metric'],
                "time_nodes": cfg.get('time_nodes', ''),
                "report_focus": cfg.get('report_focus', '')
            })
        return results

    def generate_html(self, data):
        quote = random.choice(QUOTES)
        
        # HTML 样式优化：增加关键指标和时间轴显示
        html = f"""
        <div style="font-family:'Helvetica Neue', Arial, sans-serif;max-width:640px;margin:0 auto;background:#f4f6f7;padding:20px;border-radius:8px;">
        
        <div style="background:linear-gradient(135deg, #2c3e50, #000);color:#fff;padding:25px;border-radius:12px;text-align:center;box-shadow:0 8px 16px rgba(0,0,0,0.15);">
            <h2 style="margin:0;font-size:24px;letter-spacing:1px;">🛡️ 十五五·生存资产日报</h2>
            <p style="margin:8px 0 0;font-size:13px;opacity:0.8;">{self.today.strftime("%Y-%m-%d %H:%M")} | 战略定位：上班积累 → 自由收息</p>
        </div>
        
        <div style="margin:20px 0;background:#fff;padding:15px;border-left:5px solid #c0392b;font-style:italic;color:#555;border-radius:4px;box-shadow:0 2px 4px rgba(0,0,0,0.05);">
            {quote}
        </div>
        """
        
        for item in data:
            # 根据市净率还是市盈率显示核心指标
            val_metric = f"PE: {item['pe']}" if item['pe'] < 100 else f"PB: {item['pb']}"
            if item['name'] in ["中国神华", "大秦铁路"]:
                val_metric = f"PB: {item['pb']} (关注股息)"
            
            html += f"""
            <div style="background:#fff;margin-bottom:20px;border-radius:10px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);border:1px solid #e1e8ed;">
                <div style="padding:12px 15px;background:#f8f9fa;border-bottom:1px solid #eee;display:flex;justify_content:space-between;align-items:center;">
                    <div>
                        <span style="font-weight:bold;font-size:17px;color:#2c3e50;">{item['name']}</span>
                        <span style="font-size:12px;color:#7f8c8d;margin-left:8px;background:#eee;padding:2px 6px;border-radius:4px;">{item['role']}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:18px;font-weight:bold;color:#2c3e50;">¥{item['price']}</span>
                    </div>
                </div>

                <div style="padding:15px;display:flex;align-items:center;border-bottom:1px dashed #eee;">
                    <div style="flex:1;">
                        <div style="font-size:12px;color:#95a5a6;">关注指标</div>
                        <div style="font-weight:bold;color:#34495e;">{item['key_metric']}</div>
                        <div style="font-size:11px;color:#7f8c8d;margin-top:2px;">{val_metric}</div>
                    </div>
                    <div style="flex:0 0 100px;text-align:center;">
                        <div style="background:{item['color']};color:#fff;padding:6px 12px;border-radius:20px;font-size:13px;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.2);">
                            {item['signal']}
                        </div>
                    </div>
                </div>

                <div style="padding:10px 15px;background:#fafafa;font-size:12px;color:#555;display:flex;gap:10px;">
                    <div style="flex:1;">
                        <span style="color:#e67e22;">📅 关键节点:</span> {item['time_nodes']}
                    </div>
                </div>
                <div style="padding:0 15px 10px 15px;background:#fafafa;font-size:12px;color:#666;">
                    <span style="color:#2980b9;">📊 研报重点:</span> {item['report_focus']}
                </div>

                <div style="padding:15px;background:#eef6fc;color:#2c3e50;font-size:13px;">
                    <div style="margin-bottom:6px;"><strong>🧠 心法:</strong> {item['mental']}</div>
                    <div style="color:{item['color']};font-weight:bold;">👉 行动: {item['tip']}</div>
                </div>
            </div>
            """
            
        html += """<div style="text-align:center;color:#95a5a6;font-size:12px;margin-top:30px;">
            Designed by Gemini & ChatGPT for 155 Plan
        </div></div>"""
        return html

    def run(self):
        analysis = self.analyze()
        if analysis:
            return self.generate_html(analysis)
        return None

# ========================= 4. 推送服务 =========================
def send_pushplus(content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"Mango股市策略日报 {datetime.now().strftime('%m-%d')}",
        "content": content,
        "template": "html"
    }
    requests.post(url, json=data)

def send_email(content):
    if not SENDER_EMAIL or not SENDER_PASSWORD: return
    msg = MIMEText(content, 'html', 'utf-8')
    msg['From'] = Header("Mango Investment", 'utf-8')
    msg['To'] = Header("Owner", 'utf-8')
    msg['Subject'] = Header(f"股市策略日报 {datetime.now().strftime('%Y-%m-%d')}", 'utf-8')
    try:
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    strategy = AutoStrategy()
    report = strategy.run()
    if report:
        if PUSHPLUS_TOKEN: send_pushplus(report)
        if SENDER_EMAIL: send_email(report)
        print("策略报告已生成并推送")
    else:
        print("数据获取失败或市场休市")
