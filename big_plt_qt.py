#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多模态传感器综合大屏 —— pyqtgraph 本地实时版

针对 X3 本地显示需求：matplotlib 在 X3(ARM) 上整帧渲染约 3.6s，
pyqtgraph(Qt) 每帧 <50ms，可实时刷新。

- 19 路折线（4x5 网格）：气体4 / 气象5 / 电源3 / 土壤5 / 心率·血氧2
- 5 个数字卡片：累计电量 / 海拔 / 土壤氮磷钾
- 采集在后台线程（~3Hz），GUI 主线程按数据到达刷新，互不阻塞

依赖: pip3 install pyqt5 pyqtgraph

用法:
    python3 big_plt_qt.py
    python3 big_plt_qt.py --window 300 --poll-ms 100
"""
import argparse
import os
import sys
import threading
import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QFontDatabase, QImage, QPixmap
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

try:
    from PIL import Image
except ImportError:
    Image = None  # logo 仅为装饰，缺 PIL 时跳过

from sensor_acq import (CARD_CHANNELS, CARD_KEYS, LINE_CHANNELS, LINE_PLACEMENT,
                        Y_RANGES, init_sensors, read_round)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WINDOW = 300      # 保留最近 300 个采样点
POLL_MS = 200     # GUI 刷新节拍(毫秒): 数据约3Hz(333ms)，200ms 足够且省 CPU

# matplotlib 单字母颜色 -> Qt 颜色
COLORS = {
    "r": "#e74c3c", "g": "#2ecc71", "b": "#3498db", "y": "#f1c40f",
    "c": "#00bcd4", "m": "#e91e63", "k": "#cfcfcf",
}
CARD_COLORS = {   # 卡片数值颜色
    "energy": "#f1c40f", "altitude": "#3498db",
    "soil_nitro": "#2ecc71", "soil_phosphorus": "#e91e63",
    "soil_potassium": "#00bcd4",
}


def load_cjk_font():
    """注册仓库内 STSONG.TTF，返回字体族名（失败返回 None）"""
    path = os.path.join(BASE_DIR, "STSONG.TTF")
    if not os.path.exists(path):
        return None
    fid = QFontDatabase.addApplicationFont(path)
    if fid < 0:
        return None
    families = QFontDatabase.applicationFontFamilies(fid)
    return families[0] if families else None


class BigPltQt(QWidget):
    def __init__(self, window=WINDOW, poll_ms=POLL_MS):
        super().__init__()
        self.window = window
        self.poll_ms = poll_ms

        self.setWindowTitle("多模态传感器综合大屏 (pyqtgraph)")
        self.resize(1600, 900)

        root = QVBoxLayout(self)
        # ---- 顶部：数字卡片行 ----
        card_row = QHBoxLayout()
        self.cards = {}
        for key in CARD_KEYS:
            title, unit = CARD_CHANNELS[key]
            box = QVBoxLayout()
            label = QLabel(f"{title} ({unit})" if unit else title)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color:#aab; font-size:13px;")
            value = QLabel("--")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet(
                f"color:{CARD_COLORS.get(key, '#eee')}; font-size:30px; font-weight:bold;")
            box.addWidget(label)
            box.addWidget(value)
            wrap = QWidget()
            wrap.setLayout(box)
            wrap.setStyleSheet(
                "background:#27293d; border-radius:6px; padding:6px;")
            card_row.addWidget(wrap)
            self.cards[key] = value
        root.addLayout(card_row)

        # ---- 中部：4x5 折线网格 ----
        grid = QGridLayout()
        grid.setSpacing(4)
        self.plots = {}
        self.series = {key: deque(maxlen=window) for key in LINE_CHANNELS}
        self.times = deque(maxlen=window)

        for row, col, key in LINE_PLACEMENT:
            title, unit, color = LINE_CHANNELS[key]
            pw = pg.PlotWidget(background="#1e1e2e")
            pw.showGrid(x=True, y=True, alpha=0.2)
            pw.setMenuEnabled(False)
            pw.setClipToView(True)
            pw.setTitle(self._title_html(title, unit))
            curve = pw.plot([], [], pen=pg.mkPen(COLORS.get(color, "#eee"), width=2),
                            antialias=False)
            pw.setMouseEnabled(x=False, y=False)
            # 固定 Y 量程：省去每帧自动缩放(CPU)且轴不跳动；无配置的通道自动缩放
            if key in Y_RANGES:
                pw.setYRange(*Y_RANGES[key], padding=0)
            grid.addWidget(pw, row, col)
            self.plots[key] = (pw, curve)

        # logo 占位 (3,4)
        logo_box = QLabel()
        logo_box.setAlignment(Qt.AlignCenter)
        if Image is not None:
            try:
                img = Image.open(os.path.join(BASE_DIR, "logo.jpg")).convert("RGB")
                img = img.resize((240, 180))
                qimg = QImage(img.tobytes(), img.width, img.height, img.width * 3,
                              QImage.Format_RGB888)
                logo_box.setPixmap(QPixmap.fromImage(qimg))
            except Exception:
                logo_box.setText(" ")
        else:
            logo_box.setText(" ")
        grid.addWidget(logo_box, 3, 4)
        root.addLayout(grid, 1)

        # ---- 采集线程与 GUI 节拍 ----
        self.state = {"values": {}, "ts": 0.0}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.last_ts = 0.0
        self.thread = threading.Thread(target=self._collect, daemon=True)
        self.thread.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(self.poll_ms)

    def _title_html(self, title, unit):
        family = getattr(self, "_cjk_family", None)
        fam = f'font-family:"{family}";' if family else ""
        txt = f"{title} ({unit})" if unit else title
        return f'<span style="{fam}font-size:12pt;color:#ddd">{txt}</span>'

    def _collect(self):
        """后台采集线程：每轮 read_round 写入 state"""
        family = load_cjk_font()
        self._cjk_family = family
        sensors = init_sensors()
        if not sensors:
            print("警告: 没有任何传感器加载成功，界面空转（仅显示'--'）")
        vital_cache = {}
        t0 = time.monotonic()
        values = {}
        while not self.stop.is_set():
            t_round = time.monotonic()
            try:
                values, vital_cache = read_round(sensors, vital_cache)
                with self.lock:
                    self.state["values"] = values
                    self.state["ts"] = time.monotonic() - t0
            except Exception as e:
                print(f"采集异常: {e}")
                values = {}
            if not sensors:
                time.sleep(0.5)  # 无硬件时空转，避免忙等刷屏
            else:
                # 最低轮询节流：正常一轮约330ms 无需补；读失败时一轮仅几毫秒，
                # 补足到 >=0.1s，防止采集线程空转烧 CPU
                dt = time.monotonic() - t_round
                if dt < 0.1:
                    time.sleep(0.1 - dt)

    def _refresh(self):
        """GUI 主线程：有新数据才更新曲线与卡片"""
        with self.lock:
            ts = self.state["ts"]
            if ts == self.last_ts:
                return
            self.last_ts = ts
            values = dict(self.state["values"])

        self.times.append(ts)
        for key, (pw, curve) in self.plots.items():
            self.series[key].append(values.get(key))
            # None -> nan，pyqtgraph 以 connect='finite' 断口显示
            y = np.array(self.series[key], dtype=float)
            curve.setData(list(self.times), y)
        for key, label in self.cards.items():
            v = values.get(key)
            label.setText(f"{v:.1f}" if v is not None else "--")

    def closeEvent(self, event):
        self.stop.set()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="多模态传感器综合大屏(pyqtgraph)")
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--poll-ms", type=int, default=POLL_MS)
    args = parser.parse_args()

    app = pg.mkQApp()
    win = BigPltQt(window=args.window, poll_ms=args.poll_ms)
    win.show()
    print("开始采集（pyqtgraph 实时大屏），关闭窗口或 Ctrl+C 退出...")
    try:
        app.exec_()
    except KeyboardInterrupt:
        win.stop.set()
        sys.exit(0)


if __name__ == "__main__":
    main()
