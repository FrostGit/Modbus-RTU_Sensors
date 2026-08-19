#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生命体征波形快速显示

- 上：脉搏波(acdata 64点/帧)滚动波形，固定 y 范围 -128~127
- 下：RR 间期散点（每包 6 个 rra 值，滚动最近 N 个）
- 右上角：心率 / 血氧 大字

数据量小（单帧 64 点），整帧重绘即可达到快速刷新；串口 38400bps 流式上报。

用法:
    python3 heart_wave_plt.py
    python3 heart_wave_plt.py --port /dev/vital_signs
"""

import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_BASE, os.path.join(_BASE, "core"), os.path.join(_BASE, "drivers")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse
import time
from collections import deque

import matplotlib.pyplot as plt

from heart_rate_sensor import HeartRateSensor

WAVE_MAX = 640    # 滚动波形保留点数（10 帧）
RR_MAX = 60       # RR 散点保留点数
FRAME = 64        # 每帧波形点数


def parse_args():
    parser = argparse.ArgumentParser(description="生命体征波形快速显示")
    parser.add_argument("--port", default="/dev/vital_signs", help="串口路径")
    parser.add_argument("--baudrate", type=int, default=38400)
    return parser.parse_args()


def main():
    args = parse_args()
    sensor = HeartRateSensor(serial_port=args.port, baudrate=args.baudrate, timeout=1)
    sensor.send_command(sensor.CMD_MODE_WORK)

    wave = deque(maxlen=WAVE_MAX)   # 波形采样点（连续帧拼接）
    rrs = deque(maxlen=RR_MAX)      # RR 间期序列

    fig, (ax_wave, ax_rr) = plt.subplots(2, 1, figsize=(16, 9),
                                         gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle("生命体征-脉搏波 / RR间期", fontsize=14)

    ax_wave.set_ylim(-130, 130)
    ax_wave.grid(True, alpha=0.3)
    wave_line, = ax_wave.plot([], [], 'r-', linewidth=1.5)
    hr_text = ax_wave.text(0.98, 0.92, "", transform=ax_wave.transAxes,
                           ha='right', va='top', fontsize=18, color='crimson')

    ax_rr.set_ylim(0, 2000)
    ax_rr.grid(True, alpha=0.3)
    rr_scatter = ax_rr.scatter([], [], s=20, c='g')

    print("开始显示，Ctrl+C 退出...")
    t0 = time.time()
    frames = 0
    try:
        while True:
            pkt = sensor.read_packet(timeout_s=0.05)
            if pkt:
                wave.extend(pkt.acdata)
                rrs.extend(pkt.rra)
                frames += 1

                xs = list(range(len(wave)))
                wave_line.set_data(xs, list(wave))
                rr_scatter.set_offsets(list(zip(range(len(rrs)), rrs)))
                hr_text.set_text(f"心率 {pkt.heart_rate} bpm   血氧 {pkt.spo2}%")
                ax_wave.set_xlim(max(0, len(wave) - WAVE_MAX), len(wave))
                ax_rr.set_xlim(max(0, len(rrs) - RR_MAX), len(rrs))

                fig.canvas.draw()
                fig.canvas.flush_events()

                if frames % 20 == 0:
                    print(f"[{frames}帧] 心率 {pkt.heart_rate} bpm 血氧 {pkt.spo2}% "
                          f"耗时 {time.time() - t0:.1f}s")
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        try:
            sensor.send_command(sensor.CMD_MODE_STANDBY)
        except Exception:
            pass
        sensor.close()


if __name__ == "__main__":
    main()
