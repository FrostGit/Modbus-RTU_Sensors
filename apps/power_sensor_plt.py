#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""电源传感器实时绘图

- 驱动对象实例化一次、批量读 4 项参数（1 次 Modbus 往返）
- 每轮曲线同步对齐，单点失败记 None（曲线断口）
- 横轴为相对时间(秒)，保留最近 WINDOW 个采样点
"""

import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_BASE, os.path.join(_BASE, "core"), os.path.join(_BASE, "drivers")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import os
import time
from collections import deque

import matplotlib.pyplot as plt
from matplotlib import font_manager

from lib_ModbusRTUDevice import ModbusException
from power_sensor import PowerSensor

BASE_DIR = os.path.join(_BASE, "assets")
WINDOW = 300
PORT = "/dev/power_sensor"

my_font = font_manager.FontProperties(fname=os.path.join(BASE_DIR, "STSONG.TTF"))

FIELDS = [
    ("voltage", "电压", "V", "r"),
    ("current", "电流", "A", "g"),
    ("power", "功率", "W", "b"),
    ("energy", "累计电量", "Wh", "y"),
]

plt.ion()
fig, axes = plt.subplots(2, 2, figsize=(20, 12))
fig.suptitle("多模态数据采集平台-电源类传感器数据", fontsize=16, fontproperties=my_font)
plt.tight_layout(rect=[0, 0, 1, 0.96])

lines = {}
series = {}
for i, (key, title, unit, color) in enumerate(FIELDS):
    ax = axes[i // 2, i % 2]
    line, = ax.plot([], [], color + '-', linewidth=2)
    ax.set_title(title, fontproperties=my_font)
    ax.set_ylabel(unit, fontproperties=my_font)
    ax.grid(True, alpha=0.3)
    lines[key] = line
    series[key] = deque(maxlen=WINDOW)
times = deque(maxlen=WINDOW)

sensor = PowerSensor(serial_port=PORT, baudrate=9600, timeout=1)  # 实例化一次，全程复用

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
