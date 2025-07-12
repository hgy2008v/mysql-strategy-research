import akshare as ak
import tushare as ts
import pandas as pd
#import talib
import download_stock_daily

# 全局变量
pro = None

def init_tushare():
    """初始化 Tushare API"""
    global pro
    if pro is None:
        ts.set_token('dd29d91ca9f8577814389ee9e722991fe05df214e1755d82702f956d')
        pro = ts.pro_api()
    return pro

# 设置pandas显示所有列
#pd.set_option('display.max_columns', None)

#取000001的后复权行情
#df = ts.pro_bar(ts_code='000001.SZ', start_date="20230101", end_date="20250314", factors=['tor', 'vr'])

#df = ak.stock_zh_a_spot_em() 
#print(df)

# 获取股票日线数据
#data = ak.stock_zh_a_daily(symbol="sz000001", start_date="20230101", end_date="20250313", adjust="qfq")

# 查看数据结构
#print("Columns:", data.columns.tolist())
#print("First row:", data.iloc[0].to_dict())
#print("Data types:", data.dtypes)
#print(data)


#获取单个股票数据
#df = pro.moneyflow(ts_code='300059.SZ', start_date='20230101', end_date='20250314')
#print(df)
#df.to_csv('300059.csv', index=False)

#stock_individual_fund_flow_df = ak.stock_individual_fund_flow(stock="000001", market="sz")
#print(stock_individual_fund_flow_df)
#stock_individual_fund_flow_df.to_csv('000001sz.csv', index=False)

#df=pro.download_concept_data()

# 初始化 tushare
pro = init_tushare()

df = pro.index_daily(ts_code='399101.SZ')
print(df)
df.to_csv('399101.csv', index=False)





