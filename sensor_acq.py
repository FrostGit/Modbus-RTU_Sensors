#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""传感器采集公共模块 —— big_plt(本地大屏) 与 web_dashboard(远程监看) 共用

- 驱动对象实例化一次、全程复用
- 批量读 read_all()：气象6/土壤8/电源8寄存器各1次往返，气体4从站串行，生命体征流式
- 单类传感器失败返回 None 对应字段，不中断整轮
- 通道元数据（折线/卡片/布局）为唯一来源，本地与 Web 共用
- 生命体征波形(acdata)与RR间期(rra)随采集缓存，供 web 波形面板与散点使用
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

# ---- 折线通道: key -> (标题, 单位, 颜色) ----
LINE_CHANNELS = {
    # 气体 4
    "smoke": ("烟雾传感器", "ppm", "r"),
    "co2": ("二氧化碳传感器", "ppm", "g"),
    "o2": ("氧气传感器", "%VOL", "b"),
    "ch4": ("甲烷传感器", "%LEL", "y"),
    # 气象 5（海拔改卡片）
    "temperature": ("空气温度", "℃", "c"),
    "humidity": ("空气湿度", "%", "m"),
    "dewpoint": ("露点温度", "℃", "r"),
    "pressure": ("大气压力", "hPa", "g"),
    "air_density": ("空气密度", "Kg/m³", "k"),
    # 电源 3（累计电量改卡片）
    "voltage": ("电压", "V", "r"),
    "current": ("电流", "A", "k"),
    "power": ("功率", "W", "g"),
    # 土壤 5（氮磷钾改卡片）
    "soil_temp": ("土壤温度", "℃", "r"),
    "soil_moisture": ("土壤湿度", "%", "m"),
    "soil_ec": ("土壤电导率", "µS/cm", "b"),
    "soil_salty": ("土壤盐分", "mg/L", "y"),
    "soil_ph": ("土壤PH值", "pH", "c"),
    # 生命体征 2（仅心率/血氧折线）
    "heart_rate": ("心率", "bpm", "r"),
    "spo2": ("血氧", "%", "g"),
}

# ---- 数字卡片通道(plt 与 web 都显示): key -> (标题, 单位) ----
CARD_CHANNELS = {
    "energy": ("累计电量", "Wh"),
    "altitude": ("海拔高度", "m"),
    "soil_nitro": ("土壤氮含量", "mg/kg"),
    "soil_phosphorus": ("土壤磷含量", "mg/kg"),
    "soil_potassium": ("土壤钾含量", "mg/kg"),
}

# ---- 生命体征卡片(仅 web 前端显示): key -> (标题, 单位) ----
VITAL_CARD_CHANNELS = {
    "bk": ("微循环", ""),
    "fatigue_index": ("疲劳指数", ""),
    "systolic_pressure": ("收缩压", "mmHg"),
    "diastolic_pressure": ("舒张压", "mmHg"),
    "cardiac_output": ("心输出", ""),
    "peripheral_resistance": ("外周阻力", ""),
    "rr_variability": ("RR变异性", ""),
    "sdnn": ("SDNN", "ms"),
    "rmssd": ("RMSSD", "ms"),
    "nn50": ("NN50", ""),
    "pnn50": ("PNN50", "%"),
}

# ---- 折线布局: 4 行 x 5 列（(3,4) 留给 plt 的 logo 图） ----
LINE_PLACEMENT = [
    (0, 0, "smoke"), (0, 1, "co2"), (0, 2, "o2"), (0, 3, "ch4"), (0, 4, "temperature"),
    (1, 0, "humidity"), (1, 1, "dewpoint"), (1, 2, "pressure"), (1, 3, "air_density"), (1, 4, "voltage"),
    (2, 0, "current"), (2, 1, "power"), (2, 2, "soil_temp"), (2, 3, "soil_moisture"), (2, 4, "soil_ec"),
    (3, 0, "soil_salty"), (3, 1, "soil_ph"), (3, 2, "heart_rate"), (3, 3, "spo2"),
]

# ---- plt 卡片行顺序 ----
CARD_KEYS = ["energy", "altitude", "soil_nitro", "soil_phosphorus", "soil_potassium"]

# 生命体征 13 字段（流式主动上报，读不到新包时沿用缓存值）
VITAL_FIELDS = [
    "heart_rate", "spo2", "bk", "fatigue_index",
    "systolic_pressure", "diastolic_pressure",
    "cardiac_output", "peripheral_resistance", "rr_variability",
    "sdnn", "rmssd", "nn50", "pnn50",
]

VITAL_TIMEOUT = 0.05  # 只检查缓冲区，避免每轮干等

# ---- 折线通道固定 Y 轴量程: key -> (min, max) ----
# 目的: 关闭每帧自动缩放(省 CPU)并避免轴跳动；未列出的通道保持自动缩放
Y_RANGES = {
    "smoke": (0, 100),        # ppm
    "co2": (300, 2000),       # ppm
    "o2": (0, 25),            # %VOL
    "ch4": (0, 100),          # %LEL
    "temperature": (0, 50),   # ℃
    "humidity": (0, 100),     # %
    "dewpoint": (0, 50),      # ℃
    "pressure": (950, 1050),  # hPa
    "voltage": (0, 20),       # V
    "current": (0, 10),       # A
    "power": (0, 100),        # W
    "soil_temp": (0, 50),     # ℃
    "soil_moisture": (0, 100),  # %
    "soil_ec": (0, 2000),     # µS/cm
    "soil_salty": (0, 2000),  # mg/L
    "soil_ph": (3, 10),       # pH
    "heart_rate": (40, 220),  # bpm
    "spo2": (85, 100),        # %
}


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
        (values, vital_cache):
            values 为 {通道key: 数值或None}（35 路全量，展示端自行取舍）
            vital_cache 含 13 项指标 + acdata(64点波形) + rra(6个RR间期)
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
                    "acdata": list(pkt.acdata),   # 64 点脉搏波
                    "rra": list(pkt.rra),         # 6 个 RR 间期
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
        for key in list(LINE_CHANNELS) + list(CARD_CHANNELS) + list(VITAL_CARD_CHANNELS):
            v = values.get(key)
            if v is not None:
                print(f"  {key}: {v}")
        if vital_cache.get("acdata"):
            print(f"  波形点: {len(vital_cache['acdata'])}, RR间期: {vital_cache['rra']}")
