from dotenv import load_dotenv
import os
import requests
import logging
import time

# ==============================
# CONFIG LOGGING
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/adafruit_data.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ==============================
# LOAD ENV
# ==============================
load_dotenv()

AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

if not AIO_USERNAME or not AIO_KEY:
    logging.error("Thiếu AIO_USERNAME hoặc AIO_KEY trong .env")
    exit(1)

headers = {
    "X-AIO-Key": AIO_KEY
}

BASE_URL = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}"

# ==============================
# HÀM GỌI API AN TOÀN
# ==============================
def safe_get(url):
    try:
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            logging.error(f"API lỗi {res.status_code}: {res.text}")
            return None

        return res.json()

    except Exception as e:
        logging.error(f"Lỗi request: {e}")
        return None

# ==============================
# MAIN
# ==============================
def main():
    logging.info("=== BẮT ĐẦU LẤY DỮ LIỆU ADAFRUIT IO ===")

    # 1. Lấy danh sách feeds
    feeds_url = f"{BASE_URL}/feeds"
    feeds = safe_get(feeds_url)

    if not feeds:
        logging.error("Không lấy được danh sách feeds")
        return

    logging.info(f"Tổng số feeds: {len(feeds)}")

    # 2. Lấy data từng feed
    for feed in feeds:
        key = feed.get("key")
        if not key:
            continue

        logging.info(f"\n=== Feed: {key} ===")

        data_url = f"{BASE_URL}/feeds/{key}/data?limit=1000"
        data = safe_get(data_url)

        if data is None:
            continue

        logging.info(f"Số bản ghi: {len(data)}")

        # log 5 dòng đầu cho gọn
        for record in data[:5]:
            logging.info(record)

        # tránh bị rate limit
        time.sleep(1)

    logging.info("=== HOÀN THÀNH ===")


if __name__ == "__main__":
    main()