import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from sensor_hub import Modbus_Sensor_Hub
import time
from lib_ModbusRTUDevice import ModbusException
import serial
from PIL import Image

my_font = font_manager.FontProperties(fname="./STSONG.TTF")

plt.ion()

# 初始化数据列表
x_data = []
# 气体类传感器数据
smoke_concentration_data = []
co2_concentration_data = []
o2_concentration_data = []
ch4_concentration_data = []

# 创建子图
fig, axes = plt.subplots(2, 2, figsize=(20, 12))
fig.suptitle('多模态数据采集平台-气体类传感器数据', fontsize=16, fontproperties=my_font)

smoke_concentration_line, = axes[0, 0].plot([], [], 'r-', linewidth=2)
axes[0, 0].set_title('烟雾传感器', fontproperties=my_font)
# axes[0, 0].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 0].set_ylabel('ppm', fontproperties=my_font)
axes[0, 0].grid(True, alpha=0.3)

co2_concentration_line, = axes[0, 1].plot([], [], 'g-', linewidth=2)
axes[0, 1].set_title('二氧化碳传感器', fontproperties=my_font)
# axes[0, 1].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 1].set_ylabel('ppm', fontproperties=my_font)
axes[0, 1].grid(True, alpha=0.3)

o2_concentration_line, = axes[1, 0].plot([], [], 'b-', linewidth=2)
axes[1, 0].set_title('氧气传感器', fontproperties=my_font)
# axes[0, 2].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 0].set_ylabel('%VOL', fontproperties=my_font)
axes[1, 0].grid(True, alpha=0.3)

ch4_concentration_line, = axes[1, 1].plot([], [], 'y-', linewidth=2)
axes[1, 1].set_title('甲烷传感器', fontproperties=my_font)
# axes[0, 3].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 1].set_ylabel('%LEL', fontproperties=my_font)
axes[1, 1].grid(True, alpha=0.3)

# 调整子图间距
plt.tight_layout(rect=[0, 0, 1, 0.96])

# 模拟数据获取和更新
x = 0
while True:
    start_time = time.time()

    try:
        x_data.append(x)

        # 获取气体传感器数据
        smoke_concentration = Modbus_Sensor_Hub(serial_port="/dev/gas_hub").read_smokeGasConcentration()
        smoke_concentration_data.append(smoke_concentration)
        smoke_concentration_line.set_data(x_data, smoke_concentration_data)

        co2_concentration = Modbus_Sensor_Hub(serial_port="/dev/gas_hub").read_co2GasConcentration()
        co2_concentration_data.append(co2_concentration)
        co2_concentration_line.set_data(x_data, co2_concentration_data)

        o2_concentration = Modbus_Sensor_Hub(serial_port="/dev/gas_hub").read_o2GasConcentration()
        o2_concentration_data.append(o2_concentration)
        o2_concentration_line.set_data(x_data, o2_concentration_data)

        ch4_concentration = Modbus_Sensor_Hub(serial_port="/dev/gas_hub").read_ch4GasConcentration()
        ch4_concentration_data.append(ch4_concentration)
        ch4_concentration_line.set_data(x_data, ch4_concentration_data)

        # 调整每个子图的坐标轴范围
        for ax in axes.flat:
            ax.relim()  # 重新计算数据范围
            ax.autoscale_view()  # 自动调整视图范围

        # 重绘图表
        fig.canvas.draw()
        fig.canvas.flush_events()

        x = x + 1
        print(time.time() - start_time)

    except ModbusException as e:
        print(f"Modbus Exception: {e}")
        time.sleep(1)  # 出错时等待1秒再重试
    except Exception as e:
        print(f"其他异常: {e}")
        time.sleep(1)

# 保持图表显示（实际上不会执行到这里，因为上面是无限循环）
plt.ioff()
plt.show()