from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from keras.models import load_model
import torch
from pathlib import Path
import base64
import json

app = FastAPI()

# Cấu hình CORS cho phép kết nối từ ReactJS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc chỉ định domain ReactJS, ví dụ: ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load YOLOv5 và mô hình Keras
yolo_weights_path = str(Path('./yolov5/runs/train/exp/weights/best.pt'))
keras_model_path = str(Path('./model/fine_tune_asl_model.h5'))

# Tải mô hình YOLOv5
try:
    yolo_model = torch.hub.load(
        './yolov5',
        'custom',
        path=yolo_weights_path,
        source='local',
        force_reload=True
    )
    print("YOLOv5 model loaded successfully.")
except Exception as e:
    print(f"Error loading YOLOv5 model: {e}")
    exit(1)

# Tải mô hình Keras
try:
    sign_model = load_model(keras_model_path)
    print("Keras model loaded successfully.")
except Exception as e:
    print(f"Error loading Keras model: {e}")
    exit(1)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Nhận frame từ ReactJS
            data = await websocket.receive_text()
            print("Da nhan frame")
            frame_data = json.loads(data)
            frame_base64 = frame_data.get("frame")
            frame_bytes = base64.b64decode(frame_base64)
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

            # Xử lý ảnh bằng YOLOv5 để phát hiện bàn tay
            results = yolo_model(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            detections = results.pandas().xyxy[0]  # Chuyển kết quả từ YOLOv5 thành DataFrame

            for _, row in detections.iterrows():
                if row['name'] == 'hand' and row['confidence'] > 0.5:
                    xmin, ymin, xmax, ymax = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
                    cropped_hand = frame[ymin:ymax, xmin:xmax]  # Cắt bàn tay

                    # Chỉnh lại kích thước ảnh về 100x100 hoặc 200x200 (phù hợp với yêu cầu của mô hình Keras)
                    resized_frame = cv2.resize(cropped_hand, (100, 100))  # Thay đổi ở đây nếu cần
                    reshaped_frame = np.array(resized_frame).reshape((1, 100, 100, 3)) / 255.0  # Kích thước 100x100

                    # Dự đoán ký hiệu ngôn ngữ bằng mô hình Keras
                    prediction = sign_model.predict(reshaped_frame)
                    label = f"Detected: {np.argmax(prediction)}"  # Nhãn dự đoán
                    confidence = float(prediction.max())  # Mức độ tự tin

                    # Vẽ bounding box và nhãn lên ảnh
                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                    cv2.putText(frame, f"{label} ({confidence:.2f})", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Chuyển frame đã xử lý thành base64 để gửi lại ReactJS
            _, buffer = cv2.imencode(".jpg", frame)
            frame_processed = base64.b64encode(buffer).decode("utf-8")

            # Gửi kết quả về ReactJS
            try:
                await websocket.send_json({
                    "frame": frame_processed
                })
            except WebSocketDisconnect:
                print("WebSocket connection closed.")
                break

    except WebSocketDisconnect:
        print("WebSocket connection closed.")
