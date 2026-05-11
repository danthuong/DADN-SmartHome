import websocket

ws = websocket.WebSocket()
ws.connect("ws://localhost:8000/ws/register")
print("connected")
ws.close()