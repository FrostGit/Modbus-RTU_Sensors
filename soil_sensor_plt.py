import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from soil_sensor import Modbus_Soil_Sensor
import time
from lib_ModbusRTUDevice import ModbusException
import serial
from PIL import Image

my_font = font_manager.FontProperties(fname="./STSONG.TTF")

plt.ion()

# 初始化数据列表
x_data = []
# 土壤类传感器数据
soil_temperature_data = []
soil_humi_data = []
soil_EC_data = []
soil_salty_data = []
soil_nitro_data = []
soil_phosphorus_data = []
soil_potassium_data = []
soil_PH_data = []

# 创建子图
fig, axes = plt.subplots(2, 4, figsize=(20, 12))
fig.suptitle('多模态数据采集平台-土壤类传感器数据', fontsize=16, fontproperties=my_font)

soil_humi_line, = axes[0, 0].plot([], [], 'r-', linewidth=2)
axes[0, 0].set_title('土壤湿度', fontproperties=my_font)
# axes[1, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 0].set_ylabel('%', fontproperties=my_font)
axes[0, 0].grid(True, alpha=0.3)

# 第三行：土壤其他传感器 (2,0) - (2,5)
soil_EC_line, = axes[0, 1].plot([], [], 'g-', linewidth=2)
axes[0, 1].set_title('土壤电导率', fontproperties=my_font)
# axes[2, 0].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 1].set_ylabel('µS/cm', fontproperties=my_font)
axes[0, 1].grid(True, alpha=0.3)

soil_salty_line, = axes[0, 2].plot([], [], 'b-', linewidth=2)
axes[0, 2].set_title('土壤盐分', fontproperties=my_font)
# axes[2, 1].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 2].set_ylabel('mg/L', fontproperties=my_font)
axes[0, 2].grid(True, alpha=0.3)

soil_nitro_line, = axes[0, 3].plot([], [], 'y-', linewidth=2)
axes[0, 3].set_title('土壤氮含量', fontproperties=my_font)
# axes[2, 2].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 3].set_ylabel('mg/kg', fontproperties=my_font)
axes[0, 3].grid(True, alpha=0.3)

soil_phosphorus_line, = axes[1, 0].plot([], [], 'r-', linewidth=2)
axes[1, 0].set_title('土壤磷含量', fontproperties=my_font)
# axes[2, 3].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 0].set_ylabel('mg/kg', fontproperties=my_font)
axes[1, 0].grid(True, alpha=0.3)

soil_potassium_line, = axes[1, 1].plot([], [], 'g-', linewidth=2)
axes[1, 1].set_title('土壤钾含量', fontproperties=my_font)
# axes[2, 4].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 1].set_ylabel('mg/kg', fontproperties=my_font)
axes[1, 1].grid(True, alpha=0.3)

soil_PH_line, = axes[1, 2].plot([], [], 'b-', linewidth=2)
axes[1, 2].set_title('土壤PH值', fontproperties=my_font)
# axes[2, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 2].set_ylabel('pH', fontproperties=my_font)
axes[1, 2].grid(True, alpha=0.3)

soil_temperature_line, = axes[1, 3].plot([], [], 'y-', linewidth=2)
axes[1, 3].set_title('土壤温度', fontproperties=my_font)
# axes[1, 4].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 3].set_ylabel('℃', fontproperties=my_font)
axes[1, 3].grid(True, alpha=0.3)

# 调整子图间距
plt.tight_layout(rect=[0, 0, 1, 0.96])

# 模拟数据获取和更新
x = 0
while True:
    start_time = time.time()

    try:
        x_data.append(x)

        # 获取土壤传感器数据
        soil_temperature = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_temperature()
        soil_temperature_data.append(soil_temperature)
        soil_temperature_line.set_data(x_data, soil_temperature_data)
        time.sleep(0.12)

        soil_humi = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_humi()
        soil_humi_data.append(soil_humi)
        soil_humi_line.set_data(x_data, soil_humi_data)
        time.sleep(0.12)

        soil_EC = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_EC()
        soil_EC_data.append(soil_EC)
        soil_EC_line.set_data(x_data, soil_EC_data)
        time.sleep(0.12)

        soil_salty = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_salty()
        soil_salty_data.append(soil_salty)
        soil_salty_line.set_data(x_data, soil_salty_data)
        time.sleep(0.12)

        soil_nitro = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_nitro()
        soil_nitro_data.append(soil_nitro)
        soil_nitro_line.set_data(x_data, soil_nitro_data)
        time.sleep(0.12)

        soil_phosphorus = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_phosphorus()
        soil_phosphorus_data.append(soil_phosphorus)
        soil_phosphorus_line.set_data(x_data, soil_phosphorus_data)
        time.sleep(0.12)

        soil_potassium = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_potassium()
        soil_potassium_data.append(soil_potassium)
        soil_potassium_line.set_data(x_data, soil_potassium_data)
        time.sleep(0.12)

        soil_PH = Modbus_Soil_Sensor(serial_port="/dev/soil_sensor").read_PH()
        soil_PH_data.append(soil_PH)
        soil_PH_line.set_data(x_data, soil_PH_data)
        time.sleep(0.12)

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