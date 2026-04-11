import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
import pickle
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
MODELS_DIR = os.path.join(ROOT_DIR, 'models')

CSV_PATH = os.path.join(MODELS_DIR, 'hand_gestures.csv')
MODEL_SAVE_PATH = os.path.join(MODELS_DIR, 'gesture_model.pkl')

# --- 1. Đọc dữ liệu ---
if not os.path.exists(CSV_PATH):
    print(f"Không tìm thấy file {CSV_PATH}")
    exit()

df = pd.read_csv(CSV_PATH)
X = df.drop('label', axis=1) 
y = df['label']              

# --- 2. Mã hóa nhãn (Chuyển chữ thành số) ---
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# --- 3. Chia tập dữ liệu ---
# Lưu ý: truyền y_encoded vào đây thay vì y
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

# --- 4. Huấn luyện mô hình XGBoost ---
print("Đang huấn luyện mô hình XGBoost...")
model = XGBClassifier(
    n_estimators=200, 
    max_depth=6, 
    learning_rate=0.1,
    objective='multi:softprob', 
    random_state=42,
    tree_method='gpu_hist' # Bỏ comment nếu máy có card NVIDIA và đã cài đặt hỗ trợ
)

# Bây giờ y_train chính là các nhãn đã được mã hóa số
model.fit(X_train, y_train)

# --- 5. Kiểm tra độ chính xác ---
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Độ chính xác đạt được: {acc * 100:.2f}%")

# --- 6. Xuất mô hình VÀ bộ giải mã nhãn ---
# Chúng ta lưu dưới dạng tuple (model, label_encoder)
with open(MODEL_SAVE_PATH, 'wb') as f:
    pickle.dump((model, label_encoder), f)

print(f"Đã lưu 'bộ não' và 'bộ giải mã' vào: {MODEL_SAVE_PATH}")