#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import serial
from lib_ModbusRTUDevice import ModbusRTUDevice, ModbusRTU_Frame, ModbusException

class PowerSensor(ModbusRTUDevice):
    """
    电源传感器类，提供与电源传感器通信的基本功能
    args:
        serial_port: 串口路径
        baudrate: 波特率，默认9600
        timeout: 超时时间，默认1秒
    registers:
        regVoltage: 电压寄存器地址                  长度2寄存器 有符号整数 Bigending fn: 3 除以1000得到实际电压值 单位: V
        regCurrent: 电流寄存器地址                  长度2寄存器 有符号整数 Bigending fn: 3 除以1000得到实际电流值 单位: A
        regPower: 功率寄存器地址
        regEnergy: 累计电量寄存器地址
        regBaudrate: 波特率寄存器地址
        regAddress: 设备地址寄存器地址
        regClearEnergy: 清除累计电量寄存器地址
        regUnits: 单位寄存器地址
        regSampleRate: 采样频率寄存器地址
        regEnergyAccMode: 电量积累模式寄存器地址
        regVoltageLevel: 电压量程寄存器地址
        regCoulombVoltage: 库伦计修正电压寄存器地址
        regDeviceModel: 设备型号寄存器地址
    
    """
    
    regVoltage  = 0x0BB8        # 电压寄存器地址        长度2寄存器长度 fn: 3
    regCurrent  = 0x0BBA        # 电流寄存器地址        长度2 fn: 3
    regPower    = 0x0BBC        # 功率寄存器地址        长度2 fn: 3
    regEnergy   = 0x0BC0        # 累计电量寄存器地址    长度2 fn: 3
    regBaudrate = 0x0C1C        # 波特率寄存器地址      长度1 fn: 3,6,16    范围: 1-6 对应波特率 4800,9600,19200,38400,57600,115200 默认： 2
    regAddress  = 0x0C21        # 设备地址寄存器地址    长度1 fn: 3,6,16    范围: 1-247 默认：1
    regClearEnergy = 0x0C26     # 清除累计电量寄存器地址 长度1 fn: 3,6,16    写入任意值清零累计电量
    regUnits      = 0x0C80      # 单位寄存器地址        长度1 fn: 3,6,16    范围: 0-3 对应 单位 Wh,mWh,Ah,mAh 默认：0
    regSampleRate = 0x0C81      # 采样频率寄存器地址    长度1 fn: 3,6,16     范围: 1-20 对应 1-20Hz 默认：2
    regEnergyAccMode = 0x0C82   # 电量积累模式寄存器地址 长度1 fn: 3,6,16    范围: 0-3 对应 仅正向积累,仅负向积累,双向积累，双向正累计 默认：0
    regVoltageLevel = 0x0C83    # 电压量程寄存器地址    长度1 fn: 3,6,16    范围: 0-2 对应 自动挡,60V档,400V档(400V档时最低量程为5V) 默认：0
    regCoulombVoltage = 0x0C84  # 库伦计修正电压寄存器地址 长度1 fn: 3,6,16  默认:0 输入电池的额定电压进行修正
    regDeviceModel = 0x0F3C     # 设备型号寄存器地址    长度10 fn: 3 固定为"19080201"

    def __init__(self, serial_port, baudrate=9600, timeout=1):
        self.serial_port = serial.Serial(port=serial_port,
                                         baudrate=baudrate,
                                         timeout=timeout)
    
    def __del__(self):
        super().__del__()
    
    def close(self):
        return super().close()
    # TODO:协议帧建立
        
        

if __name__ == "__main__":
    """
    串口发送 >>GetVal 测试 Power模块的基本功能
    """
    power_port = "/dev/power_sensor"  # 电源传感器串口路径
    baudrate = 9600  # 波特率
    timeout = 1  # 超时时间（秒）
    command = bytes(">>GetVal", 'utf-8')  # 发送的命令字节
    serial_port = serial.Serial(port=power_port,
                                baudrate=baudrate,
                                timeout=timeout)
    try:
        serial_port.write(command)
        print("Command sent:", command)
        time.sleep(0.1)  # 等待传感器响应
        if serial_port.in_waiting > 0:
            response = serial_port.read(serial_port.in_waiting)
            print(f"Power: {response.decode('utf-8')} W")
        time.sleep(1)  # 每秒读取一次功率
    except Exception as e:
        print(f"Error: {e}")
    finally:
        serial_port.close()