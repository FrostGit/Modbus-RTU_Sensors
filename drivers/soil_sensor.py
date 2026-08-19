#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lib_ModbusRTUDevice import ModbusRTUDevice, ModbusRTU_Frame, ModbusException


class Modbus_Soil_Sensor(ModbusRTUDevice):
    """
    Modbus_Soil_Sensor 的 Docstring
    土壤传感器485 Modbus-RTU协议通信封装类
    """
    def __init__(self,serial_port = "/dev/soil_sensor",address = 0x01):
        
        # 设备地址
        self.address = address
        self.default_baudrate = 9600
        self.default_parity = 0  # 0:无校验 1:奇校验 2:偶校验
        
        
        # 寄存器地址列表  数据为16位整型 有负数为有符号整型
        # 土壤温度 -ro  1位小数 负数用补码表示 单位℃
        self.regSoilTemp    = 0x0000
        # 土壤湿度 -ro  1位小数 0-100%
        self.regSoilHumi    = 0x0001
        # 土壤EC值 -ro  无小数 0-20000 单位us/cm
        self.regSoilEC      = 0x0002
        # 土壤盐分 -ro  无小数 0-20000 单位mg/L
        self.regSoilSalty   = 0x0003
        # 土壤氮   -ro  无小数 0-1999 单位mg/kg
        self.regSoilNitro   = 0x0004
        # 土壤磷   -ro 无小数 0-1999 单位mg/kg
        self.regSoilPhosphorus  = 0x0005
        # 土壤钾   -ro 无小数 0-1999 单位mg/kg
        self.regSoilPotassium   = 0x0006
        # 土壤PH值 -ro 2位小数 3-10 单位pH
        self.regSoilPH     = 0x0007
        # 设备地址 -rw 范围1-253 默认0x01 广播0xFE
        self.regAddress    = 0x0030
        # 设备波特率-rw 5种 默认9600
        self.regBaudrate   = 0x0031
        # 设备校验位-rw 3种 默认无校验 0:无 1:奇校验 2:偶校验
        self.regParity     = 0x0032
        # 自动上报 -rw  0-65535秒 默认0 不上报 
        self.regAutoReport = 0x0033
        
        super().__init__(serial_port=serial_port,
                         baudrate=self.default_baudrate,
                         parity=self.default_parity)

    def __del__(self):
        super().__del__()
        
    def close(self):
        return super().close()
    
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
        frame = self.build_read_frame(starting_address=self.regSoilTemp)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        # 处理补码 直接无符号转有符号
        return (float) (((raw_data ^ 0x8000 ) - 0x8000) / 10.0)
    
    def read_humi(self):
        """读取湿度信息并返回

        Returns:
            float: 湿度值（百分比）
        """
        frame = self.build_read_frame(starting_address=self.regSoilHumi)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return (float)(raw_data / 10.0)
    
    def read_EC(self):
        """读取EC信息并返回

        Returns:
            int: EC值（us/cm）
        """
        frame = self.build_read_frame(starting_address=self.regSoilEC)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def read_salty(self):
        """读取盐分信息并返回

        Returns:
            int: 盐分值（mg/L）
        """
        frame = self.build_read_frame(starting_address=self.regSoilSalty)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def read_nitro(self):
        """读取氮信息并返回

        Returns:
            int: 氮值（mg/kg）
        """
        frame = self.build_read_frame(starting_address=self.regSoilNitro)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def read_phosphorus(self):
        """读取磷信息并返回

        Returns:
            int: 磷值（mg/kg）
        """
        frame = self.build_read_frame(starting_address=self.regSoilPhosphorus)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def read_potassium(self):
        """读取钾信息并返回

        Returns:
            int: 钾值（mg/kg）
        """
        frame = self.build_read_frame(starting_address=self.regSoilPotassium)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def read_PH(self):
        """读取PH信息并返回

        Returns:
            float: PH值（pH）
        """
        frame = self.build_read_frame(starting_address=self.regSoilPH)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return (float)(raw_data / 100.0)
    
    def read_all(self):
        """一次批量读取全部8项土壤参数（0x0000-0x0007连续，1次Modbus往返）

        Returns:
            dict: {"soil_temp": ℃, "soil_moisture": %, "soil_ec": us/cm,
                   "soil_salty": mg/L, "soil_nitro": mg/kg, "soil_phosphorus": mg/kg,
                   "soil_potassium": mg/kg, "soil_ph": pH}
        """
        frame = self.build_read_frame(starting_address=0x0000, quantity=8)
        response = self.send_request_get_response(frame)
        fields = [
            ("soil_temp",       10.0, True),   # (名称, 除数, 有符号)
            ("soil_moisture",   10.0, False),
            ("soil_ec",          1.0, False),
            ("soil_salty",       1.0, False),
            ("soil_nitro",       1.0, False),
            ("soil_phosphorus",  1.0, False),
            ("soil_potassium",   1.0, False),
            ("soil_ph",        100.0, False),
        ]
        values = {}
        for i, (name, div, signed) in enumerate(fields):
            raw = (response[3 + i * 2] << 8) | response[4 + i * 2]
            val = (((raw ^ 0x8000) - 0x8000) if signed else raw) / div
            values[name] = val
        return values
    
    def read_address(self):
        """读取设备地址并返回

        Returns:
            int: 设备地址
        """
        frame = self.build_read_frame(starting_address=self.regAddress)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def read_baudrate(self):
        """读取设备波特率并返回
        0x4800 : 4800
        0x9600 : 9600
        0x1920 : 19200
        0x5760 : 57600
        0x1152 : 115200
        Returns:
            int: 设备波特率
        """
        frame = self.build_read_frame(starting_address=self.regBaudrate)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        baud_map = {
            0x4800 : 4800,
            0x9600 : 9600,
            0x1920 : 19200,
            0x5760 : 57600,
            0x1152 : 115200
        } 
        baud = baud_map.get(raw_data, None)
        return baud
    
    def read_parity(self):
        """读取设备校验位并返回

        Returns:
            int: 设备校验位
        """
        frame = self.build_read_frame(starting_address=self.regParity)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def read_auto_report(self):
        """读取自动上报时间并返回

        Returns:
            int: 自动上报时间（秒）
        """
        frame = self.build_read_frame(starting_address=self.regAutoReport)
        response = self.send_request_get_response(frame)
        raw_data = (response[3] << 8) | response[4]
        return raw_data
    
    def set_address(self, new_address):
        """设置设备地址

        Args:
            new_address (int): 新设备地址（1-253）

        Returns:
            bool: 设置成功返回True，否则返回False
        """
        if not (1 <= new_address <= 253):
            raise ValueError("设备地址必须在1到253之间")
        
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.address
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regAddress >> 8) & 0xFF
        frame.StartingAddress_L = self.regAddress & 0xFF
        frame.Value_H = (new_address >> 8) & 0xFF
        frame.Value_L = new_address & 0xFF
        
        response = self.send_request_get_response(frame)
        # 验证响应是否正确
        if (response[0] == frame.AddressCode and
            response[1] == frame.FunctionCode and
            response[2] == frame.StartingAddress_H and
            response[3] == frame.StartingAddress_L and
            response[4] == frame.Quantity_H and
            response[5] == frame.Quantity_L):
            self.address = new_address  # 更新当前地址
            return True
        return False
    
    def set_baudrate(self, new_baudrate):
        """设置设备波特率

        Args:
            new_baudrate (int): 新波特率（如9600, 19200等）

        Returns:
            bool: 设置成功返回True，否则返回False
        """
        baudrate_map = {
            4800: 0x4800,
            9600: 0x9600,
            19200: 0x1920,
            57600: 0x5760,
            115200: 0x1152
        }
        
        if new_baudrate not in baudrate_map:
            raise ValueError("不支持的波特率")
        
        baudrate_code = baudrate_map[new_baudrate]
        
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.address
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regBaudrate >> 8) & 0xFF
        frame.StartingAddress_L = self.regBaudrate & 0xFF
        frame.Value_H = (baudrate_code >> 8) & 0xFF
        frame.Value_L = baudrate_code & 0xFF
        
        response = self.send_request_get_response(frame)
        # 验证响应是否正确
        if (response[0] == frame.AddressCode and
            response[1] == frame.FunctionCode and
            response[2] == frame.StartingAddress_H and
            response[3] == frame.StartingAddress_L and
            response[4] == frame.Quantity_H and
            response[5] == frame.Quantity_L):
            return True
        return False
    
    def set_parity(self, new_parity):
        """设置设备校验位

        Args:
            new_parity (int): 新校验位（0:无 1:奇校验 2:偶校验）

        Returns:
            bool: 设置成功返回True，否则返回False
        """
        if new_parity not in [0, 1, 2]:
            raise ValueError("校验位必须是0（无），1（奇校验）或2（偶校验）")
        
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.address
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regParity >> 8) & 0xFF
        frame.StartingAddress_L = self.regParity & 0xFF
        frame.Value_H = 0x00
        frame.Value_L = new_parity
        
        response = self.send_request_get_response(frame)
        # 验证响应是否正确
        if (response[0] == frame.AddressCode and
            response[1] == frame.FunctionCode and
            response[2] == frame.StartingAddress_H and
            response[3] == frame.StartingAddress_L and
            response[4] == frame.Quantity_H and
            response[5] == frame.Quantity_L):
            return True
        return False
    
    def set_auto_report(self, interval_seconds):
        """设置自动上报时间间隔

        Args:
            interval_seconds (int): 上报间隔时间（秒），0表示关闭自动上报

        Returns:
            bool: 设置成功返回True，否则返回False
        """
        if not (0 <= interval_seconds <= 65535):
            raise ValueError("上报间隔必须在0到65535秒之间")
        
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.address
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regAutoReport >> 8) & 0xFF
        frame.StartingAddress_L = self.regAutoReport & 0xFF
        frame.Value_H = (interval_seconds >> 8) & 0xFF
        frame.Value_L = interval_seconds & 0xFF
        
        response = self.send_request_get_response(frame)
        # 验证响应是否正确
        if (response[0] == frame.AddressCode and
            response[1] == frame.FunctionCode and
            response[2] == frame.StartingAddress_H and
            response[3] == frame.StartingAddress_L and
            response[4] == frame.Quantity_H and
            response[5] == frame.Quantity_L):
            return True
        return False

        
        
        
if __name__ == "__main__":
    soil_sensor_port = "/dev/soil_sensor"

    while True:
        soil_sensor = Modbus_Soil_Sensor(serial_port=soil_sensor_port)
        try:
            print(f"device address 0x{soil_sensor.read_address():02X}")
            print(f"device baudrate {soil_sensor.read_baudrate()}")
            for name, value in soil_sensor.read_all().items():
                print(f"{name}: {value}")
        except ModbusException as e:
            print(f"Modbus Exception: {e}")
        break
