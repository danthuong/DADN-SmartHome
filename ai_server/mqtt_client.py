import sys
from Adafruit_IO import MQTTClient

# Cấu hình khóa truy cập đến ADAFRUIT
AIO_USERNAME = "thinhphan2313306"
AIO_KEY = "aio_VWuR71QDMpqjdnUvo65mq4sZKtmI"

class SmartHomeMQTT:
    def __init__(self):
        self.client = MQTTClient(AIO_USERNAME, AIO_KEY)
        # Gắn hàm mặc định để báo lỗi nếu rớt mạng
        self.client.on_disconnect = self.default_disconnected
        self.client.on_connect = self.default_connected

    def default_connected(self, client):
        print("[MQTT] Đã kết nối thành công tới Adafruit IO!")

    def default_disconnected(self, client):
        print("[MQTT] Cảnh báo: Đã ngắt kết nối với Adafruit IO!")
        sys.exit(1)

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