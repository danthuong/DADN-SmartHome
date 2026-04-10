import requests
import os
from dotenv import load_dotenv

load_dotenv()

AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

BASE_URL = "https://io.adafruit.com/api/v2"

def get_feeds():
    url = f"{BASE_URL}/{AIO_USERNAME}/feeds"
    headers = {"X-AIO-Key": AIO_KEY}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else []

def delete_feed(feed_key):
    url = f"{BASE_URL}/{AIO_USERNAME}/feeds/{feed_key}"
    headers = {"X-AIO-Key": AIO_KEY}
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"✅ Đã xóa feed: {feed_key}")
        return True
    else:
        print(f"❌ Lỗi xóa feed '{feed_key}': {response.status_code}")
        return False

def create_feed(feed_key, feed_name):
    url = f"{BASE_URL}/{AIO_USERNAME}/feeds"
    headers = {"X-AIO-Key": AIO_KEY, "Content-Type": "application/json"}
    data = {"feed": {"key": feed_key, "name": feed_name}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        print(f"✅ Tạo thành công feed: {feed_key}")
        return True
    elif response.status_code == 422:
        print(f"⚠️ Feed '{feed_key}' đã tồn tại, bỏ qua")
        return True
    else:
        print(f"❌ Lỗi tạo feed '{feed_key}': {response.status_code} - {response.text}")
        return False

def main():
    print("=== Bước 1: Xóa các feeds không dùng ===\n")
    
    feeds_to_delete = ["env-temp", "setting-temp"]
    for feed_key in feeds_to_delete:
        delete_feed(feed_key)
    
    print("\n=== Bước 2: Tạo các feeds mới ===\n")
    
    feeds_to_create = [
        ("tracking-toggle", "Tracking Toggle"),
        ("oscillation-toggle", "Oscillation Toggle")
    ]
    
    for feed_key, feed_name in feeds_to_create:
        create_feed(feed_key, feed_name)
    
    print("\n=== Danh sách feeds hiện tại ===")
    feeds = get_feeds()
    print(f"Tổng số feeds: {len(feeds)}")
    for feed in feeds:
        print(f"  - {feed['key']}")

if __name__ == "__main__":
    main()
