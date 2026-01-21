#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import serial
from crcmod import crcmod


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
        
    def close(self):
        if hasattr(self,'serial_port') and self.serial_port.is_open:
            self.serial_port.close()
    

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



        
        
if __name__ == "__main__":
    pass