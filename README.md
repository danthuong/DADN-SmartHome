# UPDATE nhánh: demo api_server.py
1) Mở terminal đường dẫn đến api_server.py, gõ **uvicorn api_server:app --reload**
2) Lên trình duyệt test local trước ví dụ **127.0.0.1:8000/docs**
3) Test từng cái để xem log trên terminal và check database xem dữ liệu có được update ko
# Thông tin chi tiết từng route của api xem file **api_server.py**
Ngoài ra bản cập nhật nhánh lần này chia như sau:
```text
    + logger_service.py: chức năng để lắng nghe các feed trên cloud Adafruit.io ghi nhận vào database
    + mqtt_client.py: chức năng để khởi tạo giao thức mqtt kết nối giữa cloud với database với con yolo bit
    + run_face_id: để chạy module face_id
    + run_human_detect: để chạy module human_detect
    + run_motion_detect: để chạy cái motion_detect
```
### File main.py tạm thời có thể bỏ đi, hoặc ta có thể đổi tên logger_service thành main cũng dc, nhưng ngữ cảnh demo cho thầy xem thì khả năng ta chạy 4 máy riêng biệt (3 máy module + 1 máy listen và ghi chép log vào db) nên ko nhất thiết có 1 file main :))

