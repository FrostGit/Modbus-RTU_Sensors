#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import serial
from crcmod import crcmod
from threading import Thread

"""
气体传感器485 Modbus-RTU协议通信底层库

传感器类型      地址
烟雾传感器      0x02
CO2传感器       0x03
氧气传感器      0x04
甲烷传感器      0x05
"""

class ModbusRTU_Frame:
    """
    Modbus RTU帧结构
    1 字节   1 字节      2 字节           2 字节       2 字节
    地址码 | 功能码 | 起始地址 | 寄存器数量 | CRC校验码
    0x01   | 0x03  | 0x0000  | 0x0002    | 0xFFFF
    说明:
    地址码: 设备地址
    功能码: 读保持寄存器 0x03
    起始地址: 要读取的第一个寄存器地址
    寄存器数量: 要读取的寄存器数量
    CRC校验码: CRC16校验码，低字节在前，高字节在后
    
    该类用于构建Modbus RTU请求帧,其中tobytes()方法会计算并附加CRC校验码。
    读取响应帧时需要单独计算CRC校验码进行验证。
    """
    def __init__(self):
        self.AddressCode = 0x00
        self.FunctionCode = 0x00
        self.StartingAddress_H = 0x00
        self.StartingAddress_L = 0x00
        self.Quantity_H = 0x00
        self.Quantity_L = 0x00
        self.CRC_L = 0x00
        self.CRC_H = 0x00
        self.crc16_modbus = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    
    def to_bytes(self):
        frame = bytearray()
        frame.append(self.AddressCode)
        frame.append(self.FunctionCode)
        frame.append(self.StartingAddress_H)
        frame.append(self.StartingAddress_L)
        frame.append(self.Quantity_H)
        frame.append(self.Quantity_L)
        crc16 = self.crc16_modbus(frame)
        self.CRC_L = crc16 & 0xFF
        self.CRC_H = (crc16 >> 8) & 0xFF
        frame.append(self.CRC_L)
        frame.append(self.CRC_H)
        # CRC will be calculated later
        return bytes(frame)
    
    def _calculate_crc(self, data):
        """计算Modbus CRC16校验码"""
        crc = self.crc16_modbus(data)
        return crc & 0xFFFF

class ModbusException(Exception):
    """Modbus特定异常"""
    pass       

class ModbusRTUDevice:
    """封装底层ModBus通信细节
    """
    def __init__(self, serial_port,
                 baudrate = 4800,
                 bytesize = serial.EIGHTBITS,
                 parity = serial.PARITY_NONE,
                 stopbits = serial.STOPBITS_ONE, 
                 timeout = 1):
        
        self.sensor_addrs = {
            "smoke_sensor": 0x02,
            "co2_sensor": 0x03,
            "oxygen_sensor": 0x04,
            "methane_sensor": 0x05
        }
        
        if parity == 'N' or parity == 0:
            parity = serial.PARITY_NONE
        elif parity == 'E' or parity == 2:
            parity = serial.PARITY_EVEN
        elif parity == 'O' or parity == 1:
            parity = serial.PARITY_ODD
        else:
            raise ValueError("无效的校验位参数")
        
        self.serial_port = serial.Serial(
            port=serial_port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
            write_timeout=timeout
        )
        self.crc16_modbus = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)


    def __del__(self):
        if hasattr(self,'serial_port') and self.serial_port.is_open:
            self.serial_port.close()

    def _clear_buffers(self):
        if hasattr(self,'serial_port') and self.serial_port.is_open:
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
    

    def _get_exception_text(self, exception_code):
        """获取Modbus异常码的文本描述"""
        exceptions = {
            0x01: "非法功能码",
            0x02: "非法数据地址",
            0x03: "非法数据值",
            0x04: "从站设备故障",
            0x05: "确认",
            0x06: "从站设备忙",
            0x08: "内存奇偶校验错误",
            0x0A: "网关路径不可用",
            0x0B: "网关目标设备无响应"
        }
        return exceptions.get(exception_code, f"未知异常 (0x{exception_code:02X})")
    
   
    def _calculate_crc(self, data):
        """计算Modbus CRC16校验码"""
        crc = self.crc16_modbus(data)
        return crc & 0xFFFF

    def read_response(self, expected_address=None, expected_function=None):
        """
        读取Modbus RTU响应帧
        
        Args:
            expected_address: 期望的从站地址（可选）
            expected_function: 期望的功能码（可选）
            
        Returns:
            bytes: 完整的Modbus RTU响应帧
            
        Raises:
            ModbusException: 各种Modbus错误
        """
        try:
            # 步骤1: 读取最小帧头 (5字节)
            header = self.serial_port.read(3)
            if len(header) < 3:
                raise ModbusException(f"超时: 只读取到 {len(header)} 字节，需要3字节帧头")
            
            address, function, byte_count = header[0], header[1], header[2]
            
            # 验证字节计数合理性
            if byte_count > 252:  # Modbus最大数据长度252字节
                raise ModbusException(f"无效字节计数: {byte_count} > 252")
            
            # 步骤2: 读取剩余数据
            remaining_bytes = byte_count + 2  # 数据 + CRC
            data_and_crc = self.serial_port.read(remaining_bytes)
            # print (f"Debug: 读取到的数据和CRC: {data_and_crc.hex().upper()}")
            if len(data_and_crc) < remaining_bytes:
                raise ModbusException(
                    f"数据不完整: 需要 {remaining_bytes} 字节，只读取到 {len(data_and_crc)}"
                )
            
            # 组合完整帧
            response = header + data_and_crc
            
            # 步骤3: CRC校验
            frame_without_crc = response[:-2]
            received_crc = (response[-1] << 8) | response[-2]  # 小端格式
            calculated_crc = self._calculate_crc(frame_without_crc)
            
            if received_crc != calculated_crc:
                raise ModbusException(
                    f"CRC校验失败: 计算值 0x{calculated_crc:04X}, 接收值 0x{received_crc:04X}"
                )
            
            # 步骤4: 验证地址和功能码（可选）
            if expected_address is not None and address != expected_address:
                raise ModbusException(
                    f"地址不匹配: 期望 0x{expected_address:02X}, 实际 0x{address:02X}"
                )
            
            # 检查异常响应
            if function & 0x80:
                exception_code = data_and_crc[0]
                raise ModbusException(
                    f"Modbus异常响应: 功能码 0x{function:02X}, "
                    f"异常码 0x{exception_code:02X} ({self._get_exception_text(exception_code)})"
                )
            
            if expected_function is not None and function != expected_function:
                raise ModbusException(
                    f"功能码不匹配: 期望 0x{expected_function:02X}, 实际 0x{function:02X}"
                )
            
            # 步骤5: 检查是否有剩余数据（可能表示帧错误）
            remaining = self.serial_port.in_waiting
            if remaining > 0:
                extra_data = self.serial_port.read(remaining)
                print(f"警告: 响应后有 {remaining} 字节额外数据: {extra_data.hex()}")
            
            return response
            
        except serial.SerialException as e:
            raise ModbusException(f"串口错误: {str(e)}") from e
        except Exception as e:
            # 清理缓冲区，准备下一次读取
            self._clear_buffers()
            raise
    
    def send_request_get_response(self, frame, retries=3, delay=0.1, debug=False):
        """
        Send a Modbus RTU request frame and get the response.
        Args:
            frame (ModbusRTU_Frame): The Modbus RTU frame to send.
            retries (int): Number of retries if no response is received.
            delay (float): Delay between retries in seconds.
        Returns:
            bytes: The response bytes received from the device.
        """
        for attempt in range(retries):
            try:
                # 清理缓冲区
                self._clear_buffers()
                
                # 发送请求帧
                self.serial_port.write(frame.to_bytes())
                self.serial_port.flush()
                
                # 读取响应帧
                expected_address = frame.AddressCode
                expected_function = frame.FunctionCode
                response = self.read_response(expected_address, expected_function)

                if not debug:
                    return response
                
                for byte in response:
                    print(f"0x{byte:02X} ", end="")
                print("")
                
                return response
                

            except ModbusException as e:
                print(f"尝试 {attempt + 1} 失败: {str(e)}")

                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                raise
            except Exception as e:
                print(f"意外错误: {str(e)}")
                raise e
        raise ModbusException("所有尝试均失败，未收到响应")


class Modbus_Gas_Sensor:
    def __init__(self, address=0x03):
        self.address = address
        # TODO:需要根据资料填写

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
        frame.Quantity_H = (new_address >> 8) & 0xFF
        frame.Quantity_L = new_address & 0xFF
        
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
        frame.Quantity_H = (baudrate_code >> 8) & 0xFF
        frame.Quantity_L = baudrate_code & 0xFF
        
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
        frame.Quantity_H = (new_parity >> 8) & 0xFF
        frame.Quantity_L = new_parity & 0xFF
        
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
        frame.Quantity_H = (interval_seconds >> 8) & 0xFF
        frame.Quantity_L = interval_seconds & 0xFF
        
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
    gas_hub_port = "/dev/gas_hub"
    soil_sensor_port = "/dev/soil_sensor"
    heart_reat_port = "/dev/heart_rate_sensor"
    weather_sensor_port = "/dev/weather_sensor"
    
    _debug_test_gas_sensor_485_ = False
    _debug_test_soil_sensor_485_ = True
    _debug_test_weather_sensor_485_ = False
    _debug_test_heart_rate_sensor_485_ = False



    
    if _debug_test_soil_sensor_485_:
        while True:
            soil_sensor = Modbus_Soil_Sensor(serial_port=soil_sensor_port)
            
            delay_time = 0.12
            
            print(f"device address 0x{soil_sensor.read_address():02X}")
            time.sleep(delay_time)
            print(f"device baudrate {soil_sensor.read_baudrate()}")
            time.sleep(delay_time)
            print(f"Temperature {soil_sensor.read_temperature()} °C")
            time.sleep(delay_time)
            print(f"Humidity {soil_sensor.read_humi()} %")
            time.sleep(delay_time)
            print(f"EC {soil_sensor.read_EC()} us/cm")
            time.sleep(delay_time)
            print(f"Salty {soil_sensor.read_salty()} mg/L")
            time.sleep(delay_time)
            print(f"Nitro {soil_sensor.read_nitro()} mg/kg")
            time.sleep(delay_time)
            print(f"phosphorus {soil_sensor.read_phosphorus()} mg/kg")
            time.sleep(delay_time)
            print(f"potassium {soil_sensor.read_potassium()} mg/kg")
            time.sleep(delay_time)
            print(f"PH {soil_sensor.read_PH()}")
            time.sleep(delay_time)
            break


    if _debug_test_gas_sensor_485_:
        gas_sensor = ModbusRTUDevice(serial_port=gas_hub_port, baudrate=4800, timeout=1)
        frame = gas_sensor.build_read_frame("co2_sensor", starting_address=0x0002)
        gas_sensor.send_frame(frame)
        response = gas_sensor.read_response()
        print("gas_hub Received response:", response.hex().upper())
        