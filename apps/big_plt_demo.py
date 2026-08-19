#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多模态传感器综合大屏（本地 matplotlib）

展示内容：
- 折线 19 路：气体4 / 气象5 / 电源3 / 土壤5 / 生命体征2(心率·血氧)
- 数字卡片 5 个：累计电量 / 海拔 / 土壤氮磷钾
（生命体征其余 11 项不做本地展示，仅在 web 端以卡片呈现）

设计要点：
- 采集逻辑共用 sensor_acq（与 web_dashboard 同一套 read_all）
- 朴素整帧重绘 + --draw-every 节流（X3 ARM 整帧约 1s，采集一轮约 330ms）
- 单类失败记 None（曲线断口/卡片"--"），不破坏整轮

用法:
    python3 big_plt_demo.py
    python3 big_plt_demo.py --draw-every 2    # 每2轮采集重绘一次(X3建议)
"""

import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_BASE, os.path.join(_BASE, "core"), os.path.join(_BASE, "drivers")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse
import os
import time
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from PIL import Image

from sensor_acq import (CARD_CHANNELS, CARD_KEYS, LINE_CHANNELS, LINE_PLACEMENT,
                        init_sensors, read_round)

BASE_DIR = os.path.join(_BASE, "assets")
WINDOW = 300      # 保留最近 300 个采样点
DRAW_EVERY = 1    # 每 N 轮采集重绘一次

my_font = font_manager.FontProperties(fname=os.path.join(BASE_DIR, "STSONG.TTF"), size=10)

plt.ion()


def parse_args():
    parser = argparse.ArgumentParser(description="多模态传感器综合大屏")
    parser.add_argument("--draw-every", type=int, default=DRAW_EVERY,
                        help="每 N 轮采集重绘一次（X3 上建议 2~3）")
    parser.add_argument("--window", type=int, default=WINDOW,
                        help="保留最近 N 个采样点（默认 300）")
    parser.add_argument("--interval", type=float, default=0.05,
                        help="每轮间额外休眠秒数（默认 0.05）")
    return parser.parse_args()


def build_figure(window):
    """5x5 布局：0-3 行折线(19路+logo)，第 4 行数字卡片(5个)"""
    fig, axes = plt.subplots(5, 5, figsize=(22, 16))
    plt.tight_layout(rect=[0, 0, 1, 0.98])

    lines = {}
    series = {key: deque(maxlen=window) for key in LINE_CHANNELS}
    times = deque(maxlen=window)

    for row, col, key in LINE_PLACEMENT:
        title, unit, color = LINE_CHANNELS[key]
        ax = axes[row, col]
        line, = ax.plot([], [], color + '-', linewidth=2)
        ax.set_title(f"{title} ({unit})" if unit else title,
                     fontproperties=my_font, fontsize=10)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.3)
        lines[key] = line

    # logo 占位
    axes[3, 4].axis('off')
    axes[3, 4].imshow(np.array(Image.open(os.path.join(BASE_DIR, "logo.jpg"))))

    # 第 4 行：数字卡片
    cards = {}  # key -> (ax, text)
    for i, key in enumerate(CARD_KEYS):
        title, unit = CARD_CHANNELS[key]
        ax = axes[4, i]
        ax.axis('off')
        ax.set_title(f"{title} ({unit})" if unit else title,
                     fontproperties=my_font, fontsize=12)
        text = ax.text(0.5, 0.5, "--", ha='center', va='center',
                       transform=ax.transAxes, fontsize=28, fontweight='bold')
        cards[key] = (ax, text)

    return fig, axes, lines, series, times, cards


def main():
    args = parse_args()
    fig, axes, lines, series, times, cards = build_figure(args.window)
    sensors = init_sensors()

    vital_cache = {}
    t0 = time.time()
    round_no = 0

    print(f"开始采集（每 {args.draw_every} 轮重绘，窗口 {args.window} 点），Ctrl+C 退出...")
    while True:
        try:
            round_no += 1
            now = time.time() - t0
            values, vital_cache = read_round(sensors, vital_cache)

            # 每轮只追加一次时间戳，所有曲线长度保持一致
            times.append(now)
            for key in LINE_CHANNELS:
                series[key].append(values.get(key))  # 缺失记 None，曲线断口
                lines[key].set_data(list(times), list(series[key]))

            # 数字卡片更新
            for key, (ax, text) in cards.items():
                v = values.get(key)
                text.set_text(f"{v:.1f}" if v is not None else "--")

            # 朴素整帧重绘 + 节流
            if round_no % args.draw_every == 0:
                for ax in axes.flat:
                    ax.relim()
                    ax.autoscale_view()
                fig.canvas.draw()
            fig.canvas.flush_events()

            print(f"采样 #{len(times)} t={now:.2f}s")
            time.sleep(args.interval)

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
