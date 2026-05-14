import sys
import os
from Adafruit_IO import MQTTClient
from dotenv import load_dotenv

# --- Bắt đầu patch lỗi của Adafruit_IO (không ném exception khi rớt mạng) ---
# Mặc định Adafruit_IO raise exception trên background thread làm chết luồng và ko tự reconnect
def custom_mqtt_disconnect(self, client, userdata, rc):
    self._connected = False
    if rc != 0:
        print(f"[MQTT] Ngắt kết nối không mong muốn từ Adafruit IO (mã lỗi rc={rc}).")
    else:
        print("[MQTT] Đã ngắt kết nối an toàn với Adafruit IO.")
        
    if self.on_disconnect is not None:
        self.on_disconnect(self)

MQTTClient._mqtt_disconnect = custom_mqtt_disconnect
# --- Kết thúc patch ---

load_dotenv()
# Cấu hình khóa truy cập đến ADAFRUIT- sau nayf se bo vao .env
AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

class SmartHomeMQTT:
    def __init__(self):
        self.client = MQTTClient(AIO_USERNAME, AIO_KEY)
        # Gắn hàm mặc định để báo lỗi nếu rớt mạng
        self.client.on_disconnect = self.default_disconnected
        self.client.on_connect = self.default_connected

    def default_connected(self, client):
        print("[MQTT] Đã kết nối thành công tới Adafruit IO!")

    def default_disconnected(self, client):
        print("[MQTT] Cảnh báo: Đã ngắt kết nối với Adafruit IO! (Sẽ tự động thử kết nối lại...)")
        # Không dùng sys.exit(1) ở đây để paho-mqtt có thể tự động reconnect

    # Hàm này dùng cho Logger (để nó tự nhét hàm lắng nghe riêng của nó vào)
    def setup_subscriber(self, custom_on_connect, custom_on_message):
        self.client.on_connect = custom_on_connect
        self.client.on_message = custom_on_message

    # Hàm khởi động
    def start(self):
        try:
            self.client.connect()
            self.client.loop_background()
        except Exception as e:
            print(f"[MQTT_ERROR] Không thể kết nối Adafruit: {e}")
            sys.exit(1)

    # Hàm gửi dữ liệu (Các file AI chỉ cần gọi hàm này là xong)
    def publish(self, feed_id, value):
        self.client.publish(feed_id, value)