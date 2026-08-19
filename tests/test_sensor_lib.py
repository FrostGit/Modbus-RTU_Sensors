#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Modbus 库与传感器驱动回归测试（假串口，无需真实硬件）

运行: python3 tests/test_sensor_lib.py

覆盖:
- 读/写帧构建（含 CRC 与标准样例一致）
- read_response 解析: 读响应(0x03) / 写回显(0x06) / 异常响应 / CRC 错误
- 端到端 send_request_get_response 往返
- 各驱动 read_all() 批量读解析（气象/土壤/电源/气体 HUB）
- 生命体征 88 字节包解析
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib_ModbusRTUDevice as lib  # noqa: E402
from lib_ModbusRTUDevice import ModbusRTU_Frame, ModbusRTUDevice, ModbusException  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# 假串口
# ═══════════════════════════════════════════════════════════════
class FakeSerial:
    """模拟 pyserial.Serial：write 记录发送帧；read 依次吐出脚本化的响应帧"""

    def __init__(self, responses=()):
        self.is_open = True
        self.written = []
        self._queue = list(responses)
        self._buf = bytearray()

    def write(self, data):
        self.written.append(bytes(data))
        return len(data)

    def flush(self):
        pass

    def read(self, n):
        if not self._buf and self._queue:
            self._buf.extend(self._queue.pop(0))
        data = bytes(self._buf[:n])
        del self._buf[:n]
        return data

    def reset_input_buffer(self):
        self._buf.clear()

    def reset_output_buffer(self):
        pass

    def close(self):
        self.is_open = False

    @property
    def in_waiting(self):
        return len(self._buf)


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ 0xA001) if (crc & 1) else (crc >> 1)
    return crc & 0xFFFF


def with_crc(payload: bytes) -> bytes:
    c = crc16(payload)
    return payload + bytes([c & 0xFF, c >> 8])  # 低字节在前


def make_device(response: bytes = None, responses=()):
    """绕过 serial.Serial 构造一个带假串口的 ModbusRTUDevice"""
    dev = ModbusRTUDevice.__new__(ModbusRTUDevice)
    dev.serial_port = FakeSerial([response] if response is not None else list(responses))
    dev.crc16_modbus = lib.crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    return dev


# ═══════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════
def test_frame_read():
    f = ModbusRTU_Frame()
    f.AddressCode, f.FunctionCode = 0x01, 0x03
    f.StartingAddress_H, f.StartingAddress_L = 0x00, 0x00
    f.Quantity_H, f.Quantity_L = 0x00, 0x02
    data = f.to_bytes()
    # 标准样例: 01 03 00 00 00 02 C4 0B
    assert data.hex().upper() == "010300000002C40B", data.hex()


def test_frame_write_uses_value():
    f = ModbusRTU_Frame()
    f.AddressCode, f.FunctionCode = 0x01, 0x06
    f.StartingAddress_H, f.StartingAddress_L = 0x0C, 0x21
    f.Value_H, f.Value_L = 0x00, 0x02
    data = f.to_bytes()
    # 写帧应使用 Value 而非 Quantity: 01 06 0C 21 00 02 + CRC
    assert data[:6].hex().upper() == "01060C210002", data.hex()
    # 计算得到的 CRC 应与发送字节一致
    assert data[-2] == crc16(data[:-2]) & 0xFF
    assert data[-1] == (crc16(data[:-2]) >> 8) & 0xFF


def test_read_response_read_ok():
    payload = bytes([0x01, 0x03, 0x0C]) + bytes(range(12))  # 12 字节数据(6寄存器)
    dev = make_device(with_crc(payload))
    resp = dev.read_response(expected_address=0x01, expected_function=0x03)
    assert len(resp) == 3 + 12 + 2
    assert resp[3] == 0x00  # 数据区从索引3开始
    assert resp[-2:] == with_crc(payload)[-2:]


def test_read_response_write_ok():
    # 0x06 写回显: 01 06 0C 21 00 02 + CRC（8字节）
    dev = make_device(with_crc(bytes([0x01, 0x06, 0x0C, 0x21, 0x00, 0x02])))
    resp = dev.read_response(expected_address=0x01, expected_function=0x06)
    assert len(resp) == 8, resp.hex()


def test_read_response_exception():
    # 异常响应: 01 83 02 + CRC（非法数据地址）
    dev = make_device(with_crc(bytes([0x01, 0x83, 0x02])))
    try:
        dev.read_response(expected_address=0x01)
        raise AssertionError("应抛出 ModbusException")
    except ModbusException as e:
        assert "非法数据地址" in str(e), str(e)


def test_read_response_bad_crc():
    dev = make_device(bytes([0x01, 0x03, 0x02, 0x00, 0x01, 0x00, 0x00]))
    try:
        dev.read_response()
        raise AssertionError("应抛出 ModbusException")
    except ModbusException as e:
        assert "CRC校验失败" in str(e), str(e)


def test_send_request_get_response_roundtrip():
    payload = bytes([0x01, 0x03, 0x02, 0x00, 0x01])  # 温度 = 1*0.01 = 0.01℃
    dev = make_device(with_crc(payload))
    f = ModbusRTU_Frame()
    f.AddressCode, f.FunctionCode = 0x01, 0x03
    f.StartingAddress_H, f.StartingAddress_L = 0x00, 0x00
    f.Quantity_H, f.Quantity_L = 0x00, 0x01
    resp = dev.send_request_get_response(f)
    assert resp[3:5] == bytes([0x00, 0x01])
    assert len(dev.serial_port.written) == 1
    assert dev.serial_port.written[0][:6].hex().upper() == "010300000001"


# ═══════════════════════════════════════════════════════════════
# 各驱动 read_all() 批量读解析
# ═══════════════════════════════════════════════════════════════
def make_air(response):
    from air_sensor import Modbus_Air_Sensor
    dev = Modbus_Air_Sensor.__new__(Modbus_Air_Sensor)
    dev.address = 0x01
    dev.serial_port = FakeSerial([response])
    dev.crc16_modbus = lib.crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    return dev


def make_soil(response):
    from soil_sensor import Modbus_Soil_Sensor
    dev = Modbus_Soil_Sensor.__new__(Modbus_Soil_Sensor)
    dev.address = 0x01
    dev.serial_port = FakeSerial([response])
    dev.crc16_modbus = lib.crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    return dev


def make_power(response):
    from power_sensor import PowerSensor
    dev = PowerSensor.__new__(PowerSensor)
    dev.address = 0x01
    dev.serial_port = FakeSerial([response])
    dev.crc16_modbus = lib.crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    return dev


def make_hub(responses):
    from sensor_hub import Modbus_Sensor_Hub
    dev = Modbus_Sensor_Hub.__new__(Modbus_Sensor_Hub)
    dev.serial_port = FakeSerial(responses)
    dev.crc16_modbus = lib.crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    return dev


def test_air_read_all():
    # 6 个 int16: 温度=25.00℃(2500), 湿度=55.00%(5500), 露点=10.00℃(1000),
    # 气压=1013.2hPa(10132), 海拔=120.0m(600, 0.2缩放), 密度=1.18(118)
    regs = [2500, 5500, 1000, 10132, 600, 118]
    data = b"".join(struct.pack(">h", r) for r in regs)
    payload = bytes([0x01, 0x03, 0x0C]) + data
    dev = make_air(with_crc(payload))
    v = dev.read_all()
    assert v["temperature"] == 25.0
    assert v["humidity"] == 55.0
    assert v["dewpoint"] == 10.0
    assert v["pressure"] == 1013.2
    assert v["altitude"] == 120.0
    assert v["air_density"] == 1.18


def test_air_read_all_negative():
    # 负温度: -5.00℃ → -500 → 0xFE0C
    data = struct.pack(">h", -500) + b"\x00" * 10
    payload = bytes([0x01, 0x03, 0x0C]) + data
    dev = make_air(with_crc(payload))
    assert dev.read_all()["temperature"] == -5.0


def test_soil_read_all():
    # 8 个寄存器: 温度=23.4℃(234, /10有符号), 湿度=45.6%(456, /10),
    # EC=1234, 盐分=567, 氮=88, 磷=99, 钾=100, PH=6.78(678, /100)
    regs = [234, 456, 1234, 567, 88, 99, 100, 678]
    data = b"".join(struct.pack(">H", r) for r in regs)
    payload = bytes([0x01, 0x03, 0x10]) + data
    dev = make_soil(with_crc(payload))
    v = dev.read_all()
    assert v["soil_temp"] == 23.4
    assert v["soil_moisture"] == 45.6
    assert v["soil_ec"] == 1234
    assert v["soil_salty"] == 567
    assert v["soil_nitro"] == 88
    assert v["soil_phosphorus"] == 99
    assert v["soil_potassium"] == 100
    assert v["soil_ph"] == 6.78


def test_power_read_all():
    # 4 个 int32: 电压=12.345V(12345), 电流=0.5A(500), 功率=6.0W(6000), 电量=80KWh(800000000×0.0001)
    raw = [12345, 500, 6000, 800000000]
    data = b"".join(struct.pack(">i", r) for r in raw)
    payload = bytes([0x01, 0x03, 0x10]) + data
    dev = make_power(with_crc(payload))
    v = dev.read_all()
    assert v["voltage"] == 12.345
    assert v["current"] == 0.5
    assert v["power"] == 6.0
    assert v["energy"] == 80000.0  # 0.0001Wh 缩放(实测校准)


def test_hub_address_map():
    from sensor_hub import GasSensor
    assert GasSensor("smoke_sensor").address == 0x02
    assert GasSensor("co2_sensor").address == 0x03
    assert GasSensor("ch4_sensor").address == 0x04  # 真机实测：0x04为甲烷
    assert GasSensor("o2_sensor").address == 0x05    # 真机实测：0x05为氧气


def test_hub_read_all():
    from sensor_hub import GasSensor
    # read_all 读取顺序: smoke(0x02) -> co2(0x03) -> o2(0x05) -> ch4(0x04)
    # 响应: smoke=5ppm, co2=600ppm, o2=20.0%VOL(200*0.1), ch4=1%LEL
    responses = []
    for addr, val in [(0x02, 5), (0x03, 600), (0x05, 200), (0x04, 1)]:
        payload = bytes([addr, 0x03, 0x02]) + struct.pack(">H", val)
        responses.append(with_crc(payload))
    dev = make_hub(responses)
    v = dev.read_all()
    assert v == {"smoke": 5, "co2": 600, "o2": 20.0, "ch4": 1}
    # 发送帧的地址应与实测映射一致
    sent = dev.serial_port.written
    assert [s[0] for s in sent] == [0x02, 0x03, 0x05, 0x04], [s.hex() for s in sent]


def test_vital_signs_packet():
    from heart_rate_sensor import VitalSignsPacket
    fmt = VitalSignsPacket.PACKET_FORMAT
    # 构造 88 字节包: 帧头0xFF + 64波形 + 心率90 + 血氧98 + 微循环75
    # + rsv[8](疲劳20,保留,保留,收缩120,舒张80,心输出5,外周阻力1500,RR变异性40)
    # + sdnn 30 + rmssd 25 + nn50 12 + pnn50 35 + rra 6字节 + rsv2 2字节
    rsv = bytes([20, 0, 0, 120, 80, 5, 1500 % 256, 40])
    pkt_bytes = struct.pack(
        fmt, 0xFF,
        *([0] * 64),   # acdata
        90, 98, 75,    # heart_rate, spo2, bk
        rsv,           # 8s
        30, 25, 12, 35,  # sdnn rmssd nn50 pnn50
        *([1] * 6),    # rra
        *([0] * 2),    # rsv2
    )
    pkt = VitalSignsPacket(pkt_bytes)
    assert pkt.start_byte == 0xFF
    assert pkt.heart_rate == 90
    assert pkt.spo2 == 98
    assert pkt.bk == 75
    assert pkt.fatigue_index == 20
    assert pkt.systolic_pressure == 120
    assert pkt.diastolic_pressure == 80
    assert pkt.cardiac_output == 5
    assert pkt.peripheral_resistance == 1500 % 256
    assert pkt.rr_variability == 40
    assert pkt.sdnn == 30
    assert pkt.rmssd == 25
    assert pkt.nn50 == 12
    assert pkt.pnn50 == 35
    assert len(pkt.acdata) == 64
    assert len(pkt.rra) == 6


def test_sensor_acq_channels():
    """sensor_acq 通道元数据：折线19 + 通用卡片5 + 生命体征卡片11 = 35 路"""
    import sensor_acq
    all_keys = (set(sensor_acq.LINE_CHANNELS)
                | set(sensor_acq.CARD_CHANNELS)
                | set(sensor_acq.VITAL_CARD_CHANNELS))
    assert len(sensor_acq.LINE_CHANNELS) == 19, len(sensor_acq.LINE_CHANNELS)
    assert len(sensor_acq.CARD_CHANNELS) == 5, len(sensor_acq.CARD_CHANNELS)
    assert len(sensor_acq.VITAL_CARD_CHANNELS) == 11, len(sensor_acq.VITAL_CARD_CHANNELS)
    assert len(all_keys) == 35, len(all_keys)
    expected = {
        "smoke", "co2", "o2", "ch4",
        "temperature", "humidity", "dewpoint", "pressure", "altitude", "air_density",
        "voltage", "current", "power", "energy",
        "soil_temp", "soil_moisture", "soil_ec", "soil_salty",
        "soil_nitro", "soil_phosphorus", "soil_potassium", "soil_ph",
        "heart_rate", "spo2", "bk", "fatigue_index",
        "systolic_pressure", "diastolic_pressure",
        "cardiac_output", "peripheral_resistance", "rr_variability",
        "sdnn", "rmssd", "nn50", "pnn50",
    }
    assert all_keys == expected
    # 折线布局恰好 19 路，无遗漏无重复
    placed = [k for _, _, k in sensor_acq.LINE_PLACEMENT]
    assert len(placed) == 19
    assert set(placed) == set(sensor_acq.LINE_CHANNELS)
    # 卡片行与卡片通道一致
    assert set(sensor_acq.CARD_KEYS) == set(sensor_acq.CARD_CHANNELS)
    # 生命体征 13 = 折线(心率/血氧) + 卡片11
    vital_line = set(sensor_acq.LINE_CHANNELS) & {"heart_rate", "spo2"}
    assert vital_line == {"heart_rate", "spo2"}
    assert set(sensor_acq.VITAL_FIELDS) == vital_line | set(sensor_acq.VITAL_CARD_CHANNELS)
    # 海拔与氮磷钾确实在卡片而非折线
    assert "altitude" not in sensor_acq.LINE_CHANNELS
    assert {"soil_nitro", "soil_phosphorus", "soil_potassium"} <= set(sensor_acq.CARD_CHANNELS)
    # 生命体征其余参数不在本地折线中（仅web卡片）
    assert set(sensor_acq.VITAL_CARD_CHANNELS).isdisjoint(sensor_acq.LINE_CHANNELS)
    # 固定Y量程只针对折线通道，且取值合法
    assert set(sensor_acq.Y_RANGES) <= set(sensor_acq.LINE_CHANNELS)
    for v in sensor_acq.Y_RANGES.values():
        assert v[0] < v[1], v


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [OK] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
    total = len(tests)
    print(f"\n{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
