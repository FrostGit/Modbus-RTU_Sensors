import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from sensor_hub import Modbus_Sensor_Hub
from air_sensor import Modbus_Air_Sensor
from soil_sensor import Modbus_Soil_Sensor
from power_sensor import PowerSensor
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
# 天气类传感器数据
air_temperature_data = []
air_humidity_data = []
dewPoint_data = []
airPressure_data = []
altitude_data = []
airDensity_data = []
# 土壤类传感器数据
soil_temperature_data = []
soil_humi_data = []
soil_EC_data = []
soil_salty_data = []
soil_nitro_data = []
soil_phosphorus_data = []
soil_potassium_data = []
soil_PH_data = []
# 电源类传感器数据
voltage_data = []
power_data = []
current_data = []
energy_data = []

# 创建子图
fig, axes = plt.subplots(3, 8, figsize=(20, 12))
# fig.suptitle('多模态数据采集平台', fontsize=16, fontproperties=my_font)

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

o2_concentration_line, = axes[0, 2].plot([], [], 'b-', linewidth=2)
axes[0, 2].set_title('氧气传感器', fontproperties=my_font)
# axes[0, 2].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 2].set_ylabel('%VOL', fontproperties=my_font)
axes[0, 2].grid(True, alpha=0.3)

ch4_concentration_line, = axes[0, 3].plot([], [], 'y-', linewidth=2)
axes[0, 3].set_title('甲烷传感器', fontproperties=my_font)
# axes[0, 3].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 3].set_ylabel('%LEL', fontproperties=my_font)
axes[0, 3].grid(True, alpha=0.3)

# 第一行第5、6个：空气温度和湿度 (0,4) - (0,5)
air_temperature_line, = axes[0, 4].plot([], [], 'c-', linewidth=2)
axes[0, 4].set_title('空气温度', fontproperties=my_font)
# axes[0, 4].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 4].set_ylabel('℃', fontproperties=my_font)
axes[0, 4].grid(True, alpha=0.3)

air_humidity_line, = axes[0, 5].plot([], [], 'm-', linewidth=2)
axes[0, 5].set_title('空气湿度', fontproperties=my_font)
# axes[0, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 5].set_ylabel('%', fontproperties=my_font)
axes[0, 5].grid(True, alpha=0.3)

voltage_line, = axes[0, 6].plot([], [], 'k-', linewidth=2)
axes[0, 6].set_title('电压', fontproperties=my_font)
# axes[0, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 6].set_ylabel('V', fontproperties=my_font)
axes[0, 6].grid(True, alpha=0.3)

power_line, = axes[0, 7].plot([], [], 'r-', linewidth=2)
axes[0, 7].set_title('功率', fontproperties=my_font)
# axes[0, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[0, 7].set_ylabel('W', fontproperties=my_font)
axes[0, 7].grid(True, alpha=0.3)

dewPoint_line, = axes[1, 0].plot([], [], 'r-', linewidth=2)
axes[1, 0].set_title('露点温度', fontproperties=my_font)
# axes[1, 0].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 0].set_ylabel('℃', fontproperties=my_font)
axes[1, 0].grid(True, alpha=0.3)

airPressure_line, = axes[1, 1].plot([], [], 'g-', linewidth=2)
axes[1, 1].set_title('大气压力', fontproperties=my_font)
# axes[1, 1].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 1].set_ylabel('hPa', fontproperties=my_font)
axes[1, 1].grid(True, alpha=0.3)

altitude_line, = axes[1, 2].plot([], [], 'b-', linewidth=2)
axes[1, 2].set_title('海拔高度', fontproperties=my_font)
# axes[1, 2].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 2].set_ylabel('m', fontproperties=my_font)
axes[1, 2].grid(True, alpha=0.3)

axes[1,3].axis('off')
img = Image.open('logo.jpg')
img_array = np.array(img)
axes[1, 3].imshow(img_array)

axes[1,4].axis('off')
img = Image.open('title.png')
img_array = np.array(img)
axes[1, 4].imshow(img_array)

soil_humi_line, = axes[1, 5].plot([], [], 'm-', linewidth=2)
axes[1, 5].set_title('土壤湿度', fontproperties=my_font)
# axes[1, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 5].set_ylabel('%', fontproperties=my_font)
axes[1, 5].grid(True, alpha=0.3)

current_line, = axes[1, 6].plot([], [], 'k-', linewidth=2)
axes[1, 6].set_title('电流', fontproperties=my_font)
# axes[1, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 6].set_ylabel('A', fontproperties=my_font)
axes[1, 6].grid(True, alpha=0.3)

energy_line, = axes[1, 7].plot([], [], 'r-', linewidth=2)
axes[1, 7].set_title('电量', fontproperties=my_font)
# axes[1, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[1, 7].set_ylabel('wh', fontproperties=my_font)
axes[1, 7].grid(True, alpha=0.3)

# 第三行：土壤其他传感器 (2,0) - (2,5)
soil_EC_line, = axes[2, 0].plot([], [], 'r-', linewidth=2)
axes[2, 0].set_title('土壤电导率', fontproperties=my_font)
# axes[2, 0].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 0].set_ylabel('µS/cm', fontproperties=my_font)
axes[2, 0].grid(True, alpha=0.3)

soil_salty_line, = axes[2, 1].plot([], [], 'g-', linewidth=2)
axes[2, 1].set_title('土壤盐分', fontproperties=my_font)
# axes[2, 1].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 1].set_ylabel('mg/L', fontproperties=my_font)
axes[2, 1].grid(True, alpha=0.3)

soil_nitro_line, = axes[2, 2].plot([], [], 'b-', linewidth=2)
axes[2, 2].set_title('土壤氮含量', fontproperties=my_font)
# axes[2, 2].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 2].set_ylabel('mg/kg', fontproperties=my_font)
axes[2, 2].grid(True, alpha=0.3)

soil_phosphorus_line, = axes[2, 3].plot([], [], 'y-', linewidth=2)
axes[2, 3].set_title('土壤磷含量', fontproperties=my_font)
# axes[2, 3].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 3].set_ylabel('mg/kg', fontproperties=my_font)
axes[2, 3].grid(True, alpha=0.3)

soil_potassium_line, = axes[2, 4].plot([], [], 'c-', linewidth=2)
axes[2, 4].set_title('土壤钾含量', fontproperties=my_font)
# axes[2, 4].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 4].set_ylabel('mg/kg', fontproperties=my_font)
axes[2, 4].grid(True, alpha=0.3)

soil_PH_line, = axes[2, 5].plot([], [], 'm-', linewidth=2)
axes[2, 5].set_title('土壤PH值', fontproperties=my_font)
# axes[2, 5].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 5].set_ylabel('pH', fontproperties=my_font)
axes[2, 5].grid(True, alpha=0.3)

airDensity_line, = axes[2, 6].plot([], [], 'k-', linewidth=2)
axes[2, 6].set_title('空气密度', fontproperties=my_font)
# axes[1, 3].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 6].set_ylabel('Kg/m³', fontproperties=my_font)
axes[2, 6].grid(True, alpha=0.3)

soil_temperature_line, = axes[2, 7].plot([], [], 'r-', linewidth=2)
axes[2, 7].set_title('土壤温度', fontproperties=my_font)
# axes[1, 4].set_xlabel('采集次数', fontproperties=my_font)
axes[2, 7].set_ylabel('℃', fontproperties=my_font)
axes[2, 7].grid(True, alpha=0.3)

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