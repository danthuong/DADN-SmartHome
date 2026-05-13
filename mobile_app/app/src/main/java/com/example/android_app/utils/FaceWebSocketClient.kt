package com.example.android_app.utils

import android.util.Log
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import android.util.Base64

class FaceWebSocketClient(
    private val serverIp: String = "100.126.85.58",
    private val onMessage: (String, JSONObject) -> Unit,
    private val onClosed: () -> Unit
) {
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    fun connect() {
        val request = Request.Builder().url("ws://$serverIp:8000/ws/register").build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("FaceWS", "Connected to AI Server")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d("FaceWS", "Received: $text")
                val json = JSONObject(text)
                val messageType = json.optString("message", "")
                onMessage(messageType, json) // Bắn dữ liệu về cho UI xử lý
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d("FaceWS", "Closed: $reason")
                onClosed()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("FaceWS", "Error: ${t.message}")
                onMessage("error", JSONObject().put("detail", t.message))
            }
        })
    }

    // Hàm này được gọi liên tục mỗi khi Camera chộp được 1 frame
    fun sendFrame(imageBytes: ByteArray, name: String, camServerIds: String) {
        if (webSocket == null) return
        try {
            // BẢN UPDATE: Mã hóa ảnh thành chuỗi Base64 (Nhẹ và an toàn hơn rất nhiều)
            val base64String = Base64.encodeToString(imageBytes, Base64.NO_WRAP)

            val jsonObject = JSONObject().apply {
                put("file", base64String) // Truyền chuỗi String lên thay vì mảng Int
                put("name", name)
                put("cam_server_id", camServerIds)
            }
            webSocket?.send(jsonObject.toString())
        } catch (e: Exception) {
            e.printStackTrace()
            Log.e("FaceWS", "Lỗi đóng gói JSON: ${e.message}")
        }
    }

    fun disconnect() {
        webSocket?.close(1000, "User cancelled")
        webSocket = null
    }
}

