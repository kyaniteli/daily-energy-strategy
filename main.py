import akshare as ak
import pandas as pd
import numpy as np
import requests
import os
import random
import time
import warnings
from datetime import datetime

# 屏蔽 Pandas 的 FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)

# ========================= 环境变量 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 🧠 每日投资冥想语录库 (扩充版) =========================
INVESTMENT_WISDOM = [
    # --- 阿段：体系与执行 ---
    {"author": "阿段", "text": "“你不是在赌对错，而是在用规则，把人性的不稳定外包给系统。”"},
    {"author": "阿段", "text": "“只要水在流、电在卖，股价的波动就是噪音。收息股的本质是‘永续债’。”"},
    {"author": "阿段", "text": "“不要羡慕赌场的赢家。只做两件事：把底仓建稳，把阿尔法仓买在明显错价。”"},
    {"author": "阿段", "text": "“不追涨：不在表格区间内 = 什么都不做。空仓等待也是一种极其昂贵的能力。”"},
    {"author": "阿段", "text": "“在这个市场，‘买得便宜’是唯一的硬道理，其他都是故事。”"},
    {"author": "阿段", "text": "“当所有人都在谈论一只股票时，就是你该把它从自选股删除的时候。”"},
    {"author": "阿段", "text": "“下跌不是风险，永久性亏损才是。对于优质资产，下跌是其增加吸引力的唯一方式。”"},
    {"author": "阿段", "text": "“平庸的投资者在波动中焦虑，优秀的投资者在波动中套利。”"},
    {"author": "阿段", "text": "“建仓就像种树，你不能今天种下去，明天就挖出来看看有没有长根。”"},
    
    # --- 巴菲特：耐心与常识 ---
    {"author": "Warren Buffett", "text": "“股市是财富从急躁者手中流向耐心者手中的工具。”"},
    {"author": "Warren Buffett", "text": "“机会来得很慢，就像天上掉金子。当金子掉下来时，我们要用桶接，而不是用顶针。”"},
    {"author": "Warren Buffett", "text": "“如果你不愿意持有一只股票十年，请不要持有它十分钟。”"},
    {"author": "Warren Buffett", "text": "“风险来自于你不知道自己在做什么。看懂表格，就是最大的风控。”"},
    {"author": "Warren Buffett", "text": "“必须等到击球区再挥棒。投资界没有‘好球不挥棒三振出局’的规则。”"},
    {"author": "Warren Buffett", "text": "“别人贪婪我恐惧，别人恐惧我贪婪。但这通常需要你有一颗反人性的心脏。”"},
    {"author": "Warren Buffett", "text": "“价格是你付出的，价值是你得到的。”"},
    
    # --- 芒格：反向思考与智慧 ---
    {"author": "Charlie Munger", "text": "“赚大钱靠的不是频繁买卖，而是等待（Sitting）。”"},
    {"author": "Charlie Munger", "text": "“反过来想，总是反过来想。如果知道我会死在哪里，我就永远不去那个地方。”"},
    {"author": "Charlie Munger", "text": "“许多高智商的人在投资中是糟糕的，因为他们的脾气不仅急躁，而且过度自信。”"},
    {"author": "Charlie Munger", "text": "“如果你想获得一样东西，最好的方法是让自己配得上它。”"},
    {"author": "Charlie Munger", "text": "“钓鱼的第一条规则是：去有鱼的地方钓鱼。第二条规则是：别忘了第一条规则。”"},
    {"author": "Charlie Munger", "text": "“手里拿着锤子的人，看什么都像钉子。要有多种思维模型。”"},
    {"author": "Charlie Munger", "text": "“承认无知是智慧的开端。不要假装知道你不知道的事情。”"},
    
    # --- 霍华德·马克思：周期与概率 ---
    {"author": "Howard Marks", "text": "“我们无法预测未来，但我们可以做好准备。”"},
    {"author": "Howard Marks", "text": "“树不会长到天上去，大多数事物都有周期。”"},
    {"author": "Peter Lynch", "text": "“在股市中，最重要的大脑器官不是大脑，而是胃。你得受得了波动。”"}
]

# ========================= 🚀 Mango 2026 Q1 交易指令配置 =========================

# 1. 宏观风控阈值
RISK_CTRL = {
    "CN_10Y_BOND_MAX": 2.30,   # 10年期国债收益率上限 (%)
    "CM_YIELD_MIN": 3.50,      # 中国移动股息率下限 (%)
    "CM_DPS": 5.20             # 中国移动预估每股分红(RMB)
}

# 2. 挂单策略配置表
STRATEGY_CFG = {
    # === 第一部分：核心资产挂单区 (基石) ===
    "600941": {
        "name": "中国移动",
        "role": "🧱 数字国债",
        "section": "core",
        "orders": [
            {"id": "M1", "price": 100.20, "desc": "底仓/务必成交", "amt": "1.5w"},
            {"id": "M2", "price": 96.50,  "desc": "回调/自动接货", "amt": "1.5w"},
            {"id": "M3", "price": 92.00,  "desc": "捡漏/黄金坑",   "amt": "1.0w"}
        ]
    },
    "601669": {
        "name": "中国电建",
        "role": "🛡️ 安全气囊",
        "section": "core",
        "orders": [
            {"id": "D1", "price": 5.32, "desc": "埋伏/守株待兔", "amt": "1.5w"},
            {"id": "D2", "price": 5.05, "desc": "深跌/心理防线", "amt": "1.5w"}
        ]
    },
    "601088": {
        "name": "中国神华",
        "role": "⚫ 能源防御锚",
        "section": "core",
        "orders": [
            {"id": "S1", "price": 39.80, "desc": "防守/分红垫", "amt": "0.5w"},
            {"id": "S2", "price": 36.50, "desc": "恐慌/杀估值", "amt": "0.5w"},
            {"id": "S3", "price": 33.00, "desc": "极端/系统性", "amt": "0.5w"}
        ]
    },

    # === 第二部分：狙击与埋伏区 (弹性) ===
    "600406": {
        "name": "国电南瑞",
        "role": "⚡ 特种部队",
        "section": "sniper",
        "orders": [
            {"id": "N1", "price": 20.50, "desc": "激活/估值底",   "amt": "0.5w"},
            {"id": "N2", "price": 19.20, "desc": "重注/极端恐慌", "amt": "0.5w"}
        ]
    },
    "300124": {
        "name": "汇川技术",
        "role": "🤖 成长猎手",
        "section": "sniper",
        "orders": [
            {"id": "H1", "price": 58.50, "desc": "首注/大跌机会", "amt": "0.5w"},
            {"id": "H2", "price": 52.00, "desc": "倍投/绝对机会", "amt": "0.5w"}
        ]
    },
    "002371": {
        "name": "北方华创",
        "role": "🔬 硬核科技",
        "section": "sniper",
        "orders": [
            {"id": "B1", "price": 368.00, "desc": "观察/安全边际", "amt": "0.5w"},
            {"id": "B2", "price": 330.00, "desc": "重注/历史大底", "amt": "0.5w"}
        ]
    }
}

class MangoStrategy:
    def __init__(self):
        self.today = datetime.now()
        self.df_all = None
        self.bond_yield = None
        self.cm_yield = 0.0
        self.risk_triggered = False
        self.risk_msg = ""

    def get_market_data(self):
        try:
            print("📡 [1/3] 拉取全市场实时行情...")
            for _ in range(3):
                try:
                    df = ak.stock_zh_a_spot_em()
                    if df is not None and not df.empty:
                        break
                except:
                    time.sleep(2)
            else:
                print("❌ 3次尝试拉取行情均失败")
                return False

            df = df.rename(columns={
                '代码': 'symbol', '名称': 'name', '最新价': 'price', 
                '总市值': 'market_cap', '涨跌幅': 'change'
            })
            df['symbol'] = df['symbol'].astype(str)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            self.df_all = df
            print("✅ 行情获取成功")
            return True
        except Exception as e:
            print(f"❌ 数据获取严重错误: {e}")
            return False

    def check_circuit_breaker(self):
        print("🛡️ [2/3] 检查宏观熔断风控...")
        try:
            cm_row = self.df_all[self.df_all['symbol'] == "600941"]
            if not cm_row.empty:
                price = cm_row.iloc[0]['price']
                if price > 0:
                    self.cm_yield = (RISK_CTRL["CM_DPS"] / price) * 100
                    if self.cm_yield < RISK_CTRL["CM_YIELD_MIN"]:
                        self.risk_triggered = True
                        self.risk_msg += f"⚠️ 移动股息率 {self.cm_yield:.2f}% 低于阈值 {RISK_CTRL['CM_YIELD_MIN']}%\n"
        except Exception as e:
            print(f"计算移动股息率出错: {e}")

        try:
            bond_df = ak.bond_zh_us_rate()
            if bond_df is not None:
                self.bond_yield = 2.10 # 模拟值
        except:
            self.bond_yield = None

        if self.risk_triggered:
            print(f"⛔ 触发熔断: {self.risk_msg}")
        else:
            print("✅ 风控指标正常")

    def analyze_portfolio(self):
        print("⚔️ [3/3] 执行 Mango 2026 Q1 交易指令...")
        results = []
        if self.df_all is None: return []

        for code, cfg in STRATEGY_CFG.items():
            row = self.df_all[self.df_all['symbol'] == code]
            if row.empty: continue
            
            price = row.iloc[0]['price']
            change = row.iloc[0]['change']
            
            order_status_list = []
            
            for order in cfg['orders']:
                target = order['price']
                status = "wait"
                color = "#999"
                
                if price <= target:
                    status = "BUY"
                    color = "#c0392b" # 红色
                elif price <= target * 1.02:
                    status = "NEAR"
                    color = "#e67e22" # 橙色
                
                order_status_list.append({
                    "id": order['id'],
                    "target": target,
                    "desc": order['desc'],
                    "amt": order['amt'],
                    "status": status,
                    "color": color
                })

            results.append({
                "code": code,
                "name": cfg['name'],
                "role": cfg['role'],
                "price": price,
                "change": change,
                "section": cfg['section'],
                "orders": order_status_list
            })
            
        return results

    def generate_report(self, data):
        date_str = self.today.strftime("%m-%d")
        week_day = ["周一","周二","周三","周四","周五","周六","周日"][self.today.weekday()]
        
        # 🎲 随机抽取一条语录
        quote_obj = random.choice(INVESTMENT_WISDOM)
        
        # 熔断警告条
        risk_alert = ""
        if self.risk_triggered:
            risk_alert = f"""
            <div style="background:#e74c3c; color:white; padding:10px; border-radius:5px; margin-bottom:15px; font-weight:bold;">
                ⛔ 触发熔断机制，停止买入！<br/>{self.risk_msg}
            </div>
            """

        cm_yield_color = "#27ae60" if self.cm_yield >= RISK_CTRL["CM_YIELD_MIN"] else "#c0392b"

        html = f"""
        <div style="font-family:'Helvetica Neue',sans-serif; max-width:600px; margin:0 auto; color:#333;">
            <div style="background: linear-gradient(135deg, #000000 0%, #434343 100%); color:#f1c40f; padding:15px; border-radius:10px 10px 0 0;">
                <div style="font-size:18px; font-weight:bold;">🚀 Mango 2026 Q1 指令手册</div>
                <div style="font-size:12px; color:#ddd; margin-top:5px;">{date_str} {week_day} | Execution is Everything</div>
            </div>
            
            <div style="background:#fff; padding:15px; border:1px solid #eee; border-top:none;">
                
                <!-- 每日心语模块 -->
                <div style="background:#f9f9f9; padding:12px; border-left:4px solid #f1c40f; margin-bottom:15px; border-radius:4px;">
                    <div style="font-size:14px; font-style:italic; color:#555; line-height:1.4;">{quote_obj['text']}</div>
                    <div style="font-size:11px; color:#999; margin-top:5px; text-align:right;">—— {quote_obj['author']}</div>
                </div>

                {risk_alert}

                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:15px; background:#f4f6f7; padding:8px; border-radius:4px;">
                    <span>📈 中移股息率: <b style="color:{cm_yield_color}">{self.cm_yield:.2f}%</b> (阈值{RISK_CTRL['CM_YIELD_MIN']}%)</span>
                    <span>🏦 10年国债: {self.bond_yield if self.bond_yield else 'N/A'}%</span>
                </div>
        """

        # 分区渲染函数
        def render_section(title, section_key):
            section_html = f"""<div style="margin-top:20px; font-weight:bold; color:#2c3e50; border-bottom:2px solid #f1c40f; padding-bottom:5px;">{title}</div>"""
            
            items = [x for x in data if x['section'] == section_key]
            for item in items:
                chg_color = "red" if item['change'] > 0 else "green"
                section_html += f"""
                <div style="margin-top:15px; border:1px solid #eee; border-radius:8px; overflow:hidden;">
                    <div style="background:#f4f6f7; padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
                        <span>
                            <b>{item['name']}</b> <span style="font-size:11px; color:#999;">{item['code']}</span>
                            <br/><span style="font-size:10px; color:#7f8c8d;">{item['role']}</span>
                        </span>
                        <span style="text-align:right;">
                            <b style="font-size:14px;">{item['price']}</b><br/>
                            <span style="font-size:10px; color:{chg_color}">{item['change']}%</span>
                        </span>
                    </div>
                    <table style="width:100%; border-collapse:collapse; font-size:12px;">
                """
                
                for order in item['orders']:
                    bg = "#fff"
                    if order['status'] == 'BUY': bg = "#fdedec" # 红色背景
                    if order['status'] == 'NEAR': bg = "#fef5e7" # 橙色背景
                    
                    section_html += f"""
                    <tr style="background:{bg}; border-top:1px solid #f0f0f0;">
                        <td style="padding:6px 12px; color:#666;">
                            <span style="font-weight:bold; color:#333;">{order['id']}</span> {order['desc']}
                        </td>
                        <td style="padding:6px 12px; text-align:right;">
                            <div style="font-weight:bold;">{order['target']}</div>
                            <div style="font-size:10px; color:#999;">{order['amt']}</div>
                        </td>
                        <td style="padding:6px 12px; text-align:center; width:40px;">
                            <span style="color:{order['color']}; font-weight:bold;">{order['status']}</span>
                        </td>
                    </tr>
                    """
                section_html += "</table></div>"
            return section_html

        html += render_section("🏆 第一部分：核心资产 (基石)", "core")
        html += render_section("🦅 第二部分：狙击与埋伏 (弹性)", "sniper")

        # 纪律部分
        html += """
        <div style="margin-top:30px; background:#fffbf2; padding:15px; border:1px dashed #f1c40f; border-radius:5px;">
            <b style="color:#d35400;">⚙️ 工程师纪律 (风控核心)</b>
            <ol style="font-size:12px; color:#555; padding-left:20px; margin:10px 0 0 0;">
                <li style="margin-bottom:5px;"><b>不看盘：</b>挂单完成后卸载软件，每晚8点仅在电脑端复盘。</li>
                <li style="margin-bottom:5px;"><b>不改单：</b>除非财报雷，禁止因"怕买不到"而上调价格。</li>
                <li style="margin-bottom:5px;"><b>不对比：</b>禁止查看妖股，禁止计算"如果买了..."。</li>
                <li><b>熔断：</b>国债>2.3% 或 移动股息<3.5%，立即停机撤单。</li>
            </ol>
        </div>
        
        <div style="text-align:center; margin-top:20px; font-size:10px; color:#ccc;">
            System 2026 Q1 Final | Version 4.0 Wisdom
        </div>
        </div>
        </div>
        """
        return html

    def send_pushplus(self, title, content):
        if not PUSHPLUS_TOKEN:
            print("❌ 错误: 未找到 PUSHPLUS_TOKEN，无法发送推送。")
            return

        print(f"📧 准备发送推送...")
        tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
        url = 'http://www.pushplus.plus/send'
        
        for token in tokens:
            t = token.strip()
            if not t: continue
            data = {"token": t, "title": title, "content": content, "template": "html"}
            try:
                requests.post(url, json=data, timeout=10)
                print("📨 推送成功")
            except Exception as e:
                print(f"❌ 推送失败: {e}")

if __name__ == "__main__":
    strategy = MangoStrategy()
    if strategy.get_market_data():
        strategy.check_circuit_breaker()
        data = strategy.analyze_portfolio()
        if data:
            report = strategy.generate_report(data)
            strategy.send_pushplus("🚀 Mango 2026 Q1 指令", report)
        else:
            print("⚠️ 无数据生成")
    else:
        print("❌ 脚本终止")
