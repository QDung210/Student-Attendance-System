import sys
import cv2
import sqlite3
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from facenet_pytorch import MTCNN, InceptionResnetV1
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import torch
import time
from datetime import datetime
import threading
import requests  # Thêm để gọi API
import json

# Khởi tạo model và Qdrant
device = torch.device('cpu')
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)
client = QdrantClient(host="localhost", port=6333)
collection_name = "faces"
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Global variables
current_recognition = {"student_id": None, "confidence": 0.0, "start_time": None}
camera_frame = None
last_update_time = 0  # Last update time
last_recognition_per_student = {}  # Last recognition time for each student
current_face_image = None  # Current face image to save when checking in

def get_face_embedding(face_img):
    """Generate embedding from face image"""
    face_img = cv2.resize(face_img, (160, 160))
    face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    face_img = face_img / 255.0
    face_img = torch.tensor(face_img, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
        embedding = model(face_img.to(device)).cpu().numpy()[0]
    return embedding / np.linalg.norm(embedding)

def get_student_info(student_id):
    """Get student information from database"""
    # Don't use cache to always get the latest information
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, class, major, avatar, attendance_time, checkin_face FROM students WHERE student_id = ?", (student_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result

def is_already_attended(attendance_time):
    """Check if student has already attended in the past 24 hours"""
    if not attendance_time:
        return False
    
    try:
        last_attendance = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()
        time_diff = current_time - last_attendance
        return time_diff.total_seconds() < 24 * 3600  # 24 hours = 86400 seconds
    except:
        return False

def update_attendance_time(student_id):
    """Update attendance time for student"""
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE students SET attendance_time = ? WHERE student_id = ?", (current_time, student_id))
    conn.commit()
    conn.close()
    
    # Send notification to API backend
    try:
        response = requests.post(
            "http://localhost:8000/notify-attendance",
            params={"student_id": student_id, "attendance_time": current_time},
            timeout=5
        )
        if response.status_code == 200:
            print(f"✅ Sent attendance notification for {student_id}")
        else:
            print(f"⚠️ Notification error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Cannot connect to API: {e}")

def update_attendance_with_face(student_id, face_image):
    """Update attendance time and save face image"""
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Convert image to bytes
    _, buffer = cv2.imencode('.jpg', face_image)
    face_blob = buffer.tobytes()
    
    cursor.execute("UPDATE students SET attendance_time = ?, checkin_face = ? WHERE student_id = ?", 
                   (current_time, face_blob, student_id))
    conn.commit()
    conn.close()
    
    # Send notification to API backend
    try:
        response = requests.post(
            "http://localhost:8000/notify-attendance",
            params={"student_id": student_id, "attendance_time": current_time},
            timeout=5
        )
        if response.status_code == 200:
            print(f"✅ Sent attendance notification for {student_id}")
        else:
            print(f"⚠️ Notification error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Cannot connect to API: {e}")

def camera_worker():
    """Worker thread for camera"""
    global camera_frame, current_recognition
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    frame_count = 0
    last_results = {}
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
            
        frame = cv2.flip(frame, 1)
        frame_count += 1
        
        # Xử lý mỗi 3 frame
        if frame_count % 3 != 0:
            # Vẽ lại kết quả cũ
            for (x, y, w, h), (name, conf) in last_results.items():
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"{name} ({conf:.2f})", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            camera_frame = frame
            continue
        
        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        last_results = {}
        recognized_student = None
        max_confidence = 0.0
        best_face_image = None
        
        for (x, y, w, h) in faces:
            face_img = frame[y:y+h, x:x+w]
            embedding = get_face_embedding(face_img)
            
            try:
                search_result = client.search(
                    collection_name=collection_name,
                    query_vector=embedding.tolist(),
                    limit=1
                )
                
                if search_result and search_result[0].score > 0.6:
                    student_id = search_result[0].payload["student_id"]
                    confidence = search_result[0].score
                    
                    if confidence > max_confidence:
                        max_confidence = confidence
                        recognized_student = student_id
                        best_face_image = face_img  # Save the best face image
                    
                    last_results[(x, y, w, h)] = (student_id, confidence)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"{student_id} ({confidence:.2f})", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    last_results[(x, y, w, h)] = ("Unknown", 0.0)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    cv2.putText(frame, "Unknown", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            except Exception as e:
                print(f"Qdrant error: {e}")
                last_results[(x, y, w, h)] = ("Error", 0.0)
        
        # Update recognition status
        current_time = time.time()
        if recognized_student and max_confidence > 0.8:
            if (current_recognition["student_id"] != recognized_student or 
                current_recognition["confidence"] < 0.8):
                current_recognition["student_id"] = recognized_student
                current_recognition["confidence"] = max_confidence
                current_recognition["start_time"] = current_time
                global current_face_image
                current_face_image = best_face_image  # Save face image to use when checking in
        elif max_confidence <= 0.8:
            current_recognition = {"student_id": None, "confidence": 0.0, "start_time": None}
            current_face_image = None
        
        camera_frame = frame

def main():
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Student Face Recognition System")
    window.setGeometry(100, 100, 1200, 800)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    # Main layout
    main_layout = QHBoxLayout(central_widget)
    
    # Camera panel (left)
    camera_panel = QWidget()
    camera_layout = QVBoxLayout(camera_panel)
    
    camera_title = QLabel("FACE RECOGNITION CAMERA")
    camera_title.setAlignment(Qt.AlignCenter)
    camera_title.setFont(QFont("Arial", 16, QFont.Bold))
    camera_title.setStyleSheet("color: #333; padding: 10px; background-color: #e0e0e0;")
    
    camera_label = QLabel()
    camera_label.setMinimumSize(640, 480)
    camera_label.setAlignment(Qt.AlignCenter)
    camera_label.setStyleSheet("border: 2px solid #ddd; background-color: black;")
    camera_label.setText("Starting camera...")
    
    status_label = QLabel("Status: Ready")
    status_label.setStyleSheet("padding: 10px; background-color: #e8f5e8; border: 1px solid #4CAF50;")
    
    camera_layout.addWidget(camera_title)
    camera_layout.addWidget(camera_label)
    camera_layout.addWidget(status_label)
    
    # Student information panel (right)
    info_panel = QWidget()
    info_panel.setFixedWidth(350)
    info_panel.setStyleSheet("background-color: #f5f5f5; border-left: 2px solid #ddd;")
    info_layout = QVBoxLayout(info_panel)
    
    info_title = QLabel("STUDENT INFORMATION")
    info_title.setAlignment(Qt.AlignCenter)
    info_title.setFont(QFont("Arial", 14, QFont.Bold))
    info_title.setStyleSheet("color: #333; padding: 10px; background-color: #e0e0e0;")
    
    avatar_label = QLabel()
    avatar_label.setFixedSize(200, 200)
    avatar_label.setAlignment(Qt.AlignCenter)
    avatar_label.setStyleSheet("border: 2px solid #ddd; background-color: white;")
    avatar_label.setText("No image")
    
    student_id_label = QLabel("Student ID: --")
    student_id_label.setStyleSheet("padding: 8px; font-size: 14px; font-weight: bold;")
    
    name_label = QLabel("Name: --")
    name_label.setStyleSheet("padding: 8px; font-size: 14px;")
    
    class_label = QLabel("Class: --")
    class_label.setStyleSheet("padding: 8px; font-size: 14px;")
    
    major_label = QLabel("Major: --")
    major_label.setStyleSheet("padding: 8px; font-size: 14px;")
    
    attendance_label = QLabel("Attendance: --")
    attendance_label.setStyleSheet("padding: 8px; font-size: 14px; color: #2196F3;")
    
    info_layout.addWidget(info_title)
    info_layout.addWidget(avatar_label, alignment=Qt.AlignCenter)
    info_layout.addWidget(student_id_label)
    info_layout.addWidget(name_label)
    info_layout.addWidget(class_label)
    info_layout.addWidget(major_label)
    info_layout.addWidget(attendance_label)
    info_layout.addStretch()
    
    main_layout.addWidget(camera_panel)
    main_layout.addWidget(info_panel)
    
    # Start camera worker
    camera_thread = threading.Thread(target=camera_worker, daemon=True)
    camera_thread.start()
    
    # UI update timer
    def update_ui():
        global camera_frame, current_recognition
        
        # Update camera
        if camera_frame is not None:
            rgb_image = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            camera_label.setPixmap(scaled_pixmap)
        
        # Check recognition > 0.8 for 1 second
        if (current_recognition["student_id"] and 
            current_recognition["confidence"] > 0.8 and 
            current_recognition["start_time"] and 
            time.time() - current_recognition["start_time"] >= 1.0):
            
            student_id = current_recognition["student_id"]
            confidence = current_recognition["confidence"]
            
            # Check delay time to avoid continuous updates
            global last_update_time, last_recognition_per_student
            current_time = time.time()
            
            # Check general delay time
            if current_time - last_update_time < 3:  # 3 seconds delay
                return
            
            # Check individual delay time for each student
            if student_id in last_recognition_per_student:
                if current_time - last_recognition_per_student[student_id] < 10:  # 10 seconds delay per student
                    return
            
            last_update_time = current_time
            last_recognition_per_student[student_id] = current_time
            
            # Update student information
            info = get_student_info(student_id)
            if info:
                student_id_label.setText(f"Student ID: {info[0]}")
                name_label.setText(f"Name: {info[1]}")
                class_label.setText(f"Class: {info[2]}")
                major_label.setText(f"Major: {info[3]}")
                
                # Display avatar
                if info[4]:  # avatar blob
                    pixmap = QPixmap()
                    pixmap.loadFromData(info[4])
                    scaled_avatar = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    avatar_label.setPixmap(scaled_avatar)
                
                # Check if already attended in 24h
                attendance_time = info[5] if len(info) > 5 else None
                if is_already_attended(attendance_time):
                    # Already attended in 24h - no update
                    last_time = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
                    attendance_label.setText(f"Already attended: {last_time}")
                    status_label.setText(f"Already attended: {info[1]} ({confidence:.2f})")
                    status_label.setStyleSheet("padding: 10px; background-color: #fff3cd; border: 1px solid #ffc107;")
                else:
                    # Not attended in 24h - update with face image
                    if current_face_image is not None:
                        update_attendance_with_face(student_id, current_face_image)
                    else:
                        update_attendance_time(student_id)
                    current_time = datetime.now().strftime("%H:%M:%S")
                    attendance_label.setText(f"Attendance: {current_time}")
                    status_label.setText(f"Recognized: {info[1]} ({confidence:.2f})")
                    status_label.setStyleSheet("padding: 10px; background-color: #e3f2fd; border: 1px solid #2196F3;")
                
                # Reset to avoid continuous updates
                current_recognition["start_time"] = None
                current_recognition["student_id"] = None
                current_recognition["confidence"] = 0.0
        
        elif not current_recognition["student_id"]:
            # Reset information when no recognition
            status_label.setText("Status: Ready")
            status_label.setStyleSheet("padding: 10px; background-color: #e8f5e8; border: 1px solid #4CAF50;")
    
    # Update UI timer every 100ms
    timer = QTimer()
    timer.timeout.connect(update_ui)
    timer.start(100)
    
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()