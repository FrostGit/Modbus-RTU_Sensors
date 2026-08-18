#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lib_ModbusRTUDevice import ModbusRTUDevice, ModbusRTU_Frame, ModbusException
"""
气体传感器485 Modbus-RTU协议通信底层库

传感器类型      地址
烟雾传感器      0x02
CO2传感器       0x03
氧气传感器      0x04
甲烷传感器      0x05
"""

class GasSensor:
    def __init__(self, sensor_type: str, address: int = 0x00):
        """气体传感器的抽象类，四个传感器共用一个气体传感器类

        Args:
            sensor_type (str): 传感器类型，可选值为 "smoke_sensor","co2_sensor","o2_sensor","ch4_sensor"
            address (int): 传感器地址，默认会自动根据类型设置地址
        Attributes:
            sensor_type (str): 传感器类型
            address (int): 传感器地址
        Returns:
            None
        """
        self.sensor_type = sensor_type
        self.address = address
        # 传感器地址（与文件头部注释、lib_ModbusRTUDevice 保持一致）：
        # 烟雾 0x02 / CO2 0x03 / 氧气 0x04 / 甲烷 0x05
        self.sensor_address_map = {
            "smoke_sensor": 0x02,
            "co2_sensor": 0x03,
            "o2_sensor": 0x04,
            "ch4_sensor": 0x05
        }
        if sensor_type in self.sensor_address_map:
            self.address = self.sensor_address_map[sensor_type]
        else:
            raise ValueError("Unsupported sensor type.\n Supported types are: smoke_sensor, co2_sensor, o2_sensor, ch4_sensor\n But got: " + sensor_type)

        self.regGasConcentration   = 0x0000  # 气体浓度 fn:0x03,0x04 范围：0-100ppm
        self.regGasConcentration_backup = 0x0002  # 气体浓度 fn:0x03,0x04 范围：0-100ppm
        if self.sensor_type == "co2_sensor":
            self.regGasConcentration_H16 = 0x0000  # CO2浓度高16位 fn:0x03,0x04 范围：0-5000ppm
            self.regGasConcentration_L16 = 0x0001  # CO2浓度低16位 fn:0x03,0x04 范围：0-5000ppm
        
        self.factor = 1.0 if self.sensor_type != "o2_sensor" else 0.1  # 气体浓度转换因子 O2传感器需要乘以0.1
        
        

        
        self.regAddress = 0x07D0  # 设备地址寄存器地址 fn:0x03,0x06 范围1-254
        self.regBaudrate = 0x07D1  # 波特率寄存器地址 fn:0x03,0x06  0:2400 1:4800 2:9600 3:19200 4:38400 5:57600 6:115200 7:1200
    
    def get_gas_unit(self):
        if self.sensor_type == "smoke_sensor" or self.sensor_type == "co2_sensor":
            return "ppm"
        elif self.sensor_type == "o2_sensor":
            return "%VOL"
        elif self.sensor_type == "ch4_sensor":
            return "%LEL"

class Modbus_Sensor_Hub(ModbusRTUDevice):
    """
    Modbus_Sensor_Hub 的 Docstring
    传感器集线器485 Modbus-RTU协议通信封装类
    """
    sensorSmoke = GasSensor(sensor_type="smoke_sensor")
    sensorCO2   = GasSensor(sensor_type="co2_sensor")
    sensorO2    = GasSensor(sensor_type="o2_sensor")
    sensorCH4   = GasSensor(sensor_type="ch4_sensor")
    
    def __init__(self,serial_port = "/dev/sensor_hub",):
        
        # 设备地址
        self.default_baudrate = 4800
        self.default_parity = 0  # 0:无校验 1:奇校验 2:偶校验
        
        
        super().__init__(serial_port=serial_port,
                         baudrate=self.default_baudrate,
                         parity=self.default_parity)

    def __del__(self):
        super().__del__()
    
    def close(self):
        return super().close()
    
    def build_read_frame(self, starting_address, quantity = 1, address=None):
        frame = ModbusRTU_Frame()
        if address is None:
            raise ModbusException("Address must be specified for sensor hub read frame.")
        else:
            frame.AddressCode = address
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
        # 设备地址寄存器地址定义在 GasSensor 上（0x07D0），HUB 本身无该属性
        frame.StartingAddress_H = (self.sensorSmoke.regAddress >> 8) & 0xFF
        frame.StartingAddress_L = self.sensorSmoke.regAddress & 0xFF
        frame.Quantity_H = 0x00
        frame.Quantity_L = 0x01

        return frame

    def get_sensor_unit(self, sensor_type: str):
        """获取传感器单位

        Args:
            sensor_type (str): 传感器类型，可选值为 "smoke_sensor","co2_sensor","o2_sensor","ch4_sensor"

        Returns:
            str: 传感器单位
        """
        sensor = None
        if sensor_type == "smoke_sensor":
            sensor = self.sensorSmoke
        elif sensor_type == "co2_sensor":
            sensor = self.sensorCO2
        elif sensor_type == "o2_sensor":
            sensor = self.sensorO2
        elif sensor_type == "ch4_sensor":
            sensor = self.sensorCH4
        else:
            raise ValueError("Unsupported sensor type.\n Supported types are: smoke_sensor, co2_sensor, o2_sensor, ch4_sensor\n But got: " + sensor_type)
        
        return sensor.get_gas_unit()

    def read_smokeGasConcentration(self, backup=False):
        """读取烟雾浓度信息并返回
        Args:
            backup (bool): 是否读取备用浓度值，默认为False，读取主浓度值
        
        Returns:
            float: 烟雾浓度值（ppm）
        """
        regAddress = self.sensorSmoke.regGasConcentration_backup if backup else self.sensorSmoke.regGasConcentration
        frame = self.build_read_frame(starting_address=regAddress,address=self.sensorSmoke.address)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        raw_data = raw_data * self.sensorSmoke.factor
        return raw_data
    

    def read_co2GasConcentration(self):
        """读取CO2浓度信息并返回

        Returns:
            float: CO2浓度值（ppm）
        """
        frame = self.build_read_frame(starting_address=self.sensorCO2.regGasConcentration,address=self.sensorCO2.address)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        raw_data = raw_data * self.sensorCO2.factor
        return raw_data

    def read_o2GasConcentration(self):
        """读取O2浓度信息并返回

        Returns:
            float: O2浓度值（%VOL）
        """
        frame = self.build_read_frame(starting_address=self.sensorO2.regGasConcentration,address=self.sensorO2.address)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        raw_data = raw_data * self.sensorO2.factor
        # 处理补码 直接无符号转有符号
        return raw_data

    def read_ch4GasConcentration(self):
        """读取CH4浓度信息并返回

        Returns:
            float: CH4浓度值（%LEL）
        """
        frame = self.build_read_frame(starting_address=self.sensorCH4.regGasConcentration,address=self.sensorCH4.address)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        raw_data = raw_data * self.sensorCH4.factor
        return raw_data

    def read_all(self):
        """一次读取全部4种气体浓度（4个从站地址不同，需4次串行往返）

        Returns:
            dict: {"smoke": ppm, "co2": ppm, "o2": %VOL, "ch4": %LEL}
        """
        return {
            "smoke": self.read_smokeGasConcentration(),
            "co2": self.read_co2GasConcentration(),
            "o2": self.read_o2GasConcentration(),
            "ch4": self.read_ch4GasConcentration(),
        }

if __name__ == "__main__":
    gas_hub_port = "/dev/gas_hub"

    while True:
        sensor_hub = Modbus_Sensor_Hub(serial_port=gas_hub_port)
        try:
            for name, value in sensor_hub.read_all().items():
                print(f"{name:6s} Gas Concentration: {value} {sensor_hub.get_sensor_unit(name + '_sensor')}")
        except ModbusException as e:
            print(f"Modbus Exception: {e}")
        break
