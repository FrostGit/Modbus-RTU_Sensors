#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""空气（气象）传感器离线数据记录

实时采集 6 项气象参数并写入 CSV（含时间戳），同时实时绘图展示。

用法:
    python3 air_sensor_record.py                # 默认每 1 秒采一次
    python3 air_sensor_record.py --interval 2   # 每 2 秒采一次
    python3 air_sensor_record.py --out /tmp/air.csv

Ctrl+C 停止，自动关闭文件并打印统计。
"""

import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_BASE, os.path.join(_BASE, "core"), os.path.join(_BASE, "drivers")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse
import csv
import os
import sys
import time
from collections import deque
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib import font_manager

from air_sensor import Modbus_Air_Sensor
from lib_ModbusRTUDevice import ModbusException

BASE_DIR = os.path.join(_BASE, "assets")
WINDOW = 600  # 绘图保留最近 600 个采样点
FIELDS = ["temperature", "humidity", "dewpoint", "pressure", "altitude", "air_density"]

my_font = font_manager.FontProperties(fname=os.path.join(BASE_DIR, "STSONG.TTF"))


def parse_args():
    parser = argparse.ArgumentParser(description="气象传感器离线数据记录 (CSV)")
    parser.add_argument("--serial-port", default="/dev/weather_sensor",
                        help="串口路径 (默认 /dev/weather_sensor)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="采样间隔秒数 (默认 1.0)")
    parser.add_argument("--out", default=None,
                        help="CSV 输出路径 (默认 data/air_sensor_<时间戳>.csv)")
    return parser.parse_args()


def default_out_path():
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(data_dir, f"air_sensor_{ts}.csv")


def build_figure():
    """2x3 实时绘图面板，返回 (fig, axes, lines, series, times)"""
    plt.ion()
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle("多模态数据采集平台-天气类传感器数据", fontsize=16, fontproperties=my_font)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    titles = {
        "temperature": ("空气温度", "℃"),
        "humidity": ("空气湿度", "%"),
        "dewpoint": ("露点温度", "℃"),
        "pressure": ("大气压力", "hPa"),
        "altitude": ("海拔高度", "m"),
        "air_density": ("空气密度", "Kg/m³"),
    }
    lines = {}
    series = {f: deque(maxlen=WINDOW) for f in FIELDS}
    times = deque(maxlen=WINDOW)
    for i, field in enumerate(FIELDS):
        ax = axes[i // 3, i % 3]
        title, unit = titles[field]
        line, = ax.plot([], [], '-', linewidth=2)
        ax.set_title(title, fontproperties=my_font)
        ax.set_ylabel(unit, fontproperties=my_font)
        ax.grid(True, alpha=0.3)
        lines[field] = line
    return fig, axes, lines, series, times


def main():
    args = parse_args()
    out_path = args.out or default_out_path()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    sensor = Modbus_Air_Sensor(serial_port=args.serial_port)
    fig, axes, lines, series, times = build_figure()

    t0 = time.time()
    rows = 0
    fail_count = 0

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ts"] + FIELDS)
        writer.writeheader()

        print(f"开始记录 -> {out_path} (间隔 {args.interval}s, Ctrl+C 停止)")
        while True:
            try:
                now = time.time() - t0
                try:
                    data = sensor.read_all()  # 一次 Modbus 往返读全部 6 项
                except ModbusException as e:
                    print(f"Modbus 读取失败: {e}")
                    fail_count += 1
                    time.sleep(args.interval)
                    continue

                ts = datetime.now().isoformat(timespec="milliseconds")
                row = {"ts": ts, **{f: round(data.get(f), 3) for f in FIELDS}}
                writer.writerow(row)
                f.flush()  # 实时落盘，掉电/中断不丢数据
                rows += 1

                # 实时绘图（每轮追加一次时间戳，长度对齐）
                times.append(now)
                for field in FIELDS:
                    series[field].append(row[field])
                    lines[field].set_data(list(times), list(series[field]))
                for ax in axes.flat:
                    ax.relim()
                    ax.autoscale_view()
                fig.canvas.draw()
                fig.canvas.flush_events()

                print(f"[{rows:6d}] t={now:7.1f}s " +
                      ", ".join(f"{f}={row[f]}" for f in FIELDS))

            except KeyboardInterrupt:
                print("\n停止记录")
                break
            except Exception as e:
                print(f"其他异常: {e}")
                fail_count += 1
                time.sleep(1)

            time.sleep(args.interval)

    sensor.close()
    duration = time.time() - t0
    print(f"\n完成: 共 {rows} 行, 用时 {duration:.1f}s, 失败 {fail_count} 次")
    print(f"输出文件: {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"初始化失败: {e}")
        sys.exit(1)
