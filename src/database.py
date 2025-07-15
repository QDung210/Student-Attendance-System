import sqlite3
import pandas as pd
import os
from glob import glob
import hashlib

# Kết nối đến SQLite
conn = sqlite3.connect("students.db")
cursor = conn.cursor()

# Tạo bảng students nếu chưa có
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT,
    class TEXT,
    major TEXT,
    avatar BLOB,
    attendance_time TEXT,
    checkin_face BLOB
)
""")

# Tạo bảng teacher nếu chưa có
cursor.execute("""
CREATE TABLE IF NOT EXISTS teacher (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT
)
""")

# Thêm cột attendance_time nếu chưa có
try:
    cursor.execute("ALTER TABLE students ADD COLUMN attendance_time TEXT")
    print("✅ Đã thêm cột attendance_time")
except sqlite3.OperationalError:
    print("ℹ️ Cột attendance_time đã tồn tại")

# Thêm cột checkin_face nếu chưa có
try:
    cursor.execute("ALTER TABLE students ADD COLUMN checkin_face BLOB")
    print("✅ Đã thêm cột checkin_face")
except sqlite3.OperationalError:
    print("ℹ️ Cột checkin_face đã tồn tại")

conn.commit()

# Đọc file Excel
df = pd.read_excel("students.xlsx")

for _, row in df.iterrows():
    student_id = row["student_id"]
    name = row["name"]
    class_ = row["class"]
    major = row["major"]

    # Tìm ảnh đầu tiên trong thư mục student_id/
    folder_path = os.path.join("avatars", student_id)  # ví dụ: avatars/HE123456/
    image_files = glob(os.path.join(folder_path, "*.*"))  # tìm mọi loại ảnh

    if not image_files:
        print(f"[!] Không tìm thấy ảnh cho {student_id}, bỏ qua...")
        continue

    image_path = image_files[0]
    with open(image_path, "rb") as f:
        avatar_blob = f.read()

    # Lưu vào SQLite
    cursor.execute("""
        INSERT OR REPLACE INTO students (student_id, name, class, major, avatar, attendance_time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, name, class_, major, avatar_blob, None))

# Thêm tài khoản giáo viên mẫu
def hash_password(password):
    """Mã hóa mật khẩu bằng SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

# Thêm tài khoản giáo viên mẫu
teachers = [
    ("admin", "admin123", "Quản trị viên"),
    ("teacher1", "teacher123", "Nguyễn Văn A"),
    ("teacher2", "teacher456", "Trần Thị B")
]

for username, password, full_name in teachers:
    password_hash = hash_password(password)
    cursor.execute("""
        INSERT OR REPLACE INTO teacher (username, password_hash, full_name)
        VALUES (?, ?, ?)
    """, (username, password_hash, full_name))

print("✅ Đã thêm tài khoản giáo viên mẫu")
conn.commit()
conn.close()
print("✅ Import hoàn tất.")
