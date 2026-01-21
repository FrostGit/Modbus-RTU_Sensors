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
    Modbus_Air_Sensor    六参数气象传感器485 Modbus-RTU协议通信封装类
    @param serial_port: 设备串口号，默认"/dev/weather_sensor"\n
    @param address: 设备Modbus地址，默认0x01
    设备地址可通过寄存器0x0100设置，范围1-50
    设备出厂默认地址为0x01
    通过Modbus RTU协议读取各项气象参数数据
    
    Attributes:
        address (int): 设备Modbus地址
        default_baudrate (int): 默认波特率9600
        各寄存器地址定义如下:
        regAirTemp (int): 温度寄存器地址0x0000
        regAirHumi (int): 湿度寄存器地址0x0001
        regDewPoint (int): 露点寄存器地址0x0002
        regAirPress (int): 气压寄存器地址0x0003
        regAltitude (int): 海拔寄存器地址0x0004
        regAirDensity (int): 空气密度寄存器地址0x0005
        regErrFlag (int): 错误标志寄存器地址0x0006
        regAirTempMax (int): 历史最大温度寄存器地址0x0010
        regAirTempMin (int): 历史最小温度寄存器地址0x0011
        regAirHumiMax (int): 历史最大湿度寄存器地址0x0012
        regAirHumiMin (int): 历史最小湿度寄存器地址0x0013
        regDewPointMax (int): 历史最大露点寄存器地址0x0014
        regDwqPointMin (int): 历史最小露点寄存器地址0x0015
        regAirPressMax (int): 历史最大气压寄存器地址0x0016
        regAirPressMin (int): 历史最小气压寄存器地址0x0017
        regAltitudeMax (int): 历史最大海拔寄存器地址0x0018
        regAltitudeMin (int): 历史最小海拔寄存器地址0x0019
        regAirDensityMax (int): 历史最大空气密度寄存器地址0x001A
        regAirDensityMin (int): 历史最小空气密度寄存器地址0x001B
        regPowerOn_H (int): 上电次数高16位寄存器地址0x001C
        regPowerOn_L (int): 上电次数低16位寄存器地址0x001D
        regPowerOnHours_H (int): 上电小时数高16位寄存器地址0x001E
        regPowerOnHours_L (int): 上电小时数低16位寄存器地址0x001F
        regErrHistory (int): 错误历史记录寄存器地址0x0020
        regAddress (int): 设备地址寄存器地址0x0100
        regUserCommand (int): 用户命令寄存器地址0x0102
        CMD_REBOOT_DEVICE (int): 重启设备命令0x100
        CMD_RESET_CALIBRATION (int): 重置所有标定参数命令0x101 **!不建议使用**
        CMD_RESET_COMM_ID (int): 重置通信ID为0x01命令0x102  **!不建议使用**

    设备地址可通过寄存器0x0100设置，范围1-50
    设备出厂默认地址为0x01
    
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
        
        self.CMD_REBOOT_DEVICE = 0x100
        self.CMD_RESET_CALIBRATION = 0x101
        self.CMD_RESET_COMM_ID = 0x102
        
        super().__init__(serial_port=serial_port,
                         baudrate=self.default_baudrate)

    def __del__(self):
        super().__del__()
        
    def close(self):
        super().close()
    
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
    
    def read_humidity(self):
        """读取湿度信息并返回

        Returns:
            float: 湿度值（百分比）
        """
        frame = self.build_read_frame(starting_address=self.regAirHumi)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        return (float) (((raw_data ^ 0x8000 ) - 0x8000) * 0.01)
    
    def read_dewPoint(self):
        """读取露点信息并返回

        Returns:
            float: 露点值（摄氏度）
        """
        frame = self.build_read_frame(starting_address=self.regDewPoint)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        return (float) (((raw_data ^ 0x8000 ) - 0x8000) * 0.01)

    def read_airPressure(self):
        """读取气压信息并返回

        Returns:
            float: 气压值（hPa）
        """
        frame = self.build_read_frame(starting_address=self.regAirPress)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        return (float) (((raw_data ^ 0x8000 ) - 0x8000) * 0.1)    
       
    def read_altitude(self):
        """读取海拔信息并返回

        Returns:
            float: 海拔值（米）
        """
        frame = self.build_read_frame(starting_address=self.regAltitude)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        return (float) (((raw_data ^ 0x8000 ) - 0x8000) * 0.2)
    
    def read_airDensity(self):
        """读取空气密度信息并返回

        Returns:
            float: 空气密度值（Kg/m³）
        """
        frame = self.build_read_frame(starting_address=self.regAirDensity)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        return (float) (((raw_data ^ 0x8000 ) - 0x8000) * 0.01)
    
    def read_errorFlag(self):
        """读取错误标志信息并返回

        Returns:
            int: 错误标志 0:正常 1:错误 可自动恢复
        """
        frame = self.build_read_frame(starting_address=self.regErrFlag)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def readAirTempMaxMin(self):
        """读取历史最大最小温度信息并返回

        Returns:
            tuple: (最大温度, 最小温度)（摄氏度）
        """
        frame = self.build_read_frame(starting_address=self.regAirTempMax, quantity=2)
        response = self.send_request_get_response(frame)
        
        raw_max = (response[3] << 8) | response[4]
        raw_min = (response[5] << 8) | response[6]
        
        max_temp = (float) (((raw_max ^ 0x8000 ) - 0x8000) * 0.01)
        min_temp = (float) (((raw_min ^ 0x8000 ) - 0x8000) * 0.01)
        
        return (max_temp, min_temp)
    
    def readAirHumiMaxMin(self):
        """读取历史最大最小湿度信息并返回

        Returns:
            tuple: (最大湿度, 最小湿度)（百分比）
        """
        frame = self.build_read_frame(starting_address=self.regAirHumiMax, quantity=2)
        response = self.send_request_get_response(frame)
        
        raw_max = (response[3] << 8) | response[4]
        raw_min = (response[5] << 8) | response[6]
        
        max_humi = (float) (((raw_max ^ 0x8000 ) - 0x8000) * 0.01)
        min_humi = (float) (((raw_min ^ 0x8000 ) - 0x8000) * 0.01)
        
        return (max_humi, min_humi)
    
    def readDewPointMaxMin(self):
        """读取历史最大最小露点信息并返回

        Returns:
            tuple: (最大露点, 最小露点)（摄氏度）
        """
        frame = self.build_read_frame(starting_address=self.regDewPointMax, quantity=2)
        response = self.send_request_get_response(frame)
        
        raw_max = (response[3] << 8) | response[4]
        raw_min = (response[5] << 8) | response[6]
        
        max_dew = (float) (((raw_max ^ 0x8000 ) - 0x8000) * 0.01)
        min_dew = (float) (((raw_min ^ 0x8000 ) - 0x8000) * 0.01)
        
        return (max_dew, min_dew)
    
    def readAirPressMaxMin(self):
        """读取历史最大最小气压信息并返回

        Returns:
            tuple: (最大气压, 最小气压)（hPa）
        """
        frame = self.build_read_frame(starting_address=self.regAirPressMax, quantity=2)
        response = self.send_request_get_response(frame)
        
        raw_max = (response[3] << 8) | response[4]
        raw_min = (response[5] << 8) | response[6]
        
        max_press = (float) (((raw_max ^ 0x8000 ) - 0x8000) * 0.1)
        min_press = (float) (((raw_min ^ 0x8000 ) - 0x8000) * 0.1)
        
        return (max_press, min_press)
    
    def readAltitudeMaxMin(self):
        """读取历史最大最小海拔信息并返回

        Returns:
            tuple: (最大海拔, 最小海拔)（米）
        """
        frame = self.build_read_frame(starting_address=self.regAltitudeMax, quantity=2)
        response = self.send_request_get_response(frame)
        
        raw_max = (response[3] << 8) | response[4]
        raw_min = (response[5] << 8) | response[6]
        
        max_alt = (float) (((raw_max ^ 0x8000 ) - 0x8000) * 0.2)
        min_alt = (float) (((raw_min ^ 0x8000 ) - 0x8000) * 0.2)
        
        return (max_alt, min_alt)
    
    def readAirDensityMaxMin(self):
        """读取历史最大最小空气密度信息并返回

        Returns:
            tuple: (最大空气密度, 最小空气密度)（Kg/m³）
        """
        frame = self.build_read_frame(starting_address=self.regAirDensityMax, quantity=2)
        response = self.send_request_get_response(frame)
        
        raw_max = (response[3] << 8) | response[4]
        raw_min = (response[5] << 8) | response[6]
        
        max_density = (float) (((raw_max ^ 0x8000 ) - 0x8000) * 0.01)
        min_density = (float) (((raw_min ^ 0x8000 ) - 0x8000) * 0.01)
        
        return (max_density, min_density)
    
    def readPowerOnCounts(self):
        """读取上电次数信息并返回

        Returns:
            int: 上电次数
        """
        frame = self.build_read_frame(starting_address=self.regPowerOn_H, quantity=2)
        response = self.send_request_get_response(frame)
        
        high_word = (response[3] << 8) | response[4]
        low_word  = (response[5] << 8) | response[6]
        
        power_on_counts = (high_word << 16) | low_word
        
        return power_on_counts
    
    def readPowerOnHours(self):
        """读取上电小时数信息并返回

        Returns:
            int: 上电小时数
        """
        frame = self.build_read_frame(starting_address=self.regPowerOnHours_H, quantity=2)
        response = self.send_request_get_response(frame)
        
        high_word = (response[3] << 8) | response[4]
        low_word  = (response[5] << 8) | response[6]
        
        power_on_hours = (high_word << 16) | low_word
        
        return power_on_hours
    
    def readErrorHistory(self):
        """读取错误历史记录信息并返回

        Returns:
            int: 错误历史记录
        """
        frame = self.build_read_frame(starting_address=self.regErrHistory)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def reboot_device(self):
        """重启设备

        """
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.address
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regUserCommand >> 8) & 0xFF
        frame.StartingAddress_L = self.regUserCommand & 0xFF
        frame.Value_H = (self.CMD_REBOOT_DEVICE >> 8) & 0xFF
        frame.Value_L = self.CMD_REBOOT_DEVICE & 0xFF
        
        self.send_request_get_response(frame)
        
if __name__ == "__main__":
    weather_sensor_port = "/dev/weather_sensor"

    while True:
        air_sensor = Modbus_Air_Sensor(serial_port=weather_sensor_port)
        delay_time = 0.05   #  该延迟时间经十轮测试可稳定读取所有数据，未测试更低延迟时间，有特殊需求可尝试
        
        print(f"Air temperature {air_sensor.read_temperature()}")
        time.sleep(delay_time)
        print(f"Air humidity {air_sensor.read_humidity()}")
        time.sleep(delay_time)
        print(f"Dew Point {air_sensor.read_dewPoint()}")
        time.sleep(delay_time)
        print(f"Air Pressure {air_sensor.read_airPressure()}")
        time.sleep(delay_time)
        print(f"Altitude {air_sensor.read_altitude()}")
        time.sleep(delay_time)
        print(f"Air Density {air_sensor.read_airDensity()}")
        time.sleep(delay_time)
        print(f"Error Flag {air_sensor.read_errorFlag()}")
        time.sleep(delay_time)
        print("-----Historical Max/Min Values-----")
        time.sleep(delay_time)
        print(f"Air Temperature Max/Min: {air_sensor.readAirTempMaxMin()}")
        time.sleep(delay_time)
        print(f"Air Humidity Max/Min: {air_sensor.readAirHumiMaxMin()}")
        time.sleep(delay_time)
        print(f"Dew Point Max/Min: {air_sensor.readDewPointMaxMin()}")
        time.sleep(delay_time)
        print(f"Air Pressure Max/Min: {air_sensor.readAirPressMaxMin()}")
        time.sleep(delay_time)
        print(f"Altitude Max/Min: {air_sensor.readAltitudeMaxMin()}")
        time.sleep(delay_time)
        print(f"Air Density Max/Min: {air_sensor.readAirDensityMaxMin()}")
        time.sleep(delay_time)
        print(f"Power On Counts: {air_sensor.readPowerOnCounts()}")
        time.sleep(delay_time)
        print(f"Power On Hours: {air_sensor.readPowerOnHours()}")
        time.sleep(delay_time)
        print(f"Error History: {air_sensor.readErrorHistory()}")
        time.sleep(delay_time) 
        
        break
