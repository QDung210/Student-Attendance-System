import sqlite3
import pandas as pd
import os
from glob import glob
import hashlib
import sys

def update_database():
    try:
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

        # Kiểm tra file Excel
        excel_file = "students.xlsx"
        if not os.path.exists(excel_file):
            print(f"❌ Không tìm thấy file Excel: {excel_file}")
            return False

        # Đọc file Excel
        df = pd.read_excel(excel_file)
        print(f"📊 Đã đọc {len(df)} sinh viên từ file Excel")

        processed_count = 0
        for _, row in df.iterrows():
            student_id = row["student_id"]
            name = row["name"]
            class_ = row["class"]
            major = row["major"]

            # Tìm ảnh đầu tiên trong thư mục student_id/
            folder_path = os.path.join("..", "avatars", student_id)
            image_files = glob(os.path.join(folder_path, "*.*"))

            if not image_files:
                print(f"⚠️ Không tìm thấy ảnh cho {student_id}, bỏ qua...")
                continue

            # Lấy ảnh đầu tiên
            image_path = image_files[0]
            try:
                with open(image_path, "rb") as f:
                    avatar_blob = f.read()
            except Exception as e:
                print(f"❌ Lỗi đọc ảnh {image_path}: {str(e)}")
                continue

            # Lưu vào SQLite
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO students (student_id, name, class, major, avatar, attendance_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, name, class_, major, avatar_blob, None))
                processed_count += 1
                print(f"✅ Đã thêm sinh viên: {student_id} - {name}")
            except Exception as e:
                print(f"❌ Lỗi thêm sinh viên {student_id}: {str(e)}")

        # Thêm tài khoản giáo viên mẫu
        def hash_password(password):
            """Mã hóa mật khẩu bằng SHA-256"""
            return hashlib.sha256(password.encode()).hexdigest()

        teachers = [
            ("admin@school.com", "admin123", "Quản trị viên"),
            ("teacher1@school.com", "teacher123", "Nguyễn Văn A"),
            ("teacher2@school.com", "teacher456", "Trần Thị B"),
            ("admin", "admin123", "Quản trị viên"),
            ("teacher1", "teacher123", "Nguyễn Văn A")
        ]

        for username, password, full_name in teachers:
            password_hash = hash_password(password)
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO teacher (username, password_hash, full_name)
                    VALUES (?, ?, ?)
                """, (username, password_hash, full_name))
            except Exception as e:
                print(f"❌ Lỗi thêm giáo viên {username}: {str(e)}")

        print("✅ Đã thêm tài khoản giáo viên mẫu")
        conn.commit()
        conn.close()
        
        print(f"🎉 Hoàn tất! Đã xử lý {processed_count}/{len(df)} sinh viên.")
        return True

    except Exception as e:
        print(f"❌ Lỗi cập nhật database: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_database()
    sys.exit(0 if success else 1)