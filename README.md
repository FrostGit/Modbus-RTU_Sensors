# Modbus-RTU 传感器数据采集

基于 Modbus RTU 协议的 485 总线传感器数据采集与实时可视化项目。包含多类传感器驱动（空气、电能、土壤、心率、气体传感器 HUB 等）以及基于 matplotlib 的实时绘图程序。

## 文件说明

| 文件 | 说明 |
|------|------|
| `lib_ModbusRTUDevice.py` | Modbus RTU 通信基础库：帧封装/解析、CRC 校验、异常处理 |
| `air_sensor.py` / `air_sensor_plt.py` / `air_sensor_record.py` | 空气传感器驱动 / 实时绘图 / 数据记录 |
| `power_sensor.py` / `power_sensor_plt.py` | 电能传感器驱动 / 实时绘图 |
| `soil_sensor.py` / `soil_sensor_plt.py` | 土壤传感器驱动 / 实时绘图 |
| `heart_rate_sensor.py` | 心率传感器驱动 |
| `sensor_hub.py` / `sensor_hub_plt.py` | 气体传感器 HUB 驱动 / 实时绘图 |
| `big_plt_demo.py` | 多传感器综合绘图 demo |
| `demo.py` | 基础示例 |
| `99-sensor-devices.rules` | udev 规则，将 USB 串口设备固定为符号链接 |
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

## 运行环境

- Python 3.8+（开发目标板：RDK X3）
- 依赖：`pyserial`、`numpy`、`matplotlib`、`Pillow`、`crcmod`

```bash
pip install pyserial numpy matplotlib pillow crcmod
```

## 使用

```bash
# 多传感器综合绘图
python3 big_plt_demo.py

# 单个传感器绘图 demo
python3 air_sensor_plt.py
python3 power_sensor_plt.py
python3 soil_sensor_plt.py
python3 sensor_hub_plt.py

# 空气传感器数据记录
python3 air_sensor_record.py
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
- 本目录为从 RDK X3（`~/DataGraber_ws/Sensors/485GasSensors`）备份的工作副本，包含尚未提交到远端的新增 `*_plt.py` 文件
