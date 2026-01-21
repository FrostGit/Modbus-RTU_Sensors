# -*- coding: utf-8 -*-
# /usr/bin/env python3
"""
演示如何使用 Modbus_Air_Sensor 类读取空气传感器的数据,并使用折线图实时显示数据变化
Args:
    sensor: 传感器类型，可选值为 "air_sensor","soil_sensor","heat_rate_sensor"和 "sensor_hub"
Returns:
    0: 成功
    -1: 失败
"""
import time
import argparse
import matplotlib.pyplot as plt
from air_sensor import Modbus_Air_Sensor
from soil_sensor import Modbus_Soil_Sensor
from heart_rate_sensor import HeartRateSensor
from sensor_hub import Modbus_Sensor_Hub

if __name__ == "__main__":
    # 读取args
    parser = argparse.ArgumentParser(description="Real-time Sensor Data Visualization")
    parser.add_argument('--sensor_type', type=str, default='air_sensor',
                        help='Type of sensor to read data from: air_sensor, soil_sensor, heart_rate_sensor, sensor_hub')
    parser.add_argument('--serial_port', type=str, required=False,
                        help='Serial port path for the sensor (e.g., /dev/ttyUSB0)')
    
    args = parser.parse_args()

    sensor_type = args.sensor_type  # 可选值: "air_sensor","soil_sensor","heart_rate_sensor","sensor_hub"
    print(f"Selected sensor type: {sensor_type}")
    if sensor_type == "air_sensor":
        sensor = Modbus_Air_Sensor()
        read_function = sensor.read_temperature
        ylabel = "Temperature (°C)"
    elif sensor_type == "soil_sensor":
        sensor = Modbus_Soil_Sensor()
        read_function = sensor.read_humi
        ylabel = "Soil Moisture (%)"
    elif sensor_type == "heart_rate_sensor":
        sensor = HeartRateSensor()
        read_function = lambda: sensor.get_heart_rate()  # 假设 HeartRateSensor 有 get_heart_rate 方法
        ylabel = "Heart Rate (bpm)"
    elif sensor_type == "sensor_hub":
        sensor = Modbus_Sensor_Hub()
        read_function = sensor.read_hub_data  # 假设 Modbus_Sensor_Hub 有 read_hub_data 方法
        ylabel = "Hub Data"
    else:
        print("Unsupported sensor type.")
        exit(-1)

    plt.ion()
    fig, ax = plt.subplots()
    xdata, ydata = [], []
    line, = ax.plot(xdata, ydata, '-o')
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Real-time {sensor_type} Data")

    start_time = time.time()
    try:
        while True:
            current_time = time.time() - start_time
            data_value = read_function()
            xdata.append(current_time)
            ydata.append(data_value)

            line.set_xdata(xdata)
            line.set_ydata(ydata)
            ax.relim()
            ax.autoscale_view()
            plt.draw()
            plt.pause(0.1)
            time.sleep(0.2)
            # 处理窗口关闭事件
            if not plt.fignum_exists(fig.number):
                break
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        plt.ioff()
        plt.show()
        sensor.close()  # 假设传感器类有 close 方法
