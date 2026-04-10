import os
import time
from Adafruit_IO import MQTTClient
from dotenv import load_dotenv

load_dotenv()

AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

client = None

def connect_mqtt():
    global client
    if client is None:
        client = MQTTClient(AIO_USERNAME, AIO_KEY)
        try:
            client.connect()
            print("[MQTT] Kết nối logger thành công!")
        except Exception as e:
            print(f"[MQTT_ERROR] Kết nối thất bại: {e}")
            client = None

FEED_MAP = {
    "One": "fan-speed-1",
    "Two": "fan-speed-1",
    "Three": "fan-speed-1",
    "Victory": "tracking-toggle",
    "Clapping": "device-led",
    "Shaking": "oscillation-toggle",
    "Close palm": "device-fan"
}

# Giá trị đặc biệt cho fan-speed
FAN_SPEED_VALUES = {
    "One": 1,
    "Two": 2,
    "Three": 3
}

def send_mqtt_command(command):
    print(f"\033[92m[IOT COMMAND] >>> GỬI LỆNH: {command}\033[0m")
    
    feed_id = FEED_MAP.get(command)
    if feed_id is None:
        print(f"[WARNING] Không tìm thấy feed cho lệnh: {command}")
        return
    
    # Lấy giá trị đặc biệt cho fan-speed
    value = FAN_SPEED_VALUES.get(command, 1)
    
    global client
    if client is None:
        connect_mqtt()
    
    if client is not None:
        try:
            client.publish(feed_id, value)
            print(f"[MQTT] Đã gửi '{command}' -> feed '{feed_id}' với giá trị {value}")
        except Exception as e:
            print(f"[MQTT_ERROR] Gửi lệnh thất bại: {e}")
            try:
                client.connect()
                client.publish(feed_id, value)
            except Exception as e2:
                print(f"[MQTT_ERROR] Kết nối lại thất bại: {e2}")
                client = None


if __name__ == "__main__":
    connect_mqtt()
    time.sleep(2)
    send_mqtt_command("One")
    send_mqtt_command("Clapping")
