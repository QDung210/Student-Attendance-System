from fastapi import FastAPI, WebSocket, HTTPException, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
import hashlib
import base64
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio
import uvicorn
import os
import shutil
import subprocess
import pandas as pd
from pathlib import Path

app = FastAPI(title="Face Recognition Attendance API")

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Serve frontend files
@app.get("/")
async def read_root():
    return FileResponse("../frontend/login.html")

@app.get("/dashboard.html")
async def dashboard():
    return FileResponse("../frontend/dashboard.html")

@app.get("/add-students.html")
async def add_students():
    return FileResponse("../frontend/add-students.html")

@app.get("/dashboard.js")
async def dashboard_js():
    return FileResponse("../frontend/dashboard.js")

@app.get("/add-students.js")
async def add_students_js():
    return FileResponse("../frontend/add-students.js")

@app.get("/dashboard.css")
async def dashboard_css():
    return FileResponse("../frontend/dashboard.css")

# Serve CSS files
@app.get("/globals.css")
async def globals_css():
    return FileResponse("../frontend/globals.css")

@app.get("/styleguide.css")
async def styleguide_css():
    return FileResponse("../frontend/styleguide.css")

@app.get("/style.css")
async def style_css():
    return FileResponse("../frontend/style.css")

# Serve JS files
@app.get("/script.js")
async def script_js():
    return FileResponse("../frontend/script.js")

# Serve image files
@app.get("/logo.png")
async def logo_png():
    return FileResponse("../frontend/logo.png")

@app.get("/icon.png")
async def icon_png():
    return FileResponse("../frontend/icon.png")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
active_connections: List[WebSocket] = []

async def connect_websocket(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

def disconnect_websocket(websocket: WebSocket):
    if websocket in active_connections:
        active_connections.remove(websocket)

async def send_personal_message(message: str, websocket: WebSocket):
    await websocket.send_text(message)

async def broadcast_message(message: str):
    for connection in active_connections[:]:  # Copy list to avoid modification during iteration
        try:
            await connection.send_text(message)
        except:
            # Remove dead connections
            active_connections.remove(connection)

# Database functions
def get_db():
    conn = sqlite3.connect("students.db")
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def blob_to_base64(blob_data) -> str:
    """Convert BLOB to base64 string"""
    if blob_data:
        return base64.b64encode(blob_data).decode('utf-8')
    return ""

# Request/Response functions
def create_login_response(success: bool, message: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Tạo response cho login"""
    response = {"success": success, "message": message}
    if token:
        response["token"] = token
    return response

def create_student_attendance(student_id: str, name: str, class_name: str, major: str, avatar_base64: str, attendance_time: str, checkin_face_base64: str = "") -> Dict[str, Any]:
    """Tạo object StudentAttendance"""
    return {
        "student_id": student_id,
        "name": name,
        "class_name": class_name,
        "major": major,
        "avatar_base64": avatar_base64,
        "attendance_time": attendance_time,
        "checkin_face_base64": checkin_face_base64
    }

def create_today_checkins_response(success: bool, data: List[Dict[str, Any]], total: int) -> Dict[str, Any]:
    """Tạo response cho today checkins"""
    return {
        "success": success,
        "data": data,
        "total": total
    }

# API Routes
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """API đăng nhập cho giáo viên"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Kiểm tra thông tin đăng nhập - có thể là username hoặc email
        cursor.execute(
            "SELECT username, password_hash, full_name FROM teacher WHERE username = ? OR username LIKE ?",
            (username, f"%{username}%")
        )
        teacher = cursor.fetchone()
        
        if not teacher:
            return create_login_response(False, "Tài khoản không tồn tại")
        
        if not verify_password(password, teacher["password_hash"]):
            return create_login_response(False, "Sai mật khẩu")
        
        # Tạo token đơn giản (trong thực tế nên dùng JWT)
        token = base64.b64encode(f"{username}:{datetime.now().isoformat()}".encode()).decode()
        
        return create_login_response(True, f"Đăng nhập thành công! Xin chào {teacher['full_name']}", token)
        
    except Exception as e:
        return create_login_response(False, f"Lỗi: {str(e)}")
    finally:
        conn.close()

@app.get("/today-checkins")
async def get_today_checkins():
    """API lấy danh sách sinh viên đã điểm danh hôm nay"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Lấy ngày hôm nay
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Truy vấn sinh viên đã điểm danh hôm nay
        cursor.execute("""
            SELECT student_id, name, class, major, avatar, attendance_time, checkin_face
            FROM students 
            WHERE attendance_time IS NOT NULL 
            AND DATE(attendance_time) = ?
            ORDER BY attendance_time DESC
        """, (today,))
        
        students = cursor.fetchall()
        
        # Chuyển đổi dữ liệu
        attendance_list = []
        for student in students:
            attendance_list.append(create_student_attendance(
                student["student_id"],
                student["name"],
                student["class"],
                student["major"],
                blob_to_base64(student["avatar"]),
                student["attendance_time"],
                blob_to_base64(student["checkin_face"]) if student["checkin_face"] else ""
            ))
        
        return create_today_checkins_response(
            True,
            attendance_list,
            len(attendance_list)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")
    finally:
        conn.close()

@app.websocket("/ws/attendance")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint để push thông tin điểm danh real-time"""
    await connect_websocket(websocket)
    try:
        while True:
            # Giữ kết nối sống
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        disconnect_websocket(websocket)

@app.post("/notify-attendance")
async def notify_attendance(student_id: str, attendance_time: str):
    """API để hệ thống nhận diện gửi thông tin điểm danh mới"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Lấy thông tin sinh viên
        cursor.execute("""
            SELECT student_id, name, class, major, avatar, attendance_time, checkin_face
            FROM students 
            WHERE student_id = ?
        """, (student_id,))
        
        student = cursor.fetchone()
        
        if not student:
            raise HTTPException(status_code=404, detail="Sinh viên không tồn tại")
        
        # Tạo thông tin để gửi qua WebSocket
        attendance_data = {
            "student_id": student["student_id"],
            "name": student["name"],
            "class_name": student["class"],
            "major": student["major"],
            "avatar_base64": blob_to_base64(student["avatar"]),
            "attendance_time": attendance_time,
            "checkin_face_base64": blob_to_base64(student["checkin_face"]) if student["checkin_face"] else "",
            "timestamp": datetime.now().isoformat()
        }
        
        # Gửi thông tin qua WebSocket
        await broadcast_message(json.dumps(attendance_data))
        
        return {"success": True, "message": "Đã gửi thông tin điểm danh"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")
    finally:
        conn.close()

# Upload Excel file endpoint
@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file Excel (.xlsx, .xls)")
        
        # Save uploaded file
        excel_path = "students.xlsx"
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate Excel content
        try:
            df = pd.read_excel(excel_path)
            required_columns = ['student_id', 'name', 'class', 'major']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise HTTPException(status_code=400, detail=f"File Excel thiếu các cột: {', '.join(missing_columns)}")
            
            student_count = len(df)
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không thể đọc file Excel: {str(e)}")
        
        return {
            "success": True, 
            "message": "Upload file Excel thành công",
            "student_count": student_count,
            "file_path": excel_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi upload file Excel: {str(e)}")

# Upload images folder endpoint
@app.post("/api/upload-images")
async def upload_images(files: List[UploadFile] = File(...)):
    try:
        # Create avatars directory if not exists
        avatars_dir = Path("../avatars")
        avatars_dir.mkdir(exist_ok=True)
        
        uploaded_students = set()
        total_files = 0
        
        for file in files:
            if file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Extract student ID from filename pattern
                # Expected pattern: images_StudentID_index_originalname
                filename_parts = file.filename.split('_')
                if len(filename_parts) >= 3 and filename_parts[0] == 'images':
                    student_id = filename_parts[1]
                    original_filename = '_'.join(filename_parts[3:])  # Get original filename
                    
                    # Create student folder
                    student_dir = avatars_dir / student_id
                    student_dir.mkdir(exist_ok=True)
                    
                    # Save image with original filename
                    image_path = student_dir / original_filename
                    with open(image_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    uploaded_students.add(student_id)
                    total_files += 1
        
        return {
            "success": True,
            "message": "Upload folder ảnh thành công",
            "students_count": len(uploaded_students),
            "total_files": total_files,
            "uploaded_students": list(uploaded_students)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi upload folder ảnh: {str(e)}")

# Process data endpoint
@app.post("/api/process-data")
async def process_data():
    try:
        # Import and run the data processing function
        from data import process_face_data
        
        success = process_face_data()
        
        if not success:
            raise HTTPException(status_code=500, detail="Xử lý dữ liệu thất bại")
        
        return {
            "success": True,
            "message": "Xử lý dữ liệu thành công"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý dữ liệu: {str(e)}")

# Update database endpoint
@app.post("/api/update-database")
async def update_database():
    try:
        # Import and run the database update function
        from database import update_database as update_db
        
        success = update_db()
        
        if not success:
            raise HTTPException(status_code=500, detail="Cập nhật database thất bại")
        
        return {
            "success": True,
            "message": "Cập nhật database thành công"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật database: {str(e)}")

# Download sample Excel file
@app.get("/sample-excel")
async def download_sample_excel():
    """Download file Excel mẫu"""
    sample_file = "students_sample.xlsx"
    if os.path.exists(sample_file):
        return FileResponse(sample_file, filename="students_sample.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        raise HTTPException(status_code=404, detail="File mẫu không tồn tại")

if __name__ == "__main__":
    print("🚀 Starting Face Recognition Attendance API...")
    print("📋 Available endpoints:")
    print("   - POST /login - Đăng nhập giáo viên")
    print("   - GET /today-checkins - Danh sách điểm danh hôm nay")
    print("   - WS /ws/attendance - WebSocket real-time")
    print("   - POST /notify-attendance - Thông báo điểm danh mới")
    print("   - POST /api/upload-excel - Upload file Excel sinh viên")
    print("   - POST /api/upload-images - Upload folder ảnh sinh viên")
    print("   - POST /api/process-data - Xử lý dữ liệu từ file Excel và ảnh")
    print("   - POST /api/update-database - Cập nhật database từ dữ liệu đã xử lý")
    print("   - GET /sample-excel - Tải file Excel mẫu")
    print("🌐 Server running on: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
