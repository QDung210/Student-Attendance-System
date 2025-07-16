import os
import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import sys

def process_face_data():
    try:
        # Load model FaceNet PyTorch
        device = torch.device('cpu')
        model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)

        # Create collection
        collection_name = "faces"
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=512, distance=Distance.COSINE)
        )

        # Load face detector
        face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

        def get_face_embedding(face_img):
            face_img = cv2.resize(face_img, (160, 160))
            face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            face_img = face_img / 255.0
            face_img = torch.tensor(face_img, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)
            with torch.no_grad():
                embedding = model(face_img.to(device)).cpu().numpy()[0]
            return embedding / np.linalg.norm(embedding)

        # Images folder path
        images_path = "../avatars"
        point_id = 1

        if not os.path.exists(images_path):
            print(f"❌ Không tìm thấy thư mục ảnh: {images_path}")
            return False

        # Loop through subfolders (person names)
        for person_name in os.listdir(images_path):
            person_path = os.path.join(images_path, person_name)
            
            if os.path.isdir(person_path):
                print(f"📸 Đang xử lý: {person_name}")
                
                processed_images = 0
                for image_file in os.listdir(person_path):
                    if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_path = os.path.join(person_path, image_file)
                        
                        try:
                            # Load image
                            img = cv2.imread(image_path)
                            if img is None:
                                print(f"⚠️ Không thể đọc ảnh: {image_path}")
                                continue
                                
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            
                            # Detect faces
                            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                            
                            if len(faces) > 0:
                                x, y, w, h = faces[0]
                                face_img = img[y:y+h, x:x+w]
                                
                                # Generate embedding
                                embedding = get_face_embedding(face_img)
                                
                                # Add to Qdrant
                                client.upsert(
                                    collection_name=collection_name,
                                    points=[PointStruct(
                                        id=point_id,
                                        vector=embedding.tolist(),
                                        payload={"student_id": person_name, "image_path": image_path}
                                    )]
                                )
                                
                                print(f"✅ Đã thêm: {image_file}")
                                processed_images += 1
                                point_id += 1
                            else:
                                print(f"⚠️ Không tìm thấy khuôn mặt trong: {image_file}")
                        except Exception as e:
                            print(f"❌ Lỗi xử lý ảnh {image_file}: {str(e)}")
                
                print(f"📊 Đã xử lý {processed_images} ảnh cho {person_name}")

        print("🎉 Hoàn tất xử lý dữ liệu!")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi xử lý dữ liệu: {str(e)}")
        return False

if __name__ == "__main__":
    success = process_face_data()
    sys.exit(0 if success else 1)
