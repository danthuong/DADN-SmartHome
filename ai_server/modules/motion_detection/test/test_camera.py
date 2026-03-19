import cv2

def test():
    # Thử các index 0, 1, 2 nếu 0 không hoạt động
    index = 0 
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"Không thể mở camera ở index {index}")
        return

    print(f"Mở thành công camera {index}. Bấm 'q' để đóng.")
    while True:
        ret, frame = cap.read()
        if not ret: break
        cv2.imshow("Test Cam", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test()