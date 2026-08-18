import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from air_sensor import Modbus_Air_Sensor
import time
from lib_ModbusRTUDevice import ModbusException
import serial
from PIL import Image

my_font = font_manager.FontProperties(fname="./STSONG.TTF")

plt.ion()

# 初始化数据列表
x_data = []
# 天气类传感器数据
air_temperature_data = []
air_humidity_data = []
dewPoint_data = []
airPressure_data = []
altitude_data = []
airDensity_data = []

# 创建子图
fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle('多模态数据采集平台-天气类传感器数据', fontsize=16, fontproperties=my_font)

# 第一行第5、6个：空气温度和湿度 (0,4) - (0,5)
air_temperature_line, = axes[0, 0].plot([], [], 'r-', linewidth=2)
axes[0, 0].set_title('空气温度', fontproperties=my_font)
# axes[0, 4].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 0].set_ylabel('℃', fontproperties=my_font)
axes[0, 0].grid(True, alpha=0.3)

air_humidity_line, = axes[0, 1].plot([], [], 'g-', linewidth=2)
axes[0, 1].set_title('空气湿度', fontproperties=my_font)
# axes[0, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 1].set_ylabel('%', fontproperties=my_font)
axes[0, 1].grid(True, alpha=0.3)

dewPoint_line, = axes[0, 2].plot([], [], 'b-', linewidth=2)
axes[0, 2].set_title('露点温度', fontproperties=my_font)
# axes[1, 0].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 2].set_ylabel('℃', fontproperties=my_font)
axes[0, 2].grid(True, alpha=0.3)

airPressure_line, = axes[1, 0].plot([], [], 'y-', linewidth=2)
axes[1, 0].set_title('大气压力', fontproperties=my_font)
# axes[1, 1].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 0].set_ylabel('hPa', fontproperties=my_font)
axes[1, 0].grid(True, alpha=0.3)

altitude_line, = axes[1, 1].plot([], [], 'c-', linewidth=2)
axes[1, 1].set_title('海拔高度', fontproperties=my_font)
# axes[1, 2].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 1].set_ylabel('m', fontproperties=my_font)
axes[1, 1].grid(True, alpha=0.3)

airDensity_line, = axes[1, 2].plot([], [], 'm-', linewidth=2)
axes[1, 2].set_title('空气密度', fontproperties=my_font)
# axes[1, 3].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 2].set_ylabel('Kg/m³', fontproperties=my_font)
axes[1, 2].grid(True, alpha=0.3)


# 调整子图间距
plt.tight_layout(rect=[0, 0, 1, 0.96])

# 模拟数据获取和更新
x = 0
while True:
    start_time = time.time()

    try:
        x_data.append(x)

        # 获取空气传感器数据
        air_temperature = Modbus_Air_Sensor(serial_port="/dev/weather_sensor").read_temperature()
        air_temperature_data.append(air_temperature)
        air_temperature_line.set_data(x_data, air_temperature_data)

        air_humidity = Modbus_Air_Sensor(serial_port="/dev/weather_sensor").read_humidity()
        air_humidity_data.append(air_humidity)
        air_humidity_line.set_data(x_data, air_humidity_data)

        dewPoint_value = Modbus_Air_Sensor(serial_port="/dev/weather_sensor").read_dewPoint()
        dewPoint_data.append(dewPoint_value)
        dewPoint_line.set_data(x_data, dewPoint_data)

        airPressure_value = Modbus_Air_Sensor(serial_port="/dev/weather_sensor").read_airPressure()
        airPressure_data.append(airPressure_value)
        airPressure_line.set_data(x_data, airPressure_data)

        altitude_value = Modbus_Air_Sensor(serial_port="/dev/weather_sensor").read_altitude()
        altitude_data.append(altitude_value)
        altitude_line.set_data(x_data, altitude_data)

        airDensity_value = Modbus_Air_Sensor(serial_port="/dev/weather_sensor").read_airDensity()
        airDensity_data.append(airDensity_value)
        airDensity_line.set_data(x_data, airDensity_data)

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