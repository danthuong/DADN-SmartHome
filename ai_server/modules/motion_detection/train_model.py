import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle

# 1. Đọc dữ liệu từ file CSV bạn vừa tạo
df = pd.read_csv('hand_gestures.csv')
X = df.drop('label', axis=1) # Các cột tọa độ
y = df['label']              # Cột nhãn

# 2. Chia tập dữ liệu để kiểm tra độ chính xác
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Huấn luyện mô hình
model = RandomForestClassifier(n_estimators=100, random_state=42)
print("Đang huấn luyện mô hình...")
model.fit(X_train, y_train)

# 4. Kiểm tra xem mô hình thông minh đến mức nào
y_pred = model.predict(X_test)
print(f"Độ chính xác đạt được: {accuracy_score(y_test, y_pred) * 100:.2f}%")

# 5. Xuất mô hình ra file để sử dụng cho App Smart Home
with open('gesture_model.pkl', 'wb') as f:
    pickle.dump(model, f)
print("Đã lưu bộ não vào file: gesture_model.pkl")