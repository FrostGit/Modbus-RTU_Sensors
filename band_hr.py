#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import serial
import struct

"""
生命体征检测模块 串口参数 38400 8N1
协议返回信息原始结构体定义
typedef struct {
    uint8_t start_byte;     // 起始字节，固定为0xFF
    int8_t acdata[64];      // 心律波形数据，范围为-128到127
    uint8_t heart_rate;     // 心率值
    uint8_t spo2;           // 血氧饱和度值
    uint8_t bk;             // 微循环
    uint8_t rsv[8];         // 保留字节 rsv[0] - rsv[2] 保留 rsv[3] 收缩压 rsv[4] 舒张压 rsv[5] - rsv[7] 保留
    } RT_PACK;
    
"""


class BandHrPacket:
    """
    生命体征数据包类，用于解析和封装心率传感器的数据包
    总长度：88字节 76字节有效
    """
    # 数据包格式定义
    PACKET_SIZE = 88
    VALID_DATA_SIZE = 76
    PACKET_FORMAT = '<B64bBBB8s'  # struct.unpack格式字符串
    START_BYTE = 0xFF
    
    def __init__(self, data: bytes = None):
        """
        初始化数据包
        :param data: 原始二进制数据，如果提供则直接解析
        """
        # 初始化所有属性
        self.start_byte = 0xFF
        self.acdata = []  # 心律波形数据 (64个int8值)
        self.heart_rate = 0  # 心率值
        self.spo2 = 0  # 血氧饱和度
        self.bk = 0  # 微循环
        self.systolic_pressure = 0  # 收缩压 (rsv[3])
        self.diastolic_pressure = 0  # 舒张压 (rsv[4])
        
        if data is not None:
            self.parse(data)
    
    def parse(self, data: bytes) -> bool:
        """
        解析二进制数据包
        :param data: 原始二进制数据
        :return: 解析是否成功
        """
        if len(data) < self.PACKET_SIZE:
            print(f"错误：数据长度不足，期望{self.PACKET_SIZE}字节，实际{len(data)}字节")
            return False
        
        if data[0] != self.START_BYTE:
            print(f"错误：起始字节不匹配，期望0x{self.START_BYTE:02X}，实际0x{data[0]:02X}")
            return False
        data = data[:self.VALID_DATA_SIZE]
        try:
            # 使用struct解析数据
            print(f"length of data: {len(data)}")
            for i in range(len(data)):
                print(f"data[{i}]: 0x{data[i]:02X}", end=' ')
            print('')
            unpacked = struct.unpack(self.PACKET_FORMAT, data[:self.PACKET_SIZE])
            
            # 分配解析结果
            self.start_byte = unpacked[0]
            self.acdata = list(unpacked[1:65])  # 64个心律波形数据
            self.heart_rate = unpacked[65]
            print(f"heart_rate: 0x{self.heart_rate:02X}")
            self.spo2 = unpacked[66]
            self.bk = unpacked[67]
            
            # 解析rsv[8]
            rsv = unpacked[68]
            self.systolic_pressure = rsv[3]
            self.diastolic_pressure = rsv[4]
            return True
        except struct.error as e:
            print(f"错误：解析数据失败 - {e}")
            return False
    
    def to_dict(self) -> dict:
        """
        将数据包转换为字典格式
        :return: 包含所有解析数据的字典
        """
        return {
            'start_byte': f'0x{self.start_byte:02X}',
            'heart_rate': self.heart_rate,
            'spo2': self.spo2,
            'bk': self.bk,
            'systolic_pressure': self.systolic_pressure,
            'diastolic_pressure': self.diastolic_pressure,
            'acdata_count': len(self.acdata),
        }
    
    def __str__(self) -> str:
        """
        返回可读的数据包字符串表示
        """
        return f"""
        心率传感器数据包:
        - 起始字节: 0x{self.start_byte:02X}
        - 心率: {self.heart_rate} bpm
        - 血氧饱和度: {self.spo2}%
        - 微循环: {self.bk}
        - 收缩压: {self.systolic_pressure} mmHg
        - 舒张压: {self.diastolic_pressure} mmHg
        - 心律波形数据点数: {len(self.acdata)}
        """


class HeartRateSensor:
    """
    心率传感器类，提供与心率传感器通信的基本功能
    """
    # 定义协议结构体格式
    CMD_MODE_WORK       = 0x8A  # 开启工作模式命令字节
    CMD_MODE_STANDBY    = 0x88  # 进入待机模式命令字节
    CMD_GATHER_ON       = 0x8E  # 开启体检模式
    CMD_GATHER_OFF      = 0x8C  # 关闭体检模式


    def __init__(self, serial_port, baudrate=38400, timeout=1):
        self.serial_port = serial.Serial(port=serial_port,
                                         baudrate=baudrate,
                                         timeout=timeout)
    
    def __del__(self):
        self.close()
    
    def close(self):
        if self.serial_port.is_open:
            self.serial_port.close()
    
    def send_command(self, command: int) -> bool:
        """
        发送命令到传感器
        :param command: 命令字节
        :return: 是否发送成功
        """
        try:
            self.serial_port.write(bytes([command]))
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False
    
    def read_packet(self) -> BandHrPacket:
        """
        从串口读取一个完整的数据包
        :return: 解析后的BandHrPacket对象，如果失败返回None
        """
        try:
            # 等待数据到达
            if self.serial_port.in_waiting < BandHrPacket.PACKET_SIZE:
                return None
            
            # 读取数据包
            raw_data = self.serial_port.read(BandHrPacket.PACKET_SIZE)
            
            # 解析数据包
            packet = BandHrPacket(raw_data)
            return packet if all([
                packet.start_byte == BandHrPacket.START_BYTE,
                len(raw_data) == BandHrPacket.PACKET_SIZE
            ]) else None
        except Exception as e:
            print(f"读取数据包失败: {e}")
            return None
    
    def read_packets(self, count: int = 1, timeout: float = None) -> list:
        """
        连续读取多个数据包
        :param count: 要读取的数据包数量
        :param timeout: 超时时间（秒），None表示不设置超时
        :return: 成功解析的BandHrPacket列表
        """
        packets = []
        start_time = time.time() if timeout else None
        
        while len(packets) < count:
            if timeout and (time.time() - start_time) > timeout:
                print(f"读取超时，仅成功读取 {len(packets)} 个数据包")
                break
            
            packet = self.read_packet()
            if packet:
                packets.append(packet)
            else:
                time.sleep(0.01)  # 避免CPU占用过高
        
        return packets

if __name__ == "__main__":
    """
    心率传感器使用示例
    """
    heart_rate_port = "/dev/hr_band"  # 心率传感器串口路径
    
    baudrate = 38400  # 波特率
    timeout = 1  # 超时时间（秒）
    
    try:
        # 初始化传感器
        sensor = HeartRateSensor(heart_rate_port, baudrate=baudrate, timeout=timeout)
        # 提前发送一个停止刷新命令，确保传感器处于已知状态
        # sensor.send_command(sensor.CMD_MODE_STANDBY)
        # time.sleep(0.5)
        
        # 发送工作模式命令
        if sensor.send_command(sensor.CMD_MODE_WORK):
            for i in range(2):
                sensor.send_command(sensor.CMD_MODE_WORK)
            print("已发送工作模式命令")
            while True:
                packet = sensor.read_packet()
                if packet:
                    print("成功解析数据包:")
                    print(packet)
                    print("\n字典格式数据(Hex):")
                    print(packet.to_dict())
                else:
                    print("等待数据包...")
                time.sleep(1)
        
            
            # 或者连续读取多个数据包
            # packets = sensor.read_packets(count=5, timeout=10)
            # for i, pkt in enumerate(packets):
            #     print(f"\n数据包 {i+1}:")
            #     print(f"  心率: {pkt.heart_rate} bpm")
            #     print(f"  血氧: {pkt.spo2}%")
            #     print(f"  疲劳指数: {pkt.fatigue_index}")
        
        # 发送待机命令
        sensor.send_command(sensor.CMD_MODE_STANDBY)
        print("已发送待机模式命令")
        
    except FileNotFoundError:
        print(f"错误：串口设备 {heart_rate_port} 未找到")
    except Exception as e:
        print(f"错误: {e}")
    finally:
        if 'sensor' in locals():
            sensor.send_command(sensor.CMD_MODE_STANDBY)
            time.sleep(0.1)
            sensor.close()