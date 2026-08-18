#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多模态传感器综合大屏（本地 matplotlib，大表格展示）

覆盖 5 类传感器共 35 路曲线：
- 气体(HUB) 4 路 / 气象 6 路 / 电源 4 路 / 土壤 8 路 / 生命体征 13 路

设计要点：
- 采集逻辑共用 sensor_acq（与 web_dashboard 远程监看同一套 read_all）
- 驱动对象实例化一次、全程复用；单类失败记 None（曲线断口），不破坏整轮
- 横轴相对时间(秒)，环形缓冲保留最近 WINDOW 个采样点
- 性能：blit 增量重绘（仅重绘变化的曲线），文字开销精简；
  采集一轮约 330ms(~3Hz)，显示刷新接近数据速率

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

import sensor_acq
from sensor_acq import CURVES, PLACEMENT, init_sensors, read_round

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WINDOW = 300      # 保留最近 300 个采样点
DRAW_EVERY = 1    # 每 N 轮采集重绘一次（blit 下通常 1 即可，按需调大）

my_font = font_manager.FontProperties(fname=os.path.join(BASE_DIR, "STSONG.TTF"), size=10)

plt.ion()


def build_figure():
    """创建 5x8 大表格并返回 (fig, axes, lines, series, times, line_axes)"""
    fig, axes = plt.subplots(5, 8, figsize=(24, 16))
    plt.tight_layout(rect=[0, 0, 1, 0.98])

    lines = {}
    line_axes = {}
    series = {key: deque(maxlen=WINDOW) for key in CURVES}
    times = deque(maxlen=WINDOW)

    for row, col, key in PLACEMENT:
        title, unit, color = CURVES[key]
        ax = axes[row, col]
        # 单位并入标题、去掉 ylabel/刻度文字，减少每帧文字渲染开销
        line, = ax.plot([], [], color + '-', linewidth=2, animated=True)
        ax.set_title(f"{title} ({unit})" if unit else title,
                     fontproperties=my_font, fontsize=10)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.3)
        lines[key] = line
        line_axes[key] = ax

    # 图片占位
    axes[1, 3].axis('off')
    axes[1, 3].imshow(np.array(Image.open(os.path.join(BASE_DIR, "logo.jpg"))))
    axes[1, 4].axis('off')
    axes[1, 4].imshow(np.array(Image.open(os.path.join(BASE_DIR, "title.png"))))
    for col in range(5, 8):
        axes[4, col].axis('off')

    return fig, axes, lines, series, times, line_axes


def main():
    fig, axes, lines, series, times, line_axes = build_figure()
    sensors = init_sensors()

    vital_cache = {}
    blit_bgs = {}
    t0 = time.time()
    round_no = 0

    print("开始采集，按 Ctrl+C 退出...")
    while True:
        try:
            round_no += 1
            now = time.time() - t0
            values, vital_cache = read_round(sensors, vital_cache)

            # 每轮只追加一次时间戳，所有曲线长度保持一致
            times.append(now)
            for key in CURVES:
                series[key].append(values.get(key))  # 缺失记 None，曲线断口
                lines[key].set_data(list(times), list(series[key]))

            if round_no % DRAW_EVERY == 0:
                # 视图范围是否变化：变化才整帧重绘，否则 blit 增量更新
                limits_changed = False
                for ax in axes.flat:
                    before = (ax.get_xlim(), ax.get_ylim())
                    ax.relim()
                    ax.autoscale_view()
                    if (ax.get_xlim(), ax.get_ylim()) != before:
                        limits_changed = True

                try:
                    if limits_changed or not blit_bgs:
                        fig.canvas.draw()
                        blit_bgs = {ax: fig.canvas.copy_from_bbox(ax.bbox)
                                    for ax in axes.flat}
                    else:
                        for ax in axes.flat:
                            fig.canvas.restore_region(blit_bgs[ax])
                    for key, line in lines.items():
                        line.axes.draw_artist(line)
                    for ax in axes.flat:
                        fig.canvas.blit(ax.bbox)
                except (AttributeError, NotImplementedError):
                    # 后端不支持 blit 时退回整帧重绘
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
