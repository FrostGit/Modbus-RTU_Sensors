# -*- coding: utf-8 -*-
# /usr/bin/env python3
"""单传感器数据读取示例

读取指定传感器的一项指标并实时绘制折线图。

Args:
    --sensor_type: air_sensor | soil_sensor | power_sensor | sensor_hub | heart_rate_sensor
    --serial_port: 串口路径（默认按传感器类型取 udev 符号链接）
    --interval:    采样间隔（秒，默认 0.2）
"""
import argparse
import time

import matplotlib.pyplot as plt

from air_sensor import Modbus_Air_Sensor
from heart_rate_sensor import HeartRateSensor
from sensor_hub import Modbus_Sensor_Hub
from soil_sensor import Modbus_Soil_Sensor
from power_sensor import PowerSensor

DEFAULT_PORTS = {
    "air_sensor": "/dev/weather_sensor",
    "soil_sensor": "/dev/soil_sensor",
    "power_sensor": "/dev/power_sensor",
    "sensor_hub": "/dev/gas_hub",
    "heart_rate_sensor": "/dev/vital_signs",
}


def build_reader(sensor_type, serial_port):
    """返回 (sensor, read_fn, ylabel) —— read_fn() 每次返回一个浮点读数"""
    if sensor_type == "air_sensor":
        sensor = Modbus_Air_Sensor(serial_port=serial_port)
        return sensor, lambda: sensor.read_all()["temperature"], "Temperature (°C)"

    if sensor_type == "soil_sensor":
        sensor = Modbus_Soil_Sensor(serial_port=serial_port)
        return sensor, lambda: sensor.read_all()["soil_moisture"], "Soil Moisture (%)"

    if sensor_type == "power_sensor":
        sensor = PowerSensor(serial_port=serial_port, baudrate=9600, timeout=1)
        return sensor, lambda: sensor.read_all()["voltage"], "Voltage (V)"

    if sensor_type == "sensor_hub":
        sensor = Modbus_Sensor_Hub(serial_port=serial_port)
        return sensor, lambda: sensor.read_all()["co2"], "CO2 (ppm)"

    if sensor_type == "heart_rate_sensor":
        sensor = HeartRateSensor(serial_port=serial_port, baudrate=38400, timeout=1)
        sensor.send_command(sensor.CMD_MODE_WORK)  # 开启工作模式
        last = {"value": None}

        def _read_hr():
            pkt = sensor.read_packet(timeout_s=0.3)
            if pkt:
                last["value"] = pkt.heart_rate
            return last["value"]

        return sensor, _read_hr, "Heart Rate (bpm)"

    raise ValueError(f"不支持的传感器类型: {sensor_type}")


def main():
    parser = argparse.ArgumentParser(description="单传感器数据实时绘图示例")
    parser.add_argument("--sensor_type", type=str, default="air_sensor",
                        help="air_sensor | soil_sensor | power_sensor | sensor_hub | heart_rate_sensor")
    parser.add_argument("--serial_port", type=str, default=None,
                        help="串口路径（默认按类型取 /dev/ udev 符号链接）")
    parser.add_argument("--interval", type=float, default=0.2,
                        help="采样间隔秒数（默认 0.2）")
    args = parser.parse_args()

    if args.serial_port is None:
        args.serial_port = DEFAULT_PORTS.get(args.sensor_type)
    if args.serial_port is None:
        print(f"不支持的传感器类型: {args.sensor_type}")
        return -1

    print(f"传感器: {args.sensor_type} @ {args.serial_port}")
    sensor, read_fn, ylabel = build_reader(args.sensor_type, args.serial_port)

    plt.ion()
    fig, ax = plt.subplots()
    xdata, ydata = [], []
    line, = ax.plot(xdata, ydata, '-o')
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Real-time {args.sensor_type} Data")

    start_time = time.time()
    try:
        while True:
            current_time = time.time() - start_time
            try:
                data_value = read_fn()
            except Exception as e:
                print(f"读取失败: {e}")
                time.sleep(args.interval)
                continue
            if data_value is None:
                print("无数据（等待传感器响应）...")
                time.sleep(args.interval)
                continue
            xdata.append(current_time)
            ydata.append(data_value)
            line.set_xdata(xdata)
            line.set_ydata(ydata)
            ax.relim()
            ax.autoscale_view()
            plt.draw()
            plt.pause(0.05)
            print(f"t={current_time:.2f}s value={data_value}")
            if not plt.fignum_exists(fig.number):  # 窗口被关闭则退出
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("退出...")
    finally:
        plt.ioff()
        plt.show()
        sensor.close()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
