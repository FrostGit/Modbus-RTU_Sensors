#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from lib_ModbusRTUDevice import ModbusRTUDevice, ModbusRTU_Frame, ModbusException

class PowerSensor(ModbusRTUDevice):
    """
    电源传感器类，提供与电源传感器通信的基本功能

    Args:
        serial_port: 串口路径
        baudrate: 波特率，默认9600
        timeout: 超时时间，默认1秒
    
    Registers:
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
    regEnergy   = 0x0BBE        # 累计电量寄存器地址    长度2 fn: 3
    regBaudrate = 0x0C1C        # 波特率寄存器地址      长度1 fn: 3,6,16    范围: 1-6 对应波特率 4800,9600,19200,38400,57600,115200 默认： 2
    regAddress  = 0x0C21        # 设备地址寄存器地址    长度1 fn: 3,6,16    范围: 1-247 默认：1
    regClearEnergy = 0x0C26     # 清除累计电量寄存器地址 长度1 fn: 3,6,16    写入0x1234清零累计电量
    regUnits      = 0x0C80      # 单位寄存器地址        长度1 fn: 3,6,16    范围: 0-3 对应 单位 Wh,mWh,Ah,mAh 默认：0
    regSampleRate = 0x0C81      # 采样频率寄存器地址    长度1 fn: 3,6,16     范围: 1-20 对应 1-20Hz 默认：2
    regEnergyAccMode = 0x0C82   # 电量积累模式寄存器地址 长度1 fn: 3,6,16    范围: 0-3 对应 仅正向积累,仅负向积累,双向积累，双向正累计 默认：0
    regVoltageLevel = 0x0C83    # 电压量程寄存器地址    长度1 fn: 3,6,16    范围: 0-2 对应 自动挡,60V档,400V档(400V档时最低量程为5V) 默认：0
    regCoulombVoltage = 0x0C84  # 库伦计修正电压寄存器地址 长度1 fn: 3,6,16  默认:0 输入电池的额定电压进行修正
    regDeviceModel = 0x0F3C     # 设备型号寄存器地址    长度10 fn: 3 固定为"19080201"
    default_address = 0x01     # 默认设备地址
    default_units = 0       # 默认单位 Wh

    def __init__(self, serial_port, baudrate=9600, timeout=1):
        self.address = self.default_address
        self.unit = self.default_units
        super().__init__(serial_port = serial_port, baudrate=baudrate, timeout=timeout)
        
    
    def __del__(self):
        super().__del__()
    
    def close(self):
        return super().close()
    
    def get_device_address(self):
        """获取设备地址，默认地址为1"""
        return self.address

    def get_device_unit(self):
        """获取当前单位设置"""
        unit_map = {
            0: "Wh",
            1: "mWh",
            2: "Ah",
            3: "mAh"
        }
        return unit_map.get(self.unit, "Unknown")

    def build_read_frame(self, start_address, length = 1):
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x03  # 读保持寄存器
        frame.StartingAddress_H = (start_address >> 8) & 0xFF
        frame.StartingAddress_L = start_address & 0xFF
        frame.Quantity_H = (length >> 8) & 0xFF
        frame.Quantity_L = length & 0xFF
        return frame

    def read_voltage(self):
        """
        读取电压值，原始数据为有符号整形，单位V
        Returns:
            电压值,浮点数，单位V
        
        """
        print()
        frame = self.build_read_frame(self.regVoltage, 2)
        response = self.send_request_get_response(frame)
        if len(response) == 9:
            voltage_raw = (response[3] << 24) | (response[4] << 16) | (response[5] << 8) | response[6]
            print(voltage_raw)
            if voltage_raw >= 0x80000000:  # 处理有符号整数
                voltage_raw -= 0x100000000
            print(voltage_raw)
            voltage = voltage_raw / 1000.0 # 数据为mV,转换为实际电压值
            return voltage
        else:
            raise ModbusException("Failed to read voltage")
    
    def read_current(self):
        """读取电流值，单位A
        
        Returns:
            电流值,浮点数，单位A
        """
        frame = self.build_read_frame(self.regCurrent, 2)
        response = self.send_request_get_response(frame)
        if len(response) == 9:
            current_raw = (response[3] << 24) | (response[4] << 16) | (response[5] << 8) | response[6]
            if current_raw >= 0x80000000:  # 处理有符号整数
                current_raw -= 0x100000000
            current = current_raw / 1000.0 # 数据为mA,转换为实际电流值
            return current
        else:
            raise ModbusException("Failed to read current")
        
    def read_power(self):
        """读取功率值，单位W
        
        Returns:
            功率值,整数，单位W
        """
        frame = self.build_read_frame(self.regPower, 2)
        response = self.send_request_get_response(frame)
        if len(response) == 9:
            power_raw = (response[3] << 24) | (response[4] << 16) | (response[5] << 8) | response[6]
            if power_raw >= 0x80000000:  # 处理有符号整数
                power_raw -= 0x100000000
            power = power_raw / 1000.0 # 数据为mW,转换为实际功率值
            return power
        else:
            raise ModbusException("Failed to read power")
        
    def read_energy(self):
        """读取累计电量值，单位Wh
        
        Returns:
            累计电量值,浮点数，单位Wh
        """
        frame = self.build_read_frame(self.regEnergy, 2)
        response = self.send_request_get_response(frame)
        if len(response) == 9:
            energy_raw = (response[3] << 24) | (response[4] << 16) | (response[5] << 8) | response[6]
            if energy_raw >= 0x80000000:  # 处理有符号整数
                energy_raw -= 0x100000000
            energy = energy_raw /10.0 # 数据为0.1Wh,转换为实际电量值
            return energy
        else:
            raise ModbusException("Failed to read energy")

    def read_baudrate(self):
        """读取当前波特率设置
        
        Returns:
            波特率值，可能值为 4800,9600,19200,38400,57600,115200

        """
        frame = self.build_read_frame(self.regBaudrate, 1)
        response = self.send_request_get_response(frame)
        if len(response) == 7:
            baudrate_code = response[4]
            baudrate_map = {
                1: 4800,
                2: 9600,
                3: 19200,
                4: 38400,
                5: 57600,
                6: 115200
            }
            return baudrate_map.get(baudrate_code, "Unknown")
        else:
            raise ModbusException("Failed to read baudrate")
    
    def read_address(self):
        """读取当前设备地址
        
        Returns:
            设备地址值，范围1-247

        """
        frame = self.build_read_frame(self.regAddress, 1)
        response = self.send_request_get_response(frame)
        if len(response) == 7:
            device_address = response[4]
            return device_address
        else:
            raise ModbusException("Failed to read device address")

    def read_units(self):
        """读取当前单位设置
        
        Returns:
            单位字符串，可能值为 "Wh","mWh","Ah","mAh"
        """
        frame = self.build_read_frame(self.regUnits, 1)
        response = self.send_request_get_response(frame)
        if len(response) == 7:
            units_code = response[4]
            self.unit = units_code
            return self.get_device_unit()
        else:
            raise ModbusException("Failed to read units")    
    
    def read_sample_rate(self):
        """读取当前采样频率设置，单位Hz
        
        Returns:
            # 采样频率值，范围1-20Hz
        """
        frame = self.build_read_frame(self.regSampleRate, 1)
        response = self.send_request_get_response(frame)
        if len(response) == 7:
            sample_rate = response[4]
            return sample_rate
        else:
            raise ModbusException("Failed to read sample rate")
        
    def read_energy_accumulation_mode(self):
        """
        读取当前电量积累模式设置

        Returns:
            "仅正向积累"
            "仅负向积累"
            "双向积累"
            "双向正累计"
        """
        frame = self.build_read_frame(self.regEnergyAccMode, 1)
        response = self.send_request_get_response(frame)
        if len(response) == 7:
            mode_code = response[4]
            mode_map = {
                0: "仅正向积累",
                1: "仅负向积累",
                2: "双向积累",
                3: "双向正累计"
            }
            return mode_map.get(mode_code, "Unknown")
        else:
            raise ModbusException("Failed to read energy accumulation mode")
        
    def read_voltage_level(self):
        """读取当前电压量程设置
        
        Returns:
            "自动挡"
            "60V档"
            "400V档"
        """
        frame = self.build_read_frame(self.regVoltageLevel, 1)
        response = self.send_request_get_response(frame)
        if len(response) == 7:
            level_code = response[4]
            level_map = {
                0: "自动挡",
                1: "60V档",
                2: "400V档"
            }
            return level_map.get(level_code, "Unknown")
        else:
            raise ModbusException("Failed to read voltage level")
        
    def read_coulomb_voltage(self):
        """读取当前库伦计修正电压设置，单位V
        
        Returns:
            库伦计修正电压值，32位浮点数，单位V
        """
        frame = self.build_read_frame(self.regCoulombVoltage, 2)
        response = self.send_request_get_response(frame)
        if len(response) == 9:
            coulomb_voltage = (response[3] << 24) | (response[4] << 16) | (response[5] << 8) | response[6]
            return coulomb_voltage
        else:
            raise ModbusException("Failed to read coulomb voltage")
        
    def read_device_model(self):
        """读取设备型号字符串，固定为"19080201"
        
        Returns:
            设备型号字符串
        """
        frame = self.build_read_frame(self.regDeviceModel, 10)
        response = self.send_request_get_response(frame)
        if len(response) == 23:
            model_bytes = response[3:23]
            model_str = bytes(model_bytes).decode('utf-8').rstrip('\x00')
            return model_str
        else:
            raise ModbusException("Failed to read device model")

    def set_baudrate(self, baudrate_code):
        """设置波特率，baudrate_code范围1-6
        1: 4800
        2: 9600
        3: 19200
        4: 38400
        5: 57600
        6: 115200
        """
        if baudrate_code < 1 or baudrate_code > 6:
            raise ValueError("Invalid baudrate code. Must be between 1 and 6.")
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regBaudrate >> 8) & 0xFF
        frame.StartingAddress_L = self.regBaudrate & 0xFF
        frame.Quantity_H = 0x00
        frame.Quantity_L = baudrate_code
        request_frame = frame.to_bytes()
        response = self.send_request_get_response(request_frame)
        if len(response) == 8:
            return True
        else:
            raise ModbusException("Failed to set baudrate")
    
    def set_address(self, new_address):
        """设置设备地址，new_address范围1-247"""
        if new_address < 1 or new_address > 247:
            raise ValueError("Invalid device address. Must be between 1 and 247.")
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regAddress >> 8) & 0xFF
        frame.StartingAddress_L = self.regAddress & 0xFF
        frame.Quantity_H = 0x00
        frame.Quantity_L = new_address
        request_frame = frame.to_bytes()
        response = self.send_request_get_response(request_frame)
        if len(response) == 8:
            self.address = new_address  # 更新当前设备地址
            return True
        else:
            raise ModbusException("Failed to set device address")

    def clear_energy(self):
        """清除累计电量，写入0x1234清零"""
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regClearEnergy >> 8) & 0xFF
        frame.StartingAddress_L = self.regClearEnergy & 0xFF
        frame.Quantity_H = 0x12
        frame.Quantity_L = 0x34
        request_frame = frame.to_bytes()
        response = self.send_request_get_response(request_frame)
        if len(response) == 8:
            return True
        else:
            raise ModbusException("Failed to clear energy")
    
    def set_units(self, units_code):
        """设置单位，units_code范围0-3
        0: Wh
        1: mWh
        2: Ah
        3: mAh
        """
        if units_code < 0 or units_code > 3:
            raise ValueError("Invalid units code. Must be between 0 and 3.")
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regUnits >> 8) & 0xFF
        frame.StartingAddress_L = self.regUnits & 0xFF
        frame.Quantity_H = 0x00
        frame.Quantity_L = units_code
        request_frame = frame.to_bytes()
        response = self.send_request_get_response(request_frame)
        if len(response) == 8:
            self.unit = units_code  # 更新当前单位设置
            return True
        else:
            raise ModbusException("Failed to set units")
        
    def set_sample_rate(self, sample_rate):
        """设置采样频率，sample_rate范围1-20Hz"""
        if sample_rate < 1 or sample_rate > 20:
            raise ValueError("Invalid sample rate. Must be between 1 and 20 Hz.")
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regSampleRate >> 8) & 0xFF
        frame.StartingAddress_L = self.regSampleRate & 0xFF
        frame.Quantity_H = 0x00
        frame.Quantity_L = sample_rate
        request_frame = frame.to_bytes()
        response = self.send_request_get_response(request_frame)
        if len(response) == 8:
            return True
        else:
            raise ModbusException("Failed to set sample rate")
        
    def set_energy_accumulation_mode(self, mode_code):
        """设置电量积累模式，mode_code范围0-3
        0: 仅正向积累
        1: 仅负向积累
        2: 双向积累
        3: 双向正累计
        """
        if mode_code < 0 or mode_code > 3:
            raise ValueError("Invalid mode code. Must be between 0 and 3.")
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regEnergyAccMode >> 8) & 0xFF
        frame.StartingAddress_L = self.regEnergyAccMode & 0xFF
        frame.Quantity_H = 0x00
        frame.Quantity_L = mode_code
        request_frame = frame.to_bytes()
        response = self.send_request_get_response(request_frame)
        if len(response) == 8:
            return True
        else:
            raise ModbusException("Failed to set energy accumulation mode")
        
    def set_coulomb_voltage(self, voltage):
        """设置库伦计修正电压，单位V **请注意，该函数未完全实现，请尽量避免使用**
        
        Args:
            voltage: 库伦计修正电压值，32位浮点数，单位V
        """
        # TODO: 完善浮点数写入功能
        if voltage < 0 or voltage > 1000:
            raise ValueError("Invalid coulomb voltage. Must be between 0 and 1000 V.")
        frame = ModbusRTU_Frame()
        frame.AddressCode = self.get_device_address()
        frame.FunctionCode = 0x06  # 写单个寄存器
        frame.StartingAddress_H = (self.regCoulombVoltage >> 8) & 0xFF
        frame.StartingAddress_L = self.regCoulombVoltage & 0xFF
        voltage_int = int(voltage)
        frame.Quantity_H = (voltage_int >> 8) & 0xFF
        frame.Quantity_L = voltage_int & 0xFF
        request_frame = frame.to_bytes()
        response = self.send_request_get_response(request_frame)
        if len(response) == 8:
            return True
        else:
            raise ModbusException("Failed to set coulomb voltage")





if __name__ == "__main__":
    """
    串口发送 >>GetVal 测试 Power模块的基本功能
    """
    power_port = "/dev/power_sensor"  # 电源传感器串口路径
    power_sensor = PowerSensor(power_port, baudrate=9600, timeout=1)
    try:
        voltage = power_sensor.read_voltage()
        print(f"Voltage: {voltage} V")
        time.sleep(0.1)
        
        current = power_sensor.read_current()
        print(f"Current: {current} A")
        time.sleep(0.1)
        
        power = power_sensor.read_power()
        print(f"Power: {power} W")
        time.sleep(0.1)
        
        energy = power_sensor.read_energy()
        print(f"Energy: {energy} Wh")
        time.sleep(0.1)
        
        units = power_sensor.read_units()
        print(f"Units: {units}")
        time.sleep(0.1)
        
        voltage_level = power_sensor.read_voltage_level()
        print(f"Voltage Level: {voltage_level}")
        time.sleep(0.1)
        
        baudrate = power_sensor.read_baudrate()
        print(f"Baudrate: {baudrate} bps")
        time.sleep(0.1)
        
        address = power_sensor.read_address()
        print(f"Device Address: 0x{address:02X}")
        time.sleep(0.1)
        
        sample_rate = power_sensor.read_sample_rate()
        print(f"Sample Rate: {sample_rate} Hz")
        time.sleep(0.1)
        
        accumulation_mode = power_sensor.read_energy_accumulation_mode()
        print(f"Energy Accumulation Mode: {accumulation_mode}")
        time.sleep(0.1)
        
    except ModbusException as e:
        print(f"Modbus Error: {str(e)}")
    finally:
        power_sensor.close()
        print("Serial port closed.")