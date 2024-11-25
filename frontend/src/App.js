import React, { useEffect, useRef, useState } from "react";

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [socket, setSocket] = useState(null);
  const [processing, setProcessing] = useState(false);

  // Kết nối WebSocket
  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws");
    
    ws.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected. Reconnecting...");
      // Tạo lại kết nối khi bị ngắt
      setTimeout(() => {
        const ws = new WebSocket("ws://127.0.0.1:8000/ws");
        setSocket(ws);
      }, 1000); // 1 giây sau sẽ thử lại
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    setSocket(ws); // Chỉ tạo một lần và sử dụng lại WebSocket

    return () => {
      if (ws) ws.close(); // Đảm bảo đóng WebSocket khi component unmount
    };
  }, []); // Thêm [] để đảm bảo chỉ chạy một lần khi component mount

  // Bắt đầu luồng webcam
  useEffect(() => {
    const startVideo = async () => {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
      });
      videoRef.current.srcObject = stream;
    };

    startVideo();
  }, []);

  // Gửi frame video liên tục
  useEffect(() => {
    const sendFrame = () => {
      if (!socket || socket.readyState !== WebSocket.OPEN || processing) return;

      setProcessing(true);
      const canvas = canvasRef.current;
      const video = videoRef.current;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const frameData = canvas.toDataURL("image/jpeg");
      const base64Frame = frameData.split(",")[1];

      // Gửi frame qua WebSocket
      socket.send(JSON.stringify({ frame: base64Frame }));

      setProcessing(false);
    };

    // Gửi frame mỗi 200ms thay vì 100ms để giảm tải
    const intervalId = setInterval(sendFrame, 300); 

    return () => clearInterval(intervalId); // Dọn dẹp khi component unmount
  }, [socket, processing]);

  // Lắng nghe dữ liệu từ WebSocket
  useEffect(() => {
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Tạo ảnh từ dữ liệu base64
        const img = new Image();
        img.src = `data:image/jpeg;base64,${data.frame}`;
        img.onload = () => {
          // Vẽ lên canvas
          const ctx = canvasRef.current.getContext("2d");
          ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height); // Xóa canvas trước khi vẽ ảnh mới
          ctx.drawImage(img, 0, 0, canvasRef.current.width, canvasRef.current.height);
        };
      };
    }
  }, [socket]);

  return (
    <div className="App">
      <h1>Realtime Hand Detection</h1>
      <div>
        {/* Hiển thị video từ webcam */}
        <video 
          ref={videoRef} 
          autoPlay 
          muted 
          style={{ width: "80%", border: "1px solid black" }} 
        />
        {/* Hiển thị kết quả lên canvas */}
        <canvas 
          ref={canvasRef} 
          style={{ width: "80%", border: "1px solid black", marginTop: "20px" }} 
        />
      </div>
    </div>
  );
}

export default App;
