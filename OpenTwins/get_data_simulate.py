import paho.mqtt.client as mqtt
import random
import time
import json

# --------------------
# 请根据实际情况修改以下参数：
# --------------------
namespace = "example"
car_name = "car_1"  # 你创建的孪生对象名称
wheels_prefix = "car_1:wheel_"

# MQTT 连接信息（根据实际地址修改）
broker = "192.168.49.2"  # 或者你的 Mosquitto 外部 IP
port = 30511           # 默认端口或你用 NodePort 映射的端口
username = "ditto"    # 如果开启了认证，填用户名
password = "ditto"    # Ditto 默认安装时用户名/密码均为 ditto

topic_prefix = "opentwins/"  # Ditto 的默认 MQTT topic 前缀

# --------------------
# MQTT 客户端设置
# --------------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ 成功连接到 MQTT Broker")
    else:
        print(f"❌ 连接失败，返回码 {rc}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.username_pw_set(username, password)
client.connect(broker, port, 60)
client.loop_start()

# --------------------
# 模拟数据生成函数
# --------------------
def generate_wheel_data():
    velocity = round(random.uniform(0, 100), 2)      # km/h
    direction = round(random.uniform(-45, 45), 2)    # degrees
    return velocity, direction


def generate_gps_data():
    latitude = round(random.uniform(-90.0, 90.0), 6)
    longitude = round(random.uniform(-180.0, 180.0), 6)
    return latitude, longitude


# --------------------
# 构建 Ditto 协议格式的消息
# --------------------
def get_ditto_msg(thing_name, feature_payload):
    return {
        "topic": f"{namespace}/{thing_name}/things/twin/commands/merge",
        "headers": {
            "content-type": "application/merge-patch+json"
        },
        "path": "/features",
        "value": feature_payload,
        "extra": {
            "thingId": f"{namespace}:{thing_name}",
            "attributes": {
                "_parents": [f"{namespace}:{car_name}"]
            }
        }
    }


def get_car_feature_payload(ts, lat, lon):
    return {
        "gps": {
            "properties": {
                "value": {
                    "latitude": lat,
                    "longitude": lon,
                    "time": ts
                }
            }
        }
    }


def get_wheel_feature_payload(ts, velocity, direction):
    return {
        "velocity": {
            "properties": {
                "value": velocity,
                "time": ts
            }
        },
        "direction": {
            "properties": {
                "value": direction,
                "time": ts
            }
        }
    }


# --------------------
# 主循环：每 5 秒发送一次数据
# --------------------
try:
    while True:
        timestamp = int(time.time() * 1000)  # 当前时间戳（毫秒）

        # 发送汽车 GPS 数据
        lat, lon = generate_gps_data()
        car_payload = get_car_feature_payload(timestamp, lat, lon)
        car_msg = get_ditto_msg(car_name, car_payload)
        car_topic = topic_prefix + namespace + "/" + car_name
        client.publish(car_topic, json.dumps(car_msg))
        print(f"🚗 GPS 发送成功 → {lat}, {lon}")

        # 发送 4 个轮子的速度和方向数据
        for i in range(1, 5):
            wheel_name = f"{wheels_prefix}{i}"
            vel, dir = generate_wheel_data()
            wheel_payload = get_wheel_feature_payload(timestamp, vel, dir)
            wheel_msg = get_ditto_msg(wheel_name, wheel_payload)
            wheel_topic = topic_prefix + namespace + "/" + wheel_name
            client.publish(wheel_topic, json.dumps(wheel_msg))
            print(f"🛞 {wheel_name} 数据发送：velocity={vel} km/h, direction={dir}°")

        print("-" * 50)
        time.sleep(5)

except KeyboardInterrupt:
    print("⏹️ 停止发送数据")
    client.disconnect()
    client.loop_stop()
