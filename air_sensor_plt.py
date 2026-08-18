#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""气象传感器实时绘图

- 驱动对象实例化一次、批量读 6 项参数（1 次 Modbus 往返）
- 每轮曲线同步对齐，单点失败记 None（曲线断口）
- 横轴为相对时间(秒)，保留最近 WINDOW 个采样点
"""
import os
import time
from collections import deque

import matplotlib.pyplot as plt
from matplotlib import font_manager

from air_sensor import Modbus_Air_Sensor
from lib_ModbusRTUDevice import ModbusException

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WINDOW = 300
PORT = "/dev/weather_sensor"

my_font = font_manager.FontProperties(fname=os.path.join(BASE_DIR, "STSONG.TTF"))

FIELDS = [
    ("temperature", "空气温度", "℃", "r"),
    ("humidity", "空气湿度", "%", "g"),
    ("dewpoint", "露点温度", "℃", "b"),
    ("pressure", "大气压力", "hPa", "y"),
    ("altitude", "海拔高度", "m", "c"),
    ("air_density", "空气密度", "Kg/m³", "m"),
]

plt.ion()
fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle("多模态数据采集平台-天气类传感器数据", fontsize=16, fontproperties=my_font)
plt.tight_layout(rect=[0, 0, 1, 0.96])

lines = {}
series = {}
for i, (key, title, unit, color) in enumerate(FIELDS):
    ax = axes[i // 3, i % 3]
    line, = ax.plot([], [], color + '-', linewidth=2)
    ax.set_title(title, fontproperties=my_font)
    ax.set_ylabel(unit, fontproperties=my_font)
    ax.grid(True, alpha=0.3)
    lines[key] = line
    series[key] = deque(maxlen=WINDOW)
times = deque(maxlen=WINDOW)

sensor = Modbus_Air_Sensor(serial_port=PORT)  # 实例化一次，全程复用

t0 = time.time()
while True:
    try:
        now = time.time() - t0
        try:
            data = sensor.read_all()
        except ModbusException as e:
            print(f"Modbus 读取失败: {e}")
            data = None

        times.append(now)  # 每轮只追加一次，所有曲线长度保持一致
        for key, _, _, _ in FIELDS:
            series[key].append(data.get(key) if data else None)
            lines[key].set_data(list(times), list(series[key]))

        for ax in axes.flat:
            ax.relim()
            ax.autoscale_view()
        fig.canvas.draw()
        fig.canvas.flush_events()

        print(f"采样 #{len(times)} t={now:.2f}s")
        time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n退出")
        break
    except Exception as e:
        print(f"其他异常: {e}")
        time.sleep(1)

sensor.close()
