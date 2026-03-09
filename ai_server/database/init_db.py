import sqlite3

def init_db():
    # Tạo kết nối (Nó sẽ tự tạo file smart_home.db nếu chưa có)
    conn = sqlite3.connect('smart_home.db')
    cursor = conn.cursor()

    # Script tạo bảng
    script = """
    CREATE TABLE IF NOT EXISTS sensors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unit TEXT
    );

    CREATE TABLE IF NOT EXISTS sensor_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_id INTEGER,
        value REAL NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sensor_id) REFERENCES sensors(id)
    );

    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS device_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER,
        status INTEGER CHECK (status IN (0, 1)),
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (device_id) REFERENCES devices(id)
    );

    INSERT OR IGNORE INTO sensors (id, name, unit) VALUES (1, 'AI_CAM', '0/1'), (2, 'PIR', '0/1'), (3, 'TEMP', 'C'), (4, 'LIGHT', 'Lux');
    INSERT OR IGNORE INTO devices (id, name) VALUES (1, 'FAN'), (2, 'LED');
    """
    
    cursor.executescript(script)
    conn.commit()
    conn.close()
    print("Đã khởi tạo Database thành công!")

if __name__ == "__main__":
    init_db()