import sys
from Adafruit_IO import MQTTClient

def connected(client):
    print("[MQTT] Success connected ...")
    # client.subscribe("ten-feed-nhan-lenh") # Bỏ comment dòng này nếu cần nhận lệnh

def subscribe(client, userdata, mid, granted_qos):
    print("[MQTT] Subcribe thanh cong ... ")

def disconnected(client):
    print("[MQTT] Disconneting ... ")
    sys.exit(1)

def message(client, feed_id, payload):
    print(f"[MQTT] Nhan du lieu tu {feed_id}: {payload}")

def setup_mqtt(username, key):
    """
    Hàm khởi tạo và kết nối MQTT theo chuẩn giáo trình.
    Trả về đối tượng 'client' để main.py sử dụng.
    """
    client = MQTTClient(username, key)
    client.on_connect = connected
    client.on_disconnect = disconnected
    client.on_message = message
    client.on_subscribe = subscribe
    
    try:
        client.connect()
        client.loop_background()
        return client
    except Exception as e:
        print(f"[LỖI MQTT] Khong the ket noi: {e}")
        sys.exit(1)