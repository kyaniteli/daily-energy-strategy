import akshare as ak
import pandas as pd
import requests
import os
import random
import time  # 引入time用于延时，防止接口被封
from datetime import datetime, timedelta

# ========================= 环境变量 =========================
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 1. 金刚配置 (防守/信仰) =========================
QUOTES = [
    "“长江的水，神华的煤，广核的电，茅台的酒。这是中国最硬的物理资产。”",
    "“太贵了就不买，哪怕它涨到天上去。错失不是亏损。”",
    "“不要羡慕泡沫，泡沫破裂时，只有我们的水电站还在印钞。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“流水不争先，争的是滔滔不绝。”"
]

PORTFOLIO_CFG = {
    "600900": {"name": "长江电力","role": "🏔️ 养老基石","dps": 0.95,"strategy": "bond","risk_point": "股息率<2.8%"},
    "601088": {"name": "中国神华","role": "⚫️ 能源底座","dps": 2.62,"strategy": "bond","risk_point": "股息率<5.0%"},
    "601006": {"name": "大秦铁路","role": "🛤️ 国家存折","dps": 0.44,"strategy": "bond","risk_point": "股息率<5.5%"},
    "601985": {"name": "中国核电","role": "⚛️ 绿色引擎","dps": 0.17,"strategy": "growth","risk_point": "PE>25"},
    "600519": {"name": "贵州茅台","role": "👑 A股之王","dps": 30.8,"strategy": "value","risk_point": "PE>40"},
    "000858": {"name": "五粮液","role": "🍷 价值前锋","dps": 4.67,"strategy": "value","risk_point": "PE>25"},
    "000333": {"name": "美的集团","role": "🤖 全球制造","dps": 3.0,"strategy": "growth","risk_point": "PE>20"},
    "000568": {"name": "泸州老窖","role": "🚀 进攻核心","dps": 6.30,"strategy": "offensive","risk_point": "PE>30"},
    "002415": {"name": "海康威视","role": "📹 智能监控","dps": 0.40,"strategy": "growth","risk_point": "PE>30"}
}

# ========================= 2. 晨爷配置 (进攻/投机) =========================
CHENYE_CFG = {
    "MAX_PRICE": 15.0,        # 单价上限
    "MAX_CAP_BILLION": 60,    # 市值上限(亿)
    "POSITION_THRESHOLD": 20, # 必须在历史最低的 20% 区域
    "HISTORY_YEARS": 4        # 回溯历史4年
}

class FusionStrategy:
    def __init__(self):
        self.today = datetime.now()
        self.bond_yield = 2.10  # 十年期国债收益率(锚)
        self.df_all = None      # 全市场数据缓存

    def get_market_data(self):
        """拉取全市场数据，只做一次"""
        try:
            print("📡 [1/3] 拉取全市场实时行情...")
            df = ak.stock_zh_a_spot_em()
            # 统一列名
            df = df.rename(columns={
                '代码': 'symbol', '名称': 'name', '最新价': 'price', 
                '总市值': 'market_cap', '市盈率-动态': 'pe_ttm', '涨跌幅': 'change'
            })
            # 数据清洗
            df['symbol'] = df['symbol'].astype(str)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
            df['pe_ttm'] = pd.to_numeric(df['pe_ttm'], errors='coerce')
            
            self.df_all = df
            return True
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            return False

    def analyze_kingkong(self):
        """分析金刚配置 (Part A)"""
        print("🛡️ [2/3] 分析金刚配置...")
        results = []
        codes = list(PORTFOLIO_CFG.keys())
        
        # 从全市场数据中提取关注列表
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()
        
        for _, row in target_df.iterrows():
            code = row['symbol']
            cfg = PORTFOLIO_CFG.get(code)
            price = row['price']
            
            # 计算指标
            current_yield = (cfg['dps'] / price * 100) if price > 0 else 0
            spread = current_yield - self.bond_yield
            
            # 状态判定
            status = "😐"
            if cfg['strategy'] == 'bond':
                if spread >= 1.5: status = "💎 低估"
                elif spread >= 0.5: status = "✅ 合理"
                else: status = "⚠️ 略贵"
            else:
                pe = row['pe_ttm']
                if pe > 0 and pe < 20: status = "✅ 击球区"
                elif pe > 35: status = "⚠️ 过热"
            
            results.append({
                "name": cfg['name'], "role": cfg['role'], "price": price,
                "yield": round(current_yield, 2), "spread": round(spread, 2),
                "status": status, "change": row['change']
            })
        return results

    def analyze_chenye(self):
        """分析晨爷策略 (Part B)"""
        print("🏴‍☠️ [3/3] 扫描晨爷潜伏标的 (需耗时约30秒)...")
        results = []
        
        # 1. 粗筛 (漏斗模型)
        df = self.df_all.copy()
        # 排除ST/退市/北交所
        df = df[~df['name'].str.contains('ST|退|北')]
        # 排除大市值 & 高价 & 极低价
        df = df[
            (df['market_cap'] < CHENYE_CFG['MAX_CAP_BILLION'] * 100000000) & 
            (df['price'] < CHENYE_CFG['MAX_PRICE']) & 
            (df['price'] > 2.5) 
        ]
        
        print(f"   初筛剩余: {len(df)} 只，开始取前80只计算历史位置...")
        
        # 为了防止GitHub超时/被封，只取按市值排序最小的前80个
        candidates = df.sort_values(by='market_cap').head(80)
        
        for _, row in candidates.iterrows():
            # 关键修复：增加0.3秒延时，防止触发反爬虫策略
            time.sleep(0.3)
            
            pos_data = self.calculate_position(row['symbol'], row['price'])
            if pos_data and pos_data['pos'] <= CHENYE_CFG['POSITION_THRESHOLD']:
                results.append({
                    "symbol": row['symbol'], "name": row['name'], 
                    "price": row['price'], "pos": pos_data['pos'],
                    "cap": round(row['market_cap'] / 100000000, 2)
                })
        
        # 按位置排序，取前10名
        return sorted(results, key=lambda x: x['pos'])[:10]

    def calculate_position(self, symbol, current_price):
        """辅助函数：计算单只股票历史位置"""
        end_date = self.today.strftime("%Y%m%d")
        start_date = (self.today - timedelta(days=365 * CHENYE_CFG['HISTORY_YEARS'])).strftime("%Y%m%d")
        
        try:
            # 获取日线
            df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
            if df.empty or len(df) < 100: return None
            
            high = df['最高'].max()
            low = df['最低'].min()
            
            if high == low: return None
            
            pos = round(((current_price - low) / (high - low)) * 100, 2)
            return {'pos': pos}
        except:
            return None

    def generate_report(self, kk_data, cy_data):
        quote = random.choice(QUOTES)
        date_str = self.today.strftime("%Y-%m-%d")
        
        msg = f"### 📊 融合策略日报 ({date_str})\n"
        msg += f"**今日心法**：*{quote}*\n"
        msg += f"**十年国债**：{self.bond_yield}%\n\n"
        
        # Part A: 金刚配置
        msg += "#### 🛡️ 十五五·金刚配置\n"
        msg += "| 资产 | 现价 | 股息% | 股债差 | 状态 |\n"
        msg += "| :--- | :--- | :--- | :--- | :--- |\n"
        for item in kk_data:
            # 股息率高亮
            y_str = f"**{item['yield']}**" if item['yield'] > 4.0 else f"{item['yield']}"
            msg += f"| {item['role']} | {item['price']} | {y_str} | {item['spread']} | {item['status']} |\n"
            
        msg += "\n---\n"
        
        # Part B: 晨爷精选
        msg += "#### 🏴‍☠️ 晨爷潜伏 (3D战法)\n"
        if cy_data:
            msg += f"*标准：市值<{CHENYE_CFG['MAX_CAP_BILLION']}亿 | 单价<{CHENYE_CFG['MAX_PRICE']}元 | 位置<{CHENYE_CFG['POSITION_THRESHOLD']}%*\n"
            msg += "| 代码 | 名称 | 现价 | 位置% | 市值 |\n"
            msg += "| :--- | :--- | :--- | :--- | :--- |\n"
            for item in cy_data:
                msg += f"| {item['symbol']} | {item['name']} | {item['price']} | {item['pos']} | {item['cap']}亿 |\n"
            msg += "\n⚠️ *注：晨爷策略需人工复核[题材故事]与[上方压力]*"
        else:
            msg += "今日无符合严格标准的[潜伏]标的。"
            
        return msg

    def send_pushplus(self, title, content):
        # 1. 检查 Token 是否存在
        if not PUSHPLUS_TOKEN:
            print("⚠️ 未配置 PUSHPLUS_TOKEN，仅打印日志")
            print(content)
            return

        # 2. 清洗逻辑（关键修复）：替换中文逗号 -> 分割 -> 去除空格
        tokens = PUSHPLUS_TOKEN.replace("，", ",").split(",")
        url = 'http://www.pushplus.plus/send'
        
        for token in tokens:
            t = token.strip()
            if not t: continue

            data = {
                "token": t, 
                "title": title, 
                "content": content, 
                "template": "markdown"
            }
            
            try:
                # 增加 timeout 防止卡死
                res = requests.post(url, json=data, timeout=10)
                print(f"✅ 微信推送结果 ({t[:4]}***): {res.json().get('msg')}")
            except Exception as e:
                print(f"❌ 推送网络异常: {e}")

if __name__ == "__main__":
    strategy = FusionStrategy()
    
    # 1. 获取数据
    if strategy.get_market_data():
        # 2. 跑两个策略
        kk_res = strategy.analyze_kingkong()
        cy_res = strategy.analyze_chenye()
        
        # 3. 生成并发送报告
        report = strategy.generate_report(kk_res, cy_res)
        strategy.send_pushplus("金刚+晨爷 | 融合日报", report)
