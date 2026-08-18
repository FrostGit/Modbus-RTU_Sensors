#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多模态传感器综合大屏（大表格展示）

覆盖 5 类传感器共 35 路曲线：
- 气体(HUB) 4 路 / 气象 6 路 / 电源 4 路 / 土壤 8 路 / 生命体征 13 路

设计要点：
- 驱动对象实例化一次、全程复用（不再每读一次 new+close 串口）
- 连续寄存器批量读：气象 6 / 土壤 8 / 电源 8 寄存器各 1 次 Modbus 往返
- 每轮所有曲线同步对齐；单类传感器失败记 None（曲线断口），不破坏整轮
- 横轴为相对时间(秒)，保留最近 WINDOW 个采样点（环形缓冲，内存有上限）

用法:
    python3 big_plt_demo.py
"""
import os
import time
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from PIL import Image

from air_sensor import Modbus_Air_Sensor
from heart_rate_sensor import HeartRateSensor
from lib_ModbusRTUDevice import ModbusException
from power_sensor import PowerSensor
from sensor_hub import Modbus_Sensor_Hub
from soil_sensor import Modbus_Soil_Sensor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WINDOW = 300  # 保留最近 300 个采样点

my_font = font_manager.FontProperties(fname=os.path.join(BASE_DIR, "STSONG.TTF"))

plt.ion()

# ---- 串口设备（与 udev 符号链接一致） ----
PORT_GAS_HUB = "/dev/gas_hub"
PORT_WEATHER = "/dev/weather_sensor"
PORT_SOIL = "/dev/soil_sensor"
PORT_POWER = "/dev/power_sensor"
PORT_VITAL = "/dev/vital_signs"

# ---- 曲线定义: key -> (标题, 单位, 颜色) ----
CURVES = {
    # 气体 4
    "smoke": ("烟雾传感器", "ppm", "r"),
    "co2": ("二氧化碳传感器", "ppm", "g"),
    "o2": ("氧气传感器", "%VOL", "b"),
    "ch4": ("甲烷传感器", "%LEL", "y"),
    # 气象 6
    "temperature": ("空气温度", "℃", "c"),
    "humidity": ("空气湿度", "%", "m"),
    "dewpoint": ("露点温度", "℃", "r"),
    "pressure": ("大气压力", "hPa", "g"),
    "altitude": ("海拔高度", "m", "b"),
    "air_density": ("空气密度", "Kg/m³", "k"),
    # 电源 4
    "voltage": ("电压", "V", "r"),
    "power": ("功率", "W", "g"),
    "current": ("电流", "A", "k"),
    "energy": ("电量", "Wh", "r"),
    # 土壤 8
    "soil_moisture": ("土壤湿度", "%", "m"),
    "soil_ec": ("土壤电导率", "µS/cm", "r"),
    "soil_salty": ("土壤盐分", "mg/L", "g"),
    "soil_nitro": ("土壤氮含量", "mg/kg", "b"),
    "soil_phosphorus": ("土壤磷含量", "mg/kg", "y"),
    "soil_potassium": ("土壤钾含量", "mg/kg", "c"),
    "soil_ph": ("土壤PH值", "pH", "m"),
    "soil_temp": ("土壤温度", "℃", "r"),
    # 生命体征 13
    "heart_rate": ("心率", "bpm", "r"),
    "spo2": ("血氧", "%", "g"),
    "bk": ("微循环", "", "b"),
    "fatigue_index": ("疲劳指数", "", "y"),
    "systolic_pressure": ("收缩压", "mmHg", "c"),
    "diastolic_pressure": ("舒张压", "mmHg", "k"),
    "cardiac_output": ("心输出", "", "r"),
    "peripheral_resistance": ("外周阻力", "", "g"),
    "rr_variability": ("RR变异性", "", "b"),
    "sdnn": ("SDNN", "ms", "y"),
    "rmssd": ("RMSSD", "ms", "c"),
    "nn50": ("NN50", "", "k"),
    "pnn50": ("PNN50", "%", "r"),
}

# ---- 布局: 5 行 x 8 列；(1,3) logo 图、(1,4) title 图，(4,5)-(4,7) 留空 ----
PLACEMENT = [
    (0, 0, "smoke"), (0, 1, "co2"), (0, 2, "o2"), (0, 3, "ch4"),
    (0, 4, "temperature"), (0, 5, "humidity"), (0, 6, "voltage"), (0, 7, "power"),
    (1, 0, "dewpoint"), (1, 1, "pressure"), (1, 2, "altitude"),
    (1, 5, "soil_moisture"), (1, 6, "current"), (1, 7, "energy"),
    (2, 0, "soil_ec"), (2, 1, "soil_salty"), (2, 2, "soil_nitro"),
    (2, 3, "soil_phosphorus"), (2, 4, "soil_potassium"), (2, 5, "soil_ph"),
    (2, 6, "air_density"), (2, 7, "soil_temp"),
    (3, 0, "heart_rate"), (3, 1, "spo2"), (3, 2, "bk"), (3, 3, "fatigue_index"),
    (3, 4, "systolic_pressure"), (3, 5, "diastolic_pressure"),
    (3, 6, "cardiac_output"), (3, 7, "peripheral_resistance"),
    (4, 0, "rr_variability"), (4, 1, "sdnn"), (4, 2, "rmssd"),
    (4, 3, "nn50"), (4, 4, "pnn50"),
]


def build_figure():
    """创建 5x8 大表格并返回 (fig, axes, lines, series, times)"""
    fig, axes = plt.subplots(5, 8, figsize=(24, 16))
    plt.tight_layout(rect=[0, 0, 1, 0.98])

    lines = {}
    series = {key: deque(maxlen=WINDOW) for key in CURVES}
    times = deque(maxlen=WINDOW)

    for row, col, key in PLACEMENT:
        title, unit, color = CURVES[key]
        ax = axes[row, col]
        line, = ax.plot([], [], color + '-', linewidth=2)
        ax.set_title(title, fontproperties=my_font)
        ax.set_ylabel(unit, fontproperties=my_font)
        ax.grid(True, alpha=0.3)
        lines[key] = line

    # 图片占位
    axes[1, 3].axis('off')
    axes[1, 3].imshow(np.array(Image.open(os.path.join(BASE_DIR, "logo.jpg"))))
    axes[1, 4].axis('off')
    axes[1, 4].imshow(np.array(Image.open(os.path.join(BASE_DIR, "title.png"))))
    for col in range(5, 8):
        axes[4, col].axis('off')

    return fig, axes, lines, series, times


def init_sensors():
    """实例化驱动对象（一次创建，全程复用；失败不影响其他传感器）"""
    sensors = {}
    try:
        sensors["gas"] = Modbus_Sensor_Hub(serial_port=PORT_GAS_HUB)
        print("气体传感器已加载 (gas_hub, 4800bps)")
    except Exception as e:
        print(f"气体传感器加载失败: {e}")
    try:
        sensors["air"] = Modbus_Air_Sensor(serial_port=PORT_WEATHER)
        print("气象传感器已加载 (weather_sensor, 9600bps)")
    except Exception as e:
        print(f"气象传感器加载失败: {e}")
    try:
        sensors["power"] = PowerSensor(serial_port=PORT_POWER, baudrate=9600, timeout=1)
        print("电源传感器已加载 (power_sensor, 9600bps)")
    except Exception as e:
        print(f"电源传感器加载失败: {e}")
    try:
        sensors["soil"] = Modbus_Soil_Sensor(serial_port=PORT_SOIL)
        print("土壤传感器已加载 (soil_sensor, 9600bps)")
    except Exception as e:
        print(f"土壤传感器加载失败: {e}")
    try:
        vital = HeartRateSensor(serial_port=PORT_VITAL, baudrate=38400, timeout=1)
        vital.send_command(vital.CMD_MODE_WORK)  # 开启工作模式
        sensors["vital"] = vital
        print("生命体征传感器已加载 (vital_signs, 38400bps)")
    except Exception as e:
        print(f"生命体征传感器加载失败: {e}")
    return sensors


def main():
    fig, axes, lines, series, times = build_figure()
    sensors = init_sensors()

    vital_cache = {}
    t0 = time.time()

    print("开始采集，按 Ctrl+C 退出...")
    while True:
        try:
            now = time.time() - t0
            values = {}

            # 气体：4 个从站地址不同，逐个读（失败则该类记 None）
            if sensors.get("gas"):
                try:
                    values.update(sensors["gas"].read_all())
                except ModbusException as e:
                    print(f"气体读取失败: {e}")

            # 气象：一次批量读 6 寄存器
            if sensors.get("air"):
                try:
                    values.update(sensors["air"].read_all())
                except ModbusException as e:
                    print(f"气象读取失败: {e}")

            # 电源：一次批量读 8 寄存器（4 个 32 位值）
            if sensors.get("power"):
                try:
                    values.update(sensors["power"].read_all())
                except ModbusException as e:
                    print(f"电源读取失败: {e}")

            # 土壤：一次批量读 8 寄存器
            if sensors.get("soil"):
                try:
                    values.update(sensors["soil"].read_all())
                except ModbusException as e:
                    print(f"土壤读取失败: {e}")

            # 生命体征：流式主动上报，读不到新包时沿用上次缓存值
            if sensors.get("vital"):
                try:
                    pkt = sensors["vital"].read_packet(timeout_s=0.3)
                    if pkt:
                        vital_cache = {
                            "heart_rate": pkt.heart_rate,
                            "spo2": pkt.spo2,
                            "bk": pkt.bk,
                            "fatigue_index": pkt.fatigue_index,
                            "systolic_pressure": pkt.systolic_pressure,
                            "diastolic_pressure": pkt.diastolic_pressure,
                            "cardiac_output": pkt.cardiac_output,
                            "peripheral_resistance": pkt.peripheral_resistance,
                            "rr_variability": pkt.rr_variability,
                            "sdnn": pkt.sdnn,
                            "rmssd": pkt.rmssd,
                            "nn50": pkt.nn50,
                            "pnn50": pkt.pnn50,
                        }
                except Exception as e:
                    print(f"生命体征读取失败: {e}")
                values.update(vital_cache)

            # 每轮只追加一次时间戳，所有曲线长度保持一致
            times.append(now)
            for key in CURVES:
                series[key].append(values.get(key))  # 缺失记 None，曲线断口
                lines[key].set_data(list(times), list(series[key]))

            for ax in axes.flat:
                ax.relim()
                ax.autoscale_view()

            fig.canvas.draw()
            fig.canvas.flush_events()

            print(f"采样 #{len(times)} t={now:.2f}s")
            time.sleep(0.05)  # 避免空转忙等

        except KeyboardInterrupt:
            print("\n退出采集")
            break
        except Exception as e:
            print(f"其他异常: {e}")
            time.sleep(1)

    # 退出前释放驱动
    for dev in sensors.values():
        try:
            dev.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
