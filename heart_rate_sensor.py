#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import serial

class HeartRateSensor:
    """
    心率传感器类，提供与心率传感器通信的基本功能
    """
    def __init__(self, serial_port, baudrate=38400, timeout=1):
        self.serial_port = serial.Serial(port=serial_port,
                                         baudrate=baudrate,
                                         timeout=timeout)
    
    def __del__(self):
        self.close()
    
    def close(self):
        if self.serial_port.is_open:
            self.serial_port.close()
        
        

if __name__ == "__main__":
    """
    串口发送0x8A 测试 HeartRate模块的基本功能
    """
    heart_reat_port = "/dev/heart_rate_sensor"  # 心率传感器串口路径
    baudrate = 38400  # 波特率
    timeout = 1  # 超时时间（秒）
    command = bytes([0x8A])  # 发送的命令字节
    serial_port = serial.Serial(port=heart_reat_port,
                                baudrate=baudrate,
                                timeout=timeout)
    try:
        serial_port.write(command)
        time.sleep(0.1)  # 等待传感器响应
        if serial_port.in_waiting > 0:
            response = serial_port.read(serial_port.in_waiting)
            heart_rate = int.from_bytes(response, byteorder='big')
            print(f"Heart Rate: {heart_rate} bpm")
        time.sleep(1)  # 每秒读取一次心率
    except Exception as e:
        print(f"Error: {e}")
    finally:
        serial_port.close()