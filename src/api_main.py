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
    """Create response for login"""
    response = {"success": success, "message": message}
    if token:
        response["token"] = token
    return response

def create_student_attendance(student_id: str, name: str, class_name: str, major: str, avatar_base64: str, attendance_time: str, checkin_face_base64: str = "") -> Dict[str, Any]:
    """Create StudentAttendance object"""
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
    """Create response for today checkins"""
    return {
        "success": success,
        "data": data,
        "total": total
    }

# API Routes
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Teacher login API"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Check login credentials - can be username or email
        cursor.execute(
            "SELECT username, password_hash, full_name FROM teacher WHERE username = ? OR username LIKE ?",
            (username, f"%{username}%")
        )
        teacher = cursor.fetchone()
        
        if not teacher:
            return create_login_response(False, "Account does not exist")
        
        if not verify_password(password, teacher["password_hash"]):
            return create_login_response(False, "Wrong password")
        
        # Create simple token (should use JWT in production)
        token = base64.b64encode(f"{username}:{datetime.now().isoformat()}".encode()).decode()
        
        return create_login_response(True, f"Login successful! Welcome {teacher['full_name']}", token)
        
    except Exception as e:
        return create_login_response(False, f"Error: {str(e)}")
    finally:
        conn.close()

@app.get("/today-checkins")
async def get_today_checkins():
    """API to get list of students who checked in today"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Query students who checked in today
        cursor.execute("""
            SELECT student_id, name, class, major, avatar, attendance_time, checkin_face
            FROM students 
            WHERE attendance_time IS NOT NULL 
            AND DATE(attendance_time) = ?
            ORDER BY attendance_time DESC
        """, (today,))
        
        students = cursor.fetchall()
        
        # Convert data
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
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()

@app.websocket("/ws/attendance")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint to push real-time attendance information"""
    await connect_websocket(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        disconnect_websocket(websocket)

@app.post("/notify-attendance")
async def notify_attendance(student_id: str, attendance_time: str):
    """API for recognition system to send new attendance information"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get student information
        cursor.execute("""
            SELECT student_id, name, class, major, avatar, attendance_time, checkin_face
            FROM students 
            WHERE student_id = ?
        """, (student_id,))
        
        student = cursor.fetchone()
        
        if not student:
            raise HTTPException(status_code=404, detail="Student does not exist")
        
        # Create information to send via WebSocket
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
        
        # Send information via WebSocket
        await broadcast_message(json.dumps(attendance_data))
        
        return {"success": True, "message": "Attendance information sent"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()

# Upload Excel file endpoint
@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted")
        
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
                raise HTTPException(status_code=400, detail=f"Excel file missing columns: {', '.join(missing_columns)}")
            
            student_count = len(df)
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unable to read Excel file: {str(e)}")
        
        return {
            "success": True, 
            "message": "Excel file uploaded successfully",
            "student_count": student_count,
            "file_path": excel_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading Excel file: {str(e)}")

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
            "message": "Images folder uploaded successfully",
            "students_count": len(uploaded_students),
            "total_files": total_files,
            "uploaded_students": list(uploaded_students)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading images folder: {str(e)}")

# Process data endpoint
@app.post("/api/process-data")
async def process_data():
    try:
        # Import and run the data processing function
        from data import process_face_data
        
        success = process_face_data()
        
        if not success:
            raise HTTPException(status_code=500, detail="Data processing failed")
        
        return {
            "success": True,
            "message": "Data processing successful"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

# Update database endpoint
@app.post("/api/update-database")
async def update_database():
    try:
        # Import and run the database update function
        from database import update_database as update_db
        
        success = update_db()
        
        if not success:
            raise HTTPException(status_code=500, detail="Database update failed")
        
        return {
            "success": True,
            "message": "Database updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating database: {str(e)}")

# Download sample Excel file
@app.get("/sample-excel")
async def download_sample_excel():
    """Download sample Excel file"""
    sample_file = "students_sample.xlsx"
    if os.path.exists(sample_file):
        return FileResponse(sample_file, filename="students_sample.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        raise HTTPException(status_code=404, detail="Sample file does not exist")

if __name__ == "__main__":
    print("🚀 Starting Face Recognition Attendance API...")
    print("📋 Available endpoints:")
    print("   - POST /login - Teacher login")
    print("   - GET /today-checkins - Today's attendance list")
    print("   - WS /ws/attendance - WebSocket real-time")
    print("   - POST /notify-attendance - New attendance notification")
    print("   - POST /api/upload-excel - Upload student Excel file")
    print("   - POST /api/upload-images - Upload student images folder")
    print("   - POST /api/process-data - Process data from Excel and images")
    print("   - POST /api/update-database - Update database from processed data")
    print("   - GET /sample-excel - Download sample Excel file")
    print("🌐 Server running on: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
