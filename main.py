```python
import akshare as ak
import pandas as pd
import requests
import os
import random
from datetime import datetime, timedelta

# ========================= 环境变量 =========================
# 只需要配置 PUSHPLUS_TOKEN 即可
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")

# ========================= 1. 金刚配置 (核心持仓) =========================
QUOTES = [
    "“长江的水，神华的煤，广核的电，茅台的酒。这是中国最硬的物理资产。”",
    "“太贵了就不买，哪怕它涨到天上去。错失不是亏损。”",
    "“不要羡慕泡沫，泡沫破裂时，只有我们的水电站还在印钞。”",
    "“只做升级，不做轮动。看不懂的钱不赚，太贵的货不买。”",
    "“真正的风控，是买入那个 30 年后肯定还在的公司。”"
]

PORTFOLIO_CFG = {
    "600900": {"name": "长江电力","role": "🏔️ 养老基石","dps": 0.95,"strategy": "bond",
               "key_metric": "股息率","mental_check": "它负责兜底。只要跌下来，就是加仓送分题。"},
    "601088": {"name": "中国神华","role": "⚫️ 能源底座","dps": 2.62,"strategy": "bond",
               "key_metric": "股息率","mental_check": "家里有矿，心中不慌。高位不追，回调加仓。"},
    "601006": {"name": "大秦铁路","role": "🛤️ 国家存折","dps": 0.44,"strategy": "bond",
               "key_metric": "股息率","mental_check": "这是甚至不需要看K线的股票。把它当成永续债。"},
    "601985": {"name": "中国核电","role": "⚛️ 绿色引擎","dps": 0.17,"strategy": "growth",
               "key_metric": "PE(TTM)","mental_check": "还在长身体的孩子。工资定投的首选对象。"},
    "600519": {"name": "贵州茅台","role": "👑 A股之王","dps": 30.8,"strategy": "value",
               "key_metric": "PE(TTM)","mental_check": "它是社交货币。跌破1400是上帝给的礼物。"},
    "000858": {"name": "五粮液","role": "🍷 价值前锋","dps": 4.67,"strategy": "value",
               "key_metric": "PE(TTM)","mental_check": "这是翻身仗。110左右极度低估，125以下只买不卖。"},
    "000333": {"name": "美的集团","role": "🤖 全球制造","dps": 3.0,"strategy": "growth",
               "key_metric": "PE(TTM)","mental_check": "代替京沪高铁和紫金，中国制造业巅峰。"},
    "000568": {"name": "泸州老窖","role": "🚀 进攻核心","dps": 6.30,"strategy": "offensive",
               "key_metric": "PE(TTM)","mental_check": "5.4%股息率是保底，PE 12倍是期权。"},
    "002415": {"name": "海康威视","role": "📹 智能监控","dps": 0.40,"strategy": "growth",
               "key_metric": "PE(TTM)","mental_check": "专注全球安防与AI增长，估值合理时是长期定投标的。"}
}

# ========================= 2. 晨爷配置 (潜伏策略) =========================
CHENYE_CFG = {
    "MAX_PRICE": 15.0,        # 价格上限
    "MAX_CAP_BILLION": 60,    # 市值上限(亿)
    "POSITION_THRESHOLD": 20, # 位置水位(%) (当前价在近4年区间的百分比)
    "HISTORY_YEARS": 4        # 回溯历史(年)
}

class AutoStrategy:
    def __init__(self):
        self.portfolio = PORTFOLIO_CFG
        self.today = datetime.now()
        self.bond_yield = 2.10  # 十年期国债收益率锚
        self.df_all = None

    def get_market_status(self):
        month = self.today.month
        msg, color = "📅 资产积累期", "#666"
        if month == 3: msg, color = "🇨🇳 两会/安全月", "#d93025"
        elif month == 4: msg, color = "📊 财报体检期", "#f39c12"
        elif month in [1, 2]: msg, color = "🧧 消费/春运旺季", "#d93025"
        elif month in [6, 7]: msg, color = "💰 分红复投期", "#188038"
        return msg, color

    def get_all_data(self):
        """一次性拉取全市场数据"""
        try:
            print("📡 拉取全市场实时行情...")
            df = ak.stock_zh_a_spot_em()
            # 统一列名，方便后续处理
            df = df.rename(columns={
                '代码': 'symbol', '名称': 'name', '最新价': 'price', 
                '总市值': 'market_cap', '市盈率-动态': 'pe_ttm', '涨跌幅': 'change'
            })
            # 数据清洗，确保全是数字
            df['symbol'] = df['symbol'].astype(str)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
            df['pe_ttm'] = pd.to_numeric(df['pe_ttm'], errors='coerce')
            self.df_all = df
            return True
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            return False

    def analyze_portfolio(self):
        """分析金刚配置"""
        if self.df_all is None: return []
        print("🛡️ 分析金刚配置...")
        results = []
        codes = list(self.portfolio.keys())
        # 筛选出我们的持仓
        target_df = self.df_all[self.df_all['symbol'].isin(codes)].copy()

        for _, row in target_df.iterrows():
            code = row['symbol']
            cfg = self.portfolio.get(code)
            price = row['price']
            
            # 计算股息率和利差
            current_yield = (cfg['dps'] / price * 100) if price > 0 else 0
            spread = current_yield - self.bond_yield
            
            # 简单状态评级
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
                "status": status, "mental": cfg.get('mental_check', '')
            })
        return results

    def scan_chenye(self):
        """扫描晨爷策略"""
        if self.df_all is None: return []
        print("🏴‍☠️ 扫描晨爷潜伏标的...")
        
        # 1. 粗筛：排除ST，限制市值和价格
        df = self.df_all.copy()
        # 排除 ST、退市、北交所(简单排除8/4/3开头的)
        df = df[~df['name'].str.contains('ST|退')]
        df = df[~df['symbol'].str.startswith(('8', '4', '92'))] 

        df = df[
            (df['market_cap'] < CHENYE_CFG['MAX_CAP_BILLION'] * 100000000) & 
            (df['price'] < CHENYE_CFG['MAX_PRICE']) & 
            (df['price'] > 2.0) # 排除过低垃圾股
        ]
        
        # 2. 性能优化：只取市值最小的前 50 个去算历史位置，防止 Action 超时
        candidates = df.sort_values(by='market_cap').head(50)
        results = []

        end_date = self.today.strftime("%Y%m%d")
        start_date = (self.today - timedelta(days=365 * CHENYE_CFG['HISTORY_YEARS'])).strftime("%Y%m%d")

        print(f"🔍 正在深入分析 {len(candidates)} 只候选股...")
        for _, row in candidates.iterrows():
            try:
                # 获取个股历史数据
                hist = ak.stock_zh_a_hist(symbol=row['symbol'], start_date=start_date, end_date=end_date, adjust="qfq")
                if hist.empty or len(hist) < 100: continue
                
                high = hist['最高'].max()
                low = hist['最低'].min()
                if high == low: continue
                
                # 计算目前价格在历史区间的位置 (0% = 历史最低, 100% = 历史最高)
                pos = round(((row['price'] - low) / (high - low)) * 100, 2)
                
                if pos <= CHENYE_CFG['POSITION_THRESHOLD']:
                    results.append({
                        "symbol": row['symbol'], "name": row['name'], 
                        "price": row['price'], "pos": pos,
                        "cap": round(row['market_cap']/100000000, 2)
                    })
            except:
                continue
        
        # 按位置越低越好排序，取前10
        return sorted(results, key=lambda x: x['pos'])[:10]

    def run(self):
        # 1. 获取数据
        if not self.get_all_data():
            return "❌ 行情数据获取失败，请检查 AKShare 接口"

        # 2. 执行分析
        kk_res = self.analyze_portfolio()
        cy_res = self.scan_chenye()
        
        # 3. 准备文案
        quote = random.choice(QUOTES)
        mkt_msg, mkt_color = self.get_market_status()
        
        # 4. 生成 HTML (适配 PushPlus)
        html = f"""
        
            
                📊 策略日报 {self.today.strftime('%m-%d')}
            

            
                {quote}

                📅 阶段: {mkt_msg} | ⚓ 国债: {self.bond_yield}%

            

            
            🛡️ 金刚配置 (防守)

            
        """
        
        for item in kk_res:
            # 简单的行样式
            status_color = "#d93025" if "低估" in item['status'] or "击球" in item['status'] else "#28a745"
            html += f"""
                
            """
        html += "
                
                    资产

                    现价

                    股息%

                    评价

                

                    
                        {item['name']}

                        {item['role']}
                    

                    {item['price']}

                    {item['yield']}

                    {item['status']}

                
"

        html += """
            🏴‍☠️ 晨爷潜伏 (进攻)

            筛选: 市值<60亿 | 单价<15 | 4年位置<20%

            
        """
        
        if cy_res:
            for item in cy_res:
                html += f"""
                
                """
        else:
            html += ""
        
        html += """
            
                
                    代码/名称

                    现价

                    位置

                    市值

                

                    
                        {item['name']}

                        {item['symbol']}
                    

                    {item['price']}

                    {item['pos']}%

                    {item['cap']}亿

                
😴 今日无符合严格标准的标的

            
                AutoStrategy via GitHub Actions
            

        

        """
        
        return html

def send_pushplus(title, content):
    """发送 PushPlus 通知 (核心修复部分)"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN，无法发送通知")
        return
    
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html"  # 指定发送 HTML 格式
    }
    
    try:
        response = requests.post(url, json=data)
        res_json = response.json()
        if res_json.get("code") == 200:
            print("✅ PushPlus 发送成功")
        else:
            print(f"❌ PushPlus 发送失败: {res_json.get('msg')}")
    except Exception as e:
        print(f"❌ 网络发送异常: {e}")

if __name__ == "__main__":
    print("🚀 启动策略分析...")
    
    # 1. 实例化策略
    strategy = AutoStrategy()
    
    # 2. 运行并获取 HTML 内容
    content = strategy.run()
    
    # 3. 发送 PushPlus
    if content:
        title = f"复盘日报 {datetime.now().strftime('%m-%d')}"
        send_pushplus(title, content)
    
    print("🏁 任务完成")
```