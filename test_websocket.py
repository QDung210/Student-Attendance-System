import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/attendance"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Lắng nghe tin nhắn
            async for message in websocket:
                print(f"📨 Received: {message}")
                
                # Parse JSON
                try:
                    data = json.loads(message)
                    print(f"👤 Student: {data['name']} ({data['student_id']})")
                    print(f"⏰ Time: {data['attendance_time']}")
                    print("-" * 50)
                except json.JSONDecodeError:
                    print("❌ Invalid JSON received")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Testing WebSocket /ws/attendance")
    print("Press Ctrl+C to stop...")
    asyncio.run(test_websocket())
