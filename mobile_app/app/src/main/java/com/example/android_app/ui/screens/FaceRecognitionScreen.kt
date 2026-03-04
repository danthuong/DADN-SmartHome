package com.example.android_app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.android_app.utils.AppStrings
import android.view.ViewGroup
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FaceRecognitionScreen(strings: AppStrings, onBack: () -> Unit) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var userName by remember { mutableStateOf("") }
    var userRole by remember { mutableStateOf("Owner") }
    var step by remember { mutableStateOf(1) }

    var showCamera by remember { mutableStateOf(true) }


    val smoothBack: () -> Unit = {
        showCamera = false
        coroutineScope.launch {
            delay(50)
            onBack()
        }
    }

    BackHandler(enabled = true) {
        smoothBack()
    }

    // --- QUẢN LÝ QUYỀN CAMERA ---
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        hasCameraPermission = isGranted
    }

    // Tự động xin quyền ngay khi vào màn hình
    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    // --- TRẠNG THÁI QUÉT ---
    var isScanning by remember { mutableStateOf(false) }
    var scanCompleted by remember { mutableStateOf(false) }

    val scanLineY = remember { Animatable(0f) }

    LaunchedEffect(isScanning) {
        if (isScanning) {
            scanLineY.animateTo(
                targetValue = 380f,
                animationSpec = infiniteRepeatable(
                    animation = tween(2000, easing = LinearEasing),
                    repeatMode = RepeatMode.Reverse
                )
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
            if (step == 1) {
                Text(
                    text = if (isScanning) strings.scanning else strings.faceInstruction,
                    style = MaterialTheme.typography.bodyLarge,
                    color = if (isScanning) MaterialTheme.colorScheme.primary else Color.Gray
                )

                Spacer(modifier = Modifier.height(32.dp))

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
                    // HIỂN THỊ CAMERA NẾU CÓ QUYỀN
                    if (hasCameraPermission && showCamera) {
                        CameraPreview(modifier = Modifier.fillMaxSize())
                    } else {
                        // Hiển thị Placeholder nếu chưa cấp quyền
                        Icon(
                            Icons.Default.Face,
                            contentDescription = null,
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(60.dp),
                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.2f)
                        )
                    }

                    // THANH QUÉT CHẠY LÊN XUỐNG
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

                Spacer(modifier = Modifier.height(48.dp))

                Button(
                    onClick = {
                        if (isScanning) {
                            isScanning = false
                            scanCompleted = true
                        } else {
                            // Chỉ cho phép bắt đầu quét khi đã có quyền camera
                            if (hasCameraPermission) {
                                isScanning = true
                                scanCompleted = false
                            } else {
                                permissionLauncher.launch(Manifest.permission.CAMERA)
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isScanning) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                    )
                ) {
                    Text(if (isScanning) strings.stopScan else strings.startScan)
                }

                Spacer(modifier = Modifier.height(16.dp))

                if (scanCompleted) {
                    OutlinedButton(
                        onClick = { step = 2 },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Text(strings.continueBtn)
                    }
                }

            } else {
                // ... (PHẦN BƯỚC 2 GIỮ NGUYÊN NHƯ CODE CŨ CỦA BẠN) ...
                Text(
                    text = "Xác nhận thông tin",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )

                Spacer(modifier = Modifier.height(32.dp))

                OutlinedTextField(
                    value = userName,
                    onValueChange = { userName = it },
                    label = { Text(strings.username) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = userRole,
                    onValueChange = { userRole = it },
                    label = { Text(strings.role) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                )

                Spacer(modifier = Modifier.weight(1f))

                Button(
                    onClick = {
                        // TODO: Gửi dữ liệu lên server
                        onBack()
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Text(strings.save)
                }
            }
        }
    }
}

@Composable
fun CameraPreview(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    AndroidView(
        factory = { ctx ->
            val previewView = PreviewView(ctx).apply {
                this.scaleType = PreviewView.ScaleType.FILL_CENTER
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
            }

            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()

                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }

                val cameraSelector = CameraSelector.Builder()
                    .requireLensFacing(CameraSelector.LENS_FACING_FRONT)
                    .build()

                try {
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(lifecycleOwner, cameraSelector, preview)
                } catch (exc: Exception) {
                    exc.printStackTrace()
                }
            }, ContextCompat.getMainExecutor(ctx))

            previewView
        },
        // THÊM ĐOẠN NÀY ĐỂ GIẢI PHÓNG CAMERA KHI THOÁT
        onRelease = {
            val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                cameraProvider.unbindAll()
            }, ContextCompat.getMainExecutor(context))
        },
        modifier = modifier
    )
}