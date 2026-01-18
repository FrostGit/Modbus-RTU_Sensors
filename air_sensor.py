#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from lib_ModbusRTUDevice import ModbusRTUDevice, ModbusRTU_Frame, ModbusException
"""HAT_R4A 系列气象检测传感器驱动文件

- 测量内容：温度、湿度、气压、露点、海拔、密度
- 传感器更新速率：2Hz
- 露点测量精度：±0.8℃
- 压力测量精度：±0.06hPa (相对)   ±1hPa(绝对)
- 海拔测量精度：±0.5m (相对) ±8m (绝对)
- 空气密度测量精度：±0.01 Kg/m³
- 通信协议： Modbus-RTU

"""

class Modbus_Air_Sensor(ModbusRTUDevice):
    """
    Modbus_Soil_Sensor 的 Docstring
    土壤传感器485 Modbus-RTU协议通信封装类
    """
    def __init__(self,serial_port = "/dev/weather_sensor",address = 0x01):
        
        # 设备地址
        self.address = address
        self.default_baudrate = 9600
        
        
        # 寄存器地址列表 有负数为有符号整型
        # 温度 int16 func:3,4   单位:0.01 温度=value * 单位  单位:℃
        self.regAirTemp    = 0x0000
        # 湿度 int16 func:3,4   单位:0.01 湿度=value * 单位  0-100%
        self.regAirHumi    = 0x0001
        # 露点 int16 func:3,4   单位:0.01  露点=value * 单位  单位:℃
        self.regDewPoint   = 0x0002
        # 气压 int16 func:3,4   单位:0.1   气压=value * 单位  单位:hPa
        self.regAirPress   = 0x0003
        # 海拔 int16 func:3,4   单位:0.2   海拔=value * 单位  单位:m
        self.regAltitude   = 0x0004
        # 空气密度 int16 func:3,4 单位:0.01 空气密度=value * 单位  单位:Kg/m³
        self.regAirDensity = 0x0005
        # 错误标志 int16 func:3,4 0:正常 1:错误 可自动恢复
        self.regErrFlag    = 0x0006
        
        # 历史记录
        # 历史最大温度 最小温度
        self.regAirTempMax   = 0x0010
        self.regAirTempMin   = 0x0011
        # 历史最大湿度 最小湿度
        self.regAirHumiMax   = 0x0012
        self.regAirHumiMin   = 0x0013
        # 历史最大露点 最小露点
        self.regDewPointMax = 0x0014
        self.regDwqPointMin = 0x0015
        # 历史最大气压 最小气压
        self.regAirPressMax = 0x0016
        self.regAirPressMin = 0x0017
        # 历史最大海拔 最小海拔
        self.regAltitudeMax = 0x0018
        self.regAltitudeMin = 0x0019
        # 历史最大空气密度 最小空气密度
        self.regAirDensityMax = 0x001A
        self.regAirDensityMin = 0x001B
        # 上电次数32位寄存器 32位无符号整数
        self.regPowerOn_H  = 0x001C
        self.regPowerOn_L  = 0x001D
        # 上电小时数32位寄存器 32位无符号整数
        self.regPowerOnHours_H = 0x001E
        self.regPowerOnHours_L = 0x001F
        # 错误历史记录 func:3,4,6 如果运行过程中出现错误 则会永久记录下来 直到手动清除
        self.regErrHistory  = 0x0020
        
        # 设置参数
        # 设备地址 可设置范围1-50
        self.regAddress    = 0x0100
        # 用户命令 func:6 0x100:重启设备 0x101:重置所有标定参数 0x102:重置通信ID为0x01
        self.regUserCommand = 0x0102
        
        
        super().__init__(serial_port=serial_port,
                         baudrate=self.default_baudrate)

    def __del__(self):
        super().__del__()
    
    def build_read_frame(self, starting_address, quantity = 1):
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.address
        frame.FunctionCode = 0x03  # 读保持寄存器
        frame.StartingAddress_H = (starting_address >> 8) & 0xFF
        frame.StartingAddress_L = starting_address & 0xFF
        frame.Quantity_H = (quantity >> 8) & 0xFF
        frame.Quantity_L = quantity & 0xFF
        return frame
    
    def build_broadcast_frame(self):
        """
        生成广播查询地址帧
        
        """
        frame = ModbusRTU_Frame()
        frame.AddressCode = 0xFE  # 广播地址
        frame.FunctionCode = 0x03  # 读保持寄存器
        frame.StartingAddress_H = (self.regAddress >> 8) & 0xFF
        frame.StartingAddress_L = self.regAddress & 0xFF
        frame.Quantity_H = 0x00
        frame.Quantity_L = 0x01

        return frame

    def read_temperature(self):
        """读取温度信息并返回

        Returns:
            float: 温度值（摄氏度）
        """
        frame = self.build_read_frame(starting_address=self.regAirTemp)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        return (float) (((raw_data ^ 0x8000 ) - 0x8000) * 0.01)

        
        
        
if __name__ == "__main__":
    heart_reat_port = "/dev/heart_rate_sensor"
    weather_sensor_port = "/dev/weather_sensor"

    while True:
        air_sensor = Modbus_Air_Sensor(serial_port=weather_sensor_port)
        delay_time = 0.12
        
        print(f"Air temperature {air_sensor.read_temperature()}")
        time.sleep(delay_time)
        
        break
