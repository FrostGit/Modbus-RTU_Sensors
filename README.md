# Modbus-RTU 传感器数据采集

基于 Modbus RTU 协议的 485 总线传感器数据采集与实时可视化项目。包含多类传感器驱动（空气、电能、土壤、心率/生命体征、气体传感器 HUB 等）以及基于 matplotlib 的实时绘图程序（离线采集 + 可视化展示）。

## 目录结构

```
DataCollector/
├── drivers/    # 传感器驱动（lib_ModbusRTUDevice, air, soil, power, sensor_hub, heart_rate）
├── core/       # sensor_acq.py 采集公共模块
├── apps/       # 可视化/记录/演示入口（big_plt_qt, big_plt_demo, web_dashboard, heart_wave_plt, 各*_plt, record, demo）
├── web/        # Flask 远程监看前端
├── tests/      # 回归测试（假串口，无需硬件）
├── docs/       # make_usage_html.py（README → 使用说明.html 生成器）
├── assets/     # 字体与图片资源（STSONG.TTF / logo.jpg / title.png）
├── udev/       # 99-sensor-devices.rules
├── desktop/    # 桌面快捷方式模板（big_plt_qt.desktop / 使用说明.desktop）
├── README.md   # 本文档（唯一说明来源）
└── 使用说明.html  # README 渲染版（docs/make_usage_html.py 生成，X3 桌面打开用）
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `drivers/lib_ModbusRTUDevice.py` | Modbus RTU 通信基础库：帧封装/解析、CRC16 校验、异常处理、读写响应解析（crcmod 缺失时自动注入纯 Python 实现） |
| `drivers/air_sensor.py` 等 6 个驱动 | 气象 / 电能 / 土壤 / 心率生命体征 / 气体 HUB 驱动（各驱动可独立自测：`python3 drivers/air_sensor.py`） |
| `core/sensor_acq.py` | 采集公共模块（批量读、通道元数据，big_plt 与 web 共用） |
| `apps/big_plt_qt.py` | 多传感器综合大屏（**pyqtgraph 实时版，X3 本地显示推荐**：19 折线 + 5 卡片，每帧 <50ms） |
| `apps/big_plt_demo.py` | 多传感器综合大屏（matplotlib 版，适合 PC 端） |
| `apps/web_dashboard.py` / `web/` | 远程监看服务（Flask + Web：19 折线 + 16 卡片 + 脉搏波 + RR 散点） |
| `apps/heart_wave_plt.py` | 生命体征波形快速显示（脉搏波滚动 + RR 间期散点） |
| `apps/air_sensor_record.py` | 气象 CSV 离线记录 |
| `apps/*_plt.py` / `apps/demo.py` | 单传感器绘图 / 单传感器读取示例 |
| `udev/99-sensor-devices.rules` | udev 规则，将 USB 串口设备固定为符号链接 |
| `tests/test_sensor_lib.py` | 回归测试（假串口，无需真实硬件） |
| `desktop/*.desktop` | X3 桌面快捷方式模板（大屏 / 使用说明） |
| `assets/` | 绘图界面资源（背景图、标题图、中文字体） |

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
- 依赖：`pyserial`、`numpy`、`matplotlib`、`Pillow`；`crcmod` 可选（缺失时自动使用内置纯 Python CRC16 实现）；`web_dashboard.py` 另需 `flask`；`big_plt_qt.py` 另需 `pyqt5` + `pyqtgraph`

```bash
pip install pyserial numpy matplotlib pillow crcmod
```

## 使用

```bash
cd ~/DataGraber_ws/Sensors/485GasSensors

# X3 本地实时大屏（pyqtgraph，推荐；也可双击桌面「多模态传感器大屏」图标）
# 注意: PyPI 无 aarch64 预编译 wheel，PyQt5 必须用 apt 装，勿用 pip(会卡在源码编译)
sudo apt install -y python3-pyqt5 python3-pyqtgraph   # Debian 系(X3)
# 若 apt 无 python3-pyqtgraph: python3 -m pip install --user pyqtgraph (纯Python不编译)
python3 apps/big_plt_qt.py --skip-frames 2

# 多传感器大屏（matplotlib 版，PC 端用）
python3 apps/big_plt_demo.py --draw-every 2

# 生命体征波形快速显示（脉搏波 + RR 散点）
python3 apps/heart_wave_plt.py

# 远程监看（Flask + Web，浏览器打开 http://<主机IP>:5000/）
pip install flask   # 首次需要
python3 apps/web_dashboard.py
python3 apps/web_dashboard.py --port 8080

# 单个传感器绘图 demo
python3 apps/air_sensor_plt.py
python3 apps/power_sensor_plt.py
python3 apps/soil_sensor_plt.py
python3 apps/sensor_hub_plt.py

# 气象传感器离线记录（CSV 落盘 + 实时绘图，Ctrl+C 停止）
python3 apps/air_sensor_record.py                 # 默认每 1 秒采一次
python3 apps/air_sensor_record.py --interval 2    # 每 2 秒采一次
python3 apps/air_sensor_record.py --out /tmp/air.csv

# 单传感器读取示例
python3 apps/demo.py --sensor_type air_sensor
python3 apps/demo.py --sensor_type heart_rate_sensor

# 驱动独立自测（无需应用层）
python3 drivers/air_sensor.py
python3 drivers/sensor_hub.py

# 回归测试（无需硬件）
python3 tests/test_sensor_lib.py
```

udev 规则部署（root）：

```bash
sudo cp udev/99-sensor-devices.rules /etc/udev/rules.d/
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
