from fastapi import FastAPI, WebSocket, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import hashlib
import base64
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio
import uvicorn

app = FastAPI(title="Face Recognition Attendance API")

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
        # Kiểm tra thông tin đăng nhập
        cursor.execute(
            "SELECT username, password_hash, full_name FROM teacher WHERE username = ?",
            (username,)
        )
        teacher = cursor.fetchone()
        
        if not teacher:
            return create_login_response(False, "Tài khoản không tồn tại")
        
        if not verify_password(password, teacher["password_hash"]):
            return create_login_response(False, "Sai mật khẩu")
        
        # Tạo token đơn giản (trong thực tế nên dùng JWT)
        token = base64.b64encode(f"{username}:{datetime.now().isoformat()}".encode()).decode()
        
        return create_login_response(
            True,
            f"Đăng nhập thành công! Xin chào {teacher['full_name']}",
            token
        )
        
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

@app.get("/")
async def root():
    """API test"""
    return {
        "message": "Face Recognition Attendance API",
        "version": "1.0.0",
        "endpoints": {
            "login": "POST /login",
            "today_checkins": "GET /today-checkins", 
            "websocket": "WS /ws/attendance",
            "notify": "POST /notify-attendance"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Face Recognition Attendance API...")
    print("📋 Available endpoints:")
    print("   - POST /login - Đăng nhập giáo viên")
    print("   - GET /today-checkins - Danh sách điểm danh hôm nay")
    print("   - WS /ws/attendance - WebSocket real-time")
    print("   - POST /notify-attendance - Thông báo điểm danh mới")
    print("🌐 Server running on: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
