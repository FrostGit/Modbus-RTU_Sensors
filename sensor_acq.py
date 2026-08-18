#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""传感器采集公共模块 —— big_plt(本地大屏) 与 web_dashboard(远程监看) 共用

- 驱动对象实例化一次、全程复用
- 批量读 read_all()：气象6/土壤8/电源8寄存器各1次往返，气体4从站串行，生命体征流式
- 单类传感器失败返回 None 对应字段，不中断整轮
- 通道元数据 CURVES/PLACEMENT 为唯一来源，本地与 Web 共用
"""
import time

from lib_ModbusRTUDevice import ModbusException
from air_sensor import Modbus_Air_Sensor
from heart_rate_sensor import HeartRateSensor
from power_sensor import PowerSensor
from sensor_hub import Modbus_Sensor_Hub
from soil_sensor import Modbus_Soil_Sensor

# ---- 串口设备（与 udev 符号链接一致） ----
PORTS = {
    "gas": "/dev/gas_hub",
    "air": "/dev/weather_sensor",
    "power": "/dev/power_sensor",
    "soil": "/dev/soil_sensor",
    "vital": "/dev/vital_signs",
}

# ---- 通道元数据: key -> (标题, 单位, 颜色) ----
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

# ---- 布局: 5 行 x 8 列；(4,5)-(4,7) 留空 ----
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

# 生命体征通道（流式主动上报，读不到新包时沿用缓存值）
VITAL_FIELDS = [
    "heart_rate", "spo2", "bk", "fatigue_index",
    "systolic_pressure", "diastolic_pressure",
    "cardiac_output", "peripheral_resistance", "rr_variability",
    "sdnn", "rmssd", "nn50", "pnn50",
]

VITAL_TIMEOUT = 0.05  # 只检查缓冲区，避免每轮干等


def init_sensors(ports=None, vital=True):
    """实例化驱动对象（一次创建，全程复用；失败不影响其他传感器）

    Returns:
        dict: {"gas": ..., "air": ..., "power": ..., "soil": ..., "vital": ...}
        加载失败的传感器不在字典中
    """
    ports = ports or PORTS
    sensors = {}
    try:
        sensors["gas"] = Modbus_Sensor_Hub(serial_port=ports["gas"])
        print("气体传感器已加载 (gas_hub, 4800bps)")
    except Exception as e:
        print(f"气体传感器加载失败: {e}")
    try:
        sensors["air"] = Modbus_Air_Sensor(serial_port=ports["air"])
        print("气象传感器已加载 (weather_sensor, 9600bps)")
    except Exception as e:
        print(f"气象传感器加载失败: {e}")
    try:
        sensors["power"] = PowerSensor(serial_port=ports["power"], baudrate=9600, timeout=1)
        print("电源传感器已加载 (power_sensor, 9600bps)")
    except Exception as e:
        print(f"电源传感器加载失败: {e}")
    try:
        sensors["soil"] = Modbus_Soil_Sensor(serial_port=ports["soil"])
        print("土壤传感器已加载 (soil_sensor, 9600bps)")
    except Exception as e:
        print(f"土壤传感器加载失败: {e}")
    if vital:
        try:
            vital_dev = HeartRateSensor(serial_port=ports["vital"], baudrate=38400, timeout=1)
            vital_dev.send_command(vital_dev.CMD_MODE_WORK)  # 开启工作模式
            sensors["vital"] = vital_dev
            print("生命体征传感器已加载 (vital_signs, 38400bps)")
        except Exception as e:
            print(f"生命体征传感器加载失败: {e}")
    return sensors


def read_round(sensors, vital_cache=None):
    """采集一轮：全部传感器读数返回 dict（失败字段为 None）

    Args:
        sensors: init_sensors() 的返回值
        vital_cache: 生命体征上次成功缓存（流式无新包时沿用），None 则初始化

    Returns:
        (values, vital_cache): values 为 {通道key: 数值或None}
    """
    if vital_cache is None:
        vital_cache = {}
    values = {}

    if sensors.get("gas"):
        try:
            values.update(sensors["gas"].read_all())
        except ModbusException as e:
            print(f"气体读取失败: {e}")

    if sensors.get("air"):
        try:
            values.update(sensors["air"].read_all())
        except ModbusException as e:
            print(f"气象读取失败: {e}")

    if sensors.get("power"):
        try:
            values.update(sensors["power"].read_all())
        except ModbusException as e:
            print(f"电源读取失败: {e}")

    if sensors.get("soil"):
        try:
            values.update(sensors["soil"].read_all())
        except ModbusException as e:
            print(f"土壤读取失败: {e}")

    if sensors.get("vital"):
        try:
            pkt = sensors["vital"].read_packet(timeout_s=VITAL_TIMEOUT)
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

    return values, vital_cache


if __name__ == "__main__":
    import time
    sensors = init_sensors()
    vital_cache = {}
    for i in range(3):
        t0 = time.time()
        values, vital_cache = read_round(sensors, vital_cache)
        dt = (time.time() - t0) * 1000
        print(f"--- round {i + 1} ({dt:.0f} ms) ---")
        for key, (title, unit, _) in CURVES.items():
            v = values.get(key)
            print(f"  {title}({unit}): {v if v is not None else '-'}")
