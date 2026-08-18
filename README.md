# Modbus-RTU 传感器数据采集

基于 Modbus RTU 协议的 485 总线传感器数据采集与实时可视化项目。包含多类传感器驱动（空气、电能、土壤、心率/生命体征、气体传感器 HUB 等）以及基于 matplotlib 的实时绘图程序（离线采集 + 可视化展示）。

## 文件说明

| 文件 | 说明 |
|------|------|
| `lib_ModbusRTUDevice.py` | Modbus RTU 通信基础库：帧封装/解析、CRC16 校验、异常处理、读写响应解析（crcmod 缺失时自动注入纯 Python 实现） |
| `air_sensor.py` / `air_sensor_plt.py` / `air_sensor_record.py` | 空气（气象）传感器驱动 / 实时绘图 / **CSV 离线记录** |
| `power_sensor.py` / `power_sensor_plt.py` | 电能传感器驱动 / 实时绘图 |
| `soil_sensor.py` / `soil_sensor_plt.py` | 土壤传感器驱动 / 实时绘图 |
| `heart_rate_sensor.py` | 生命体征传感器驱动（88 字节协议包解析、帧同步，含 HRV/血压等指标） |
| `sensor_hub.py` / `sensor_hub_plt.py` | 气体传感器 HUB 驱动 / 实时绘图 |
| `big_plt_demo.py` | 多传感器综合大屏（5×8 大表格，35 路曲线，含生命体征面板） |
| `demo.py` | 单传感器读取示例 |
| `99-sensor-devices.rules` | udev 规则，将 USB 串口设备固定为符号链接 |
| `tests/test_sensor_lib.py` | 回归测试（假串口，无需真实硬件） |
| `logo.jpg` / `title.png` / `STSONG.TTF` | 绘图界面资源（背景图、标题图、中文字体） |

## 传感器与串口设备映射

| 设备 | 串口 | udev 符号链接 |
|------|------|---------------|
| power_sensor（电能） | ttyACM0 | `/dev/power_sensor` |
| so100-main | ttyACM1 | - |
| so100-sub | ttyACM2 | - |
| gas_hub（气体 HUB） | ttyUSB0 | `/dev/gas_hub` |
| vital_signs（生命体征） | ttyUSB1 | `/dev/vital_signs` |
| soil_sensor（土壤） | ttyUSB2 | `/dev/soil_sensor` |
| hr_band（心率） | ttyUSB3 | `/dev/hr_band` |
| weather_sensor（气象） | ttyUSB4 | `/dev/weather_sensor` |

udev 规则按 `idVendor`/`idProduct`/`devpath`/`serial` 多层匹配，将 CH340（1a86:7523/55d4）、CP210x（10c4:ea60）等 USB 转串口设备固定为稳定设备名，避免拔插后 tty 编号漂移。

## 驱动设计要点

- **批量读**：气象 6 / 土壤 8 / 电源 8 寄存器各自连续，`read_all()` 一次 Modbus 往返读回（全量一轮从 22 次往返降到 4 次，约 0.4s）
- **对象复用**：驱动实例化一次、全程复用，不再每读一次 new+close 串口
- **写操作**：`set_*`/`clear_*` 等写寄存器方法使用 0x06 功能码与 Value 字段，基础库正确解析写回显
- **容错**：绘图脚本每轮只追加一次时间戳，单传感器失败记 `None`（曲线断口），列表不产生错位
- **时间轴**：横轴为相对时间（秒），环形缓冲保留最近 300~600 个采样点，内存有上限

## 运行环境

- Python 3.8+（开发目标板：RDK X3）
- 依赖：`pyserial`、`numpy`、`matplotlib`、`Pillow`；`crcmod` 可选（缺失时自动使用内置纯 Python CRC16 实现）

```bash
pip install pyserial numpy matplotlib pillow crcmod
```

## 使用

```bash
# 多传感器综合大屏（大表格展示，含生命体征面板）
python3 big_plt_demo.py

# 单个传感器绘图 demo
python3 air_sensor_plt.py
python3 power_sensor_plt.py
python3 soil_sensor_plt.py
python3 sensor_hub_plt.py

# 气象传感器离线记录（CSV 落盘 + 实时绘图，Ctrl+C 停止）
python3 air_sensor_record.py                 # 默认每 1 秒采一次
python3 air_sensor_record.py --interval 2    # 每 2 秒采一次
python3 air_sensor_record.py --out /tmp/air.csv

# 单传感器读取示例
python3 demo.py --sensor_type air_sensor
python3 demo.py --sensor_type heart_rate_sensor

# 回归测试（无需硬件）
python3 tests/test_sensor_lib.py
```

udev 规则部署（root）：

```bash
sudo cp 99-sensor-devices.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

访问串口需要 `dialout` 组权限：

```bash
sudo usermod -aG dialout $USER
```

## Git 说明

- 仓库：`git@github.com:FrostGit/Modbus-RTU_Sensors.git`
- 分支：`master` / `devel` / `dev-HeartRateSonsor`
- 本目录为从 RDK X3（`~/DataGraber_ws/Sensors/485GasSensors`）备份的工作副本；驱动库全部在本工作区内自包含，与 DataLabelApp 设备端（同机部署）的驱动保持同步维护
