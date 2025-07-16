import sqlite3
import pandas as pd
import os
from glob import glob
import hashlib
import sys

def update_database():
    try:
        # Connect to SQLite
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        # Create students table if not exists
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

        # Create teacher table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT
        )
        """)

        # Add attendance_time column if not exists
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN attendance_time TEXT")
            print("✅ Added attendance_time column")
        except sqlite3.OperationalError:
            print("ℹ️ attendance_time column already exists")

        # Add checkin_face column if not exists
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN checkin_face BLOB")
            print("✅ Added checkin_face column")
        except sqlite3.OperationalError:
            print("ℹ️ checkin_face column already exists")

        conn.commit()

        # Check Excel file
        excel_file = "students.xlsx"
        if not os.path.exists(excel_file):
            print(f"❌ Excel file not found: {excel_file}")
            return False

        # Read Excel file
        df = pd.read_excel(excel_file)
        print(f"📊 Read {len(df)} students from Excel file")

        processed_count = 0
        for _, row in df.iterrows():
            student_id = row["student_id"]
            name = row["name"]
            class_ = row["class"]
            major = row["major"]

            # Find first image in student_id/ folder
            folder_path = os.path.join("..", "avatars", student_id)
            image_files = glob(os.path.join(folder_path, "*.*"))

            if not image_files:
                print(f"⚠️ No image found for {student_id}, skipping...")
                continue

            # Get first image
            image_path = image_files[0]
            try:
                with open(image_path, "rb") as f:
                    avatar_blob = f.read()
            except Exception as e:
                print(f"❌ Error reading image {image_path}: {str(e)}")
                continue

            # Save to SQLite
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO students (student_id, name, class, major, avatar, attendance_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, name, class_, major, avatar_blob, None))
                processed_count += 1
                print(f"✅ Added student: {student_id} - {name}")
            except Exception as e:
                print(f"❌ Error adding student {student_id}: {str(e)}")

        # Add sample teacher accounts
        def hash_password(password):
            """Encrypt password using SHA-256"""
            return hashlib.sha256(password.encode()).hexdigest()

        teachers = [
            ("admin@school.com", "admin123", "Administrator"),
            ("teacher1@school.com", "teacher123", "Nguyen Van A"),
            ("teacher2@school.com", "teacher456", "Tran Thi B"),
            ("admin", "admin123", "Administrator"),
            ("teacher1", "teacher123", "Nguyen Van A")
        ]

        for username, password, full_name in teachers:
            password_hash = hash_password(password)
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO teacher (username, password_hash, full_name)
                    VALUES (?, ?, ?)
                """, (username, password_hash, full_name))
            except Exception as e:
                print(f"❌ Error adding teacher {username}: {str(e)}")

        print("✅ Added sample teacher accounts")
        conn.commit()
        conn.close()
        
        print(f"🎉 Completed! Processed {processed_count}/{len(df)} students.")
        return True

    except Exception as e:
        print(f"❌ Error updating database: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_database()
    sys.exit(0 if success else 1)