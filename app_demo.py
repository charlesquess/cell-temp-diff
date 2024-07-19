import time
import json
import requests
import pandas as pd
from functools import reduce
import plotly.graph_objects as go
from load_data import *
import streamlit as st

# Streamlit 的UI部分
st.title("焦耳矿机数据分析")
col1, col2, col3, col4 = st.columns(4)
with col1:
    # 日期选择组件
    start_date = st.date_input("选择开始日期", pd.to_datetime("2024-07-15"))
with col2:
    # 时间选择组件
    start_time = st.time_input("选择开始时间", pd.to_datetime("00:00:00").time())
with col3:
    # 日期选择组件 2
    end_date = st.date_input("选择结束日期", pd.to_datetime("2024-07-18"))
with col4:
    # 时间选择组件 2
    end_time = st.time_input("选择结束时间", pd.to_datetime("23:59:00").time())

# 将日期和时间组合成字符串
start_datetime = f"{start_date} {start_time}"
end_datetime = f"{end_date} {end_time}"

# 日期时间字符串转换为时间戳
def get_datetime_stamp(datetime_str):
    time_array = time.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    time_stamp = int(time.mktime(time_array)) * 1000  # 转换为毫秒
    return time_stamp

start_ts = get_datetime_stamp(start_datetime)
end_ts = get_datetime_stamp(end_datetime)

url = "http://energyscene.zenergyai.com:38080/api/"
payload = json.dumps({"username": "zenergy@zenergy.ai", "password": "ZEnergy.Ai2312"})
response = requests.post(f"{url}auth/login", data=payload)
token = response.json()["token"]

device_df = pd.read_csv('data/ThingsBoardDevice.csv')
device_df.set_index('ProjectId', inplace=True)

# dic 列表
@st.cache_data
def load_data():
    dic = {}
    for index, row in device_df.iterrows():
        # 请求参数
        device_id = row['Eb-DeviceId']
        keys = "maxcell_t, mincell_t, avecellt"
        # 发出请求
        response = requests.get(
            f"{url}plugins/telemetry/DEVICE/{device_id}/values/timeseries",
            headers={"X-Authorization": f"Bearer {token}"},
            params={"keys": keys.replace(" ", ""),
                    "startTs": start_ts,
                    "endTs": end_ts,
                    "interval": 60000,
                    "limit": 50000,
                    "agg": "NONE"})
        json = response.json()
        if json == {}:
            continue
        # 转换为 DataFrame
        dfs = []
        for key, value in json.items():
            df = pd.DataFrame(value)
            df['value'] = df['value'].astype(float)  # value 列转换类型
            df.rename(columns={'value': key}, inplace=True)  # 重命名列名
            dfs.append(df)  # 添加到列表
        # 合并数据
        df = reduce(lambda x, y: pd.merge(x, y, on="ts", how="outer"), dfs)
        df['ts'] = pd.to_datetime(df['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')  # 转换时间戳
        df.rename(columns={'maxcell_t': 'max', 'mincell_t': 'min', 'avecellt': 'avg'}, inplace=True)  # 重命名列名
        df["diff"] = df['max'] - df['min']  # 计算温差
        df = df[(df['max'] > 0) & (df['min'] > 0) & (df['avg'] > 0) & (df['diff'] >= 0)]  # 过滤无效数据
        df.set_index('ts', inplace=True)  # 设置索引
        df.sort_index(inplace=True)  # 按时间排序
        # df.ffill(inplace=True)  # 前向填充
        # 添加到字典
        dic[index] = df
    return dic

def plot_data(dic,idea):
    # 绘图
    fig = go.Figure()
    fig.update_xaxes(title_text = 'ts')
    fig.update_yaxes(title_text = idea)
    for key, value in dic.items():
        fig.add_trace(go.Scatter(x=value.index, y=value[idea], mode='lines+markers', name=f"{key}-{idea}"))
    return fig

# 加载数据
dic = load_data()

# 获取焦耳矿机名称列表
device_names = device_df.index.tolist()

# 使用下拉复选框选择焦耳矿机
selected_devices = st.multiselect("请选择：焦耳矿机编号", device_names)

# 添加确认按钮
if st.button('确认选择'):
    if selected_devices:
        # 根据选择的焦耳矿机创建 current_dic
        current_dic = {key: value for key, value in dic.items() if key in selected_devices}

        # 绘图
        fig = plot_data(current_dic,'diff')
        fig.update_layout(title_text="所选焦耳矿机温差")
        st.plotly_chart(fig)

        # 绘图
        fig_2 = plot_data(current_dic,'avg')
        fig_2.update_layout(title_text="所选焦耳矿机平均温度")
        st.plotly_chart(fig_2)    

        # 绘图
        fig_3 = plot_data(current_dic,'min')
        fig_3.update_layout(title_text="所选焦耳矿机最低温度")
        st.plotly_chart(fig_3)

        # 绘图
        fig_4 = plot_data(current_dic,'max')
        fig_4.update_layout(title_text="所选焦耳矿机最高温度")
        st.plotly_chart(fig_4)

    else:
        st.write("请选择焦耳矿机进行数据分析")

