import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from power_sensor import PowerSensor
import time
from lib_ModbusRTUDevice import ModbusException
import serial
from PIL import Image

my_font = font_manager.FontProperties(fname="./STSONG.TTF")

plt.ion()

# 初始化数据列表
x_data = []
# 电源类传感器数据
voltage_data = []
power_data = []
current_data = []
energy_data = []

# 创建子图
fig, axes = plt.subplots(2, 2, figsize=(20, 12))
fig.suptitle('多模态数据采集平台-电源类传感器数据', fontsize=16, fontproperties=my_font)

voltage_line, = axes[0, 0].plot([], [], 'r-', linewidth=2)
axes[0, 0].set_title('电压', fontproperties=my_font)
# axes[0, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 0].set_ylabel('V', fontproperties=my_font)
axes[0, 0].grid(True, alpha=0.3)

power_line, = axes[0, 1].plot([], [], 'g-', linewidth=2)
axes[0, 1].set_title('功率', fontproperties=my_font)
# axes[0, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 1].set_ylabel('W', fontproperties=my_font)
axes[0, 1].grid(True, alpha=0.3)

current_line, = axes[1, 0].plot([], [], 'b-', linewidth=2)
axes[1, 0].set_title('电流', fontproperties=my_font)
# axes[1, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 0].set_ylabel('A', fontproperties=my_font)
axes[1, 0].grid(True, alpha=0.3)

energy_line, = axes[1, 1].plot([], [], 'y-', linewidth=2)
axes[1, 1].set_title('电量', fontproperties=my_font)
# axes[1, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 1].set_ylabel('wh', fontproperties=my_font)
axes[1, 1].grid(True, alpha=0.3)

# 调整子图间距
plt.tight_layout(rect=[0, 0, 1, 0.96])

# 模拟数据获取和更新
x = 0
while True:
    start_time = time.time()

    try:
        x_data.append(x)

        voltage = PowerSensor("/dev/power_sensor", baudrate=9600, timeout=1).read_voltage()
        voltage_data.append(voltage)
        voltage_line.set_data(x_data, voltage_data)

        current = PowerSensor("/dev/power_sensor", baudrate=9600, timeout=1).read_current()
        current_data.append(current)
        current_line.set_data(x_data, current_data)

        power = PowerSensor("/dev/power_sensor", baudrate=9600, timeout=1).read_power()
        power_data.append(power)
        power_line.set_data(x_data, power_data)

        energy = PowerSensor("/dev/power_sensor", baudrate=9600, timeout=1).read_energy()
        energy_data.append(energy)
        energy_line.set_data(x_data, energy_data)

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