package com.example.android_app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import android.view.ViewGroup
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Face
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.example.android_app.utils.AppStrings
import com.example.android_app.utils.FaceWebSocketClient
import com.example.android_app.utils.toJpegByteArray
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.util.concurrent.Executors
import okhttp3.OkHttpClient
import okhttp3.Request

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FaceRecognitionScreen(strings: AppStrings, loggedInUsername: String, onBack: () -> Unit) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    // --- STATES ---
    var isScanning by remember { mutableStateOf(false) }
    var showCamera by remember { mutableStateOf(true) }

    // States để thông báo cho User
    var statusMessage by remember { mutableStateOf("Vui lòng nhìn thẳng và bấm Bắt đầu quét") }
    var isSuccess by remember { mutableStateOf(false) }

    // --- STATES LẤY DANH SÁCH SERVER ---
    var camServerIdsStr by remember { mutableStateOf("") }
    var serverCount by remember { mutableStateOf(0) }
    var isFetchingServers by remember { mutableStateOf(true) }

    val smoothBack: () -> Unit = {
        showCamera = false
        coroutineScope.launch {
            delay(50)
            onBack()
        }
    }

    BackHandler(enabled = true) { smoothBack() }

    // --- QUẢN LÝ QUYỀN CAMERA ---
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted -> hasCameraPermission = isGranted }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    // --- GỌI API LẤY DANH SÁCH NHÀ (SERVER) TỰ ĐỘNG ---
    LaunchedEffect(loggedInUsername) {
        if (loggedInUsername.isNotBlank()) {
            kotlinx.coroutines.withContext(Dispatchers.IO) {
                try {
                    val client = OkHttpClient()
                    val url = "http://100.126.85.58:8000/cameras?account=$loggedInUsername"

                    val request = Request.Builder().url(url).build()
                    val response = client.newCall(request).execute()

                    if (response.isSuccessful) {
                        val jsonResponse = JSONObject(response.body!!.string())
                        val serversArray = jsonResponse.optJSONArray("servers")

                        val idList = mutableListOf<String>()
                        if (serversArray != null) {
                            for (i in 0 until serversArray.length()) {
                                val obj = serversArray.getJSONObject(i)
                                idList.add(obj.getString("cam_server_id"))
                            }
                        }
                        serverCount = idList.size
                        // Nối các ID lại bằng dấu phẩy (vd: "server1,server2")
                        camServerIdsStr = idList.joinToString(",")
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                } finally {
                    isFetchingServers = false
                }
            }
        } else {
            isFetchingServers = false
        }
    }

    // --- KHỞI TẠO WEBSOCKET CLIENT ---
    val webSocketClient = remember {
        FaceWebSocketClient(
            onMessage = { type, json ->
                when (type) {
                    "processing" -> {
                        val progress = json.optString("progress", "")
                        statusMessage = "Đang lấy mẫu: $progress"
                    }
                    "success" -> {
                        statusMessage = "Đăng ký thành công!"
                        isScanning = false
                        isSuccess = true
                        coroutineScope.launch(Dispatchers.Main) {
                            delay(1500)
                            smoothBack()
                        }
                    }
                    "low_quality" -> statusMessage = "Ảnh mờ, vui lòng giữ điện thoại tĩnh!"
                    "no_face_detected" -> statusMessage = "Không tìm thấy khuôn mặt!"
                    "more_than_one" -> statusMessage = "Chỉ được có 1 người trong khung hình!"
                    "spoof_detected" -> statusMessage = "CẢNH BÁO: Phát hiện ảnh giả mạo!"
                    "error" -> statusMessage = "Lỗi máy chủ!"
                }
            },
            onClosed = {
                if (!isSuccess) statusMessage = "Đã ngắt kết nối với Server"
            }
        )
    }

    DisposableEffect(Unit) {
        webSocketClient.connect()
        onDispose { webSocketClient.disconnect() }
    }

    val scanLineY = remember { Animatable(0f) }
    LaunchedEffect(isScanning) {
        if (isScanning) {
            scanLineY.animateTo(
                targetValue = 380f,
                animationSpec = infiniteRepeatable(tween(2000, easing = LinearEasing), RepeatMode.Reverse)
            )
        } else {
            scanLineY.snapTo(0f)
        }
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(strings.faceRecognition, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = smoothBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 1. NHẬP THÔNG TIN TRƯỚC KHI QUÉT
            OutlinedTextField(
                value = loggedInUsername,
                onValueChange = { },
                label = { Text("Tên người dùng") },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                singleLine = true,
                readOnly = true,
                enabled = false
            )

            // Dòng text thông báo số lượng server sẽ được đồng bộ
            if (isFetchingServers) {
                Text("Đang tải dữ liệu Camera Server...", color = Color.Gray, style = MaterialTheme.typography.bodySmall)
            } else if (serverCount > 0) {
                Text("Sẽ đồng bộ khuôn mặt lên $serverCount khu vực", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            } else {
                Text("Chưa có Camera Server nào được liên kết!", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = statusMessage,
                style = MaterialTheme.typography.bodyLarge,
                color = when {
                    isSuccess -> Color(0xFF4CAF50)
                    statusMessage.contains("mờ") || statusMessage.contains("giả mạo") -> MaterialTheme.colorScheme.error
                    else -> MaterialTheme.colorScheme.primary
                },
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            Box(
                modifier = Modifier
                    .width(260.dp)
                    .height(380.dp)
                    .clip(RoundedCornerShape(200.dp))
                    .background(Color.Black.copy(alpha = 0.05f))
                    .border(
                        width = 4.dp,
                        color = if (isScanning) MaterialTheme.colorScheme.primary else Color.LightGray,
                        shape = RoundedCornerShape(200.dp)
                    ),
                contentAlignment = Alignment.TopCenter
            ) {
                if (hasCameraPermission && showCamera) {
                    StreamingCameraPreview(
                        isScanning = isScanning,
                        onFrameCaptured = { jpegBytes ->
                            // Đẩy frame lên Server, kèm theo chuỗi ID đã gộp
                            if (camServerIdsStr.isNotEmpty()) {
                                webSocketClient.sendFrame(jpegBytes, loggedInUsername, camServerIdsStr)
                            }
                        },
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    Icon(
                        Icons.Default.Face, contentDescription = null,
                        modifier = Modifier.fillMaxSize().padding(60.dp),
                        tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.2f)
                    )
                }

                if (isScanning) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(4.dp)
                            .offset(y = scanLineY.value.dp)
                            .background(
                                Brush.horizontalGradient(
                                    listOf(Color.Transparent, MaterialTheme.colorScheme.primary, Color.Transparent)
                                )
                            )
                    )
                }
            }

            Spacer(modifier = Modifier.weight(1f))

            Button(
                onClick = {
                    if (isScanning) {
                        isScanning = false
                        statusMessage = "Đã dừng quét"
                    } else {
                        if (serverCount == 0) {
                            statusMessage = "Lỗi: Bạn chưa có Server nào để lưu mặt!"
                            return@Button
                        }
                        if (hasCameraPermission) {
                            isScanning = true
                            statusMessage = "Đang kết nối để phân tích..."
                        } else {
                            permissionLauncher.launch(Manifest.permission.CAMERA)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = RoundedCornerShape(16.dp),
                // Nút bị khóa nếu đang fetch server hoặc không có server nào
                enabled = !isSuccess && !isFetchingServers && serverCount > 0,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isScanning) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                )
            ) {
                Text(if (isScanning) strings.stopScan else strings.startScan)
            }
        }
    }
}

// ==========================================
// COMPOSABLE CAMERA STREAMING (GIỮ NGUYÊN)
// ==========================================
@Composable
fun StreamingCameraPreview(
    isScanning: Boolean,
    onFrameCaptured: (ByteArray) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val executor = remember { Executors.newSingleThreadExecutor() }

    val latestIsScanning by rememberUpdatedState(isScanning)
    val latestOnFrameCaptured by rememberUpdatedState(onFrameCaptured)

    AndroidView(
        factory = { ctx ->
            val previewView = PreviewView(ctx).apply {
                scaleType = PreviewView.ScaleType.FILL_CENTER
            }

            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }

                val imageAnalysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                    .build()

                var lastTimeAnalyzed = 0L

                imageAnalysis.setAnalyzer(executor) { imageProxy ->
                    if (latestIsScanning) {
                        val currentTime = System.currentTimeMillis()
                        if (currentTime - lastTimeAnalyzed >= 300) {
                            lastTimeAnalyzed = currentTime

                            try {
                                val bitmap = imageProxy.toBitmap()
                                val stream = java.io.ByteArrayOutputStream()
                                bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 80, stream)
                                val jpegBytes = stream.toByteArray()
                                latestOnFrameCaptured(jpegBytes)
                            } catch (e: Exception) {
                                android.util.Log.e("FaceWS", "Lỗi convert ảnh: ${e.message}")
                            }
                        }
                    }
                    imageProxy.close()
                }

                val cameraSelector = CameraSelector.Builder()
                    .requireLensFacing(CameraSelector.LENS_FACING_FRONT)
                    .build()

                try {
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(
                        lifecycleOwner, cameraSelector, preview, imageAnalysis
                    )
                } catch (exc: Exception) {
                    exc.printStackTrace()
                }
            }, ContextCompat.getMainExecutor(ctx))

            previewView
        },
        onRelease = {
            val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                cameraProvider.unbindAll()
            }, ContextCompat.getMainExecutor(context))
            executor.shutdown()
        },
        modifier = modifier
    )
}