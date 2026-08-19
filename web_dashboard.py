#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""远程监看服务：Flask 后端 + Web 前端实时曲线

X3 上只跑采集 + HTTP 推送（无 matplotlib 渲染负担），35 路曲线由浏览器绘制，
显示刷新 ≈ 数据速率（采集一轮约 330ms / ~3Hz）。

依赖: flask（pip install flask；纯 Python，X3 可直接装）

用法:
    python3 web_dashboard.py                  # 默认 0.0.0.0:5000
    python3 web_dashboard.py --port 8080      # 换端口
    python3 web_dashboard.py --interval 0.2   # 采集线程额外休眠(限流)

浏览器打开: http://<主机IP>:5000/
"""
import argparse
import os
import threading
import time

from flask import Flask, jsonify, send_from_directory

import sensor_acq

app = Flask(__name__)
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

STATE = {"values": {}, "ts": 0.0}
LOCK = threading.Lock()
STOP = threading.Event()


def collector(interval: float):
    """后台采集线程：每轮 read_round，结果写入 STATE"""
    sensors = sensor_acq.init_sensors()
    vital_cache = {}
    while not STOP.is_set():
        t_round = time.time()
        try:
            values, vital_cache = sensor_acq.read_round(sensors, vital_cache)
            with LOCK:
                STATE["values"] = values
                STATE["ts"] = time.time()
                STATE["acdata"] = vital_cache.get("acdata", [])
                STATE["rra"] = vital_cache.get("rra", [])
        except Exception as e:
            print(f"采集异常: {e}")
        # 最低轮询节流：正常一轮约330ms；读失败时一轮仅几毫秒，
        # 补足到 >=0.1s，防止采集线程空转烧 CPU
        dt = time.time() - t_round
        if dt < 0.1:
            time.sleep(0.1 - dt)
        if interval > 0:
            time.sleep(interval)


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/api/meta")
def api_meta():
    """通道元数据（折线/卡片/布局），前端据此建图"""
    return jsonify({
        "lines": {k: {"title": t, "unit": u, "color": c}
                  for k, (t, u, c) in sensor_acq.LINE_CHANNELS.items()},
        "cards": {k: {"title": t, "unit": u}
                  for k, (t, u) in sensor_acq.CARD_CHANNELS.items()},
        "vital_cards": {k: {"title": t, "unit": u}
                        for k, (t, u) in sensor_acq.VITAL_CARD_CHANNELS.items()},
        "line_placement": sensor_acq.LINE_PLACEMENT,
        "card_keys": sensor_acq.CARD_KEYS,
    })


@app.route("/api/data")
def api_data():
    with LOCK:
        wave = {"acdata": STATE.get("acdata", []), "rra": STATE.get("rra", [])}
        return jsonify({"ts": STATE["ts"], "values": STATE["values"], "wave": wave})


def main():
    parser = argparse.ArgumentParser(description="远程传感器监看服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=5000, help="监听端口")
    parser.add_argument("--interval", type=float, default=0.0,
                        help="采集线程额外休眠秒数(默认0=全速约3Hz)")
    args = parser.parse_args()

    t = threading.Thread(target=collector, args=(args.interval,), daemon=True)
    t.start()
    print(f"监看服务: http://{args.host}:{args.port}/  (Ctrl+C 停止)")

    try:
        app.run(host=args.host, port=args.port, threaded=True)
    except KeyboardInterrupt:
        print("\n停止服务")
    finally:
        STOP.set()


if __name__ == "__main__":
    main()
