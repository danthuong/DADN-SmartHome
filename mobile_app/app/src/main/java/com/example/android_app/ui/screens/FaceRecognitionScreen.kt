package com.example.android_app.ui.screens

import android.graphics.Bitmap
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.launch
import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.android_app.utils.AppStrings

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FaceRecognitionScreen(strings: AppStrings, onBack: () -> Unit) {
    // --- STATE QUẢN LÝ DỮ LIỆU ---
    var imageUri by remember { mutableStateOf<Uri?>(null) }
    var capturedBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var userName by remember { mutableStateOf("") }
    var userRole by remember { mutableStateOf("Owner") } // Mặc định là chủ nhà
    var step by remember { mutableStateOf(1) } // 1: Quét/Chọn ảnh, 2: Nhập thông tin

    // Launcher: Chọn ảnh từ Album
    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            imageUri = uri
            step = 2
        }
    }

    // Launcher: Chụp ảnh trực tiếp (Yêu cầu module 3 trong README)
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicturePreview()) { bitmap ->
        if (bitmap != null) {
            capturedBitmap = bitmap
            step = 2
        }
    }

    // --- HIỆU ỨNG QUÉT (SCANNING ANIMATION) ---
    val infiniteTransition = rememberInfiniteTransition(label = "scan")
    val scanLineY by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 240f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "line"
    )

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(strings.profileAva, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
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
                // --- BƯỚC 1: GIAO DIỆN QUÉT KHUÔN MẶT ---
                Text(
                    "Đặt khuôn mặt vào khung",
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color.Gray
                )

                Spacer(modifier = Modifier.height(32.dp))

                // KHUNG QUÉT CÓ HIỆU ỨNG CHẠY DÒNG
                Box(
                    modifier = Modifier
                        .size(250.dp)
                        .border(4.dp, MaterialTheme.colorScheme.primary, RoundedCornerShape(24.dp))
                        .padding(8.dp),
                    contentAlignment = Alignment.TopCenter
                ) {
                    // Icon Camera mờ ở nền
                    Icon(
                        Icons.Default.Face,
                        contentDescription = null,
                        modifier = Modifier.fillMaxSize().padding(40.dp),
                        tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.1f)
                    )

                    // THANH QUÉT CHẠY LÊN XUỐNG
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(2.dp)
                            .offset(y = scanLineY.dp)
                            .background(
                                Brush.horizontalGradient(
                                    listOf(Color.Transparent, MaterialTheme.colorScheme.primary, Color.Transparent)
                                )
                            )
                    )
                }

                Spacer(modifier = Modifier.height(48.dp))

                // NÚT CHỨC NĂNG
                Button(
                    onClick = { cameraLauncher.launch() },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Icon(Icons.Default.PhotoCamera, null)
                    Spacer(Modifier.width(8.dp))
                    Text(strings.cam) // Chụp ảnh
                }

                Spacer(modifier = Modifier.height(16.dp))

                OutlinedButton(
                    onClick = { galleryLauncher.launch("image/*") },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Icon(Icons.Default.Image, null)
                    Spacer(Modifier.width(8.dp))
                    Text(strings.lib) // Chọn từ thư viện
                }

            } else {
                // --- BƯỚC 2: NHẬP THÔNG TIN ĐĂNG KÝ (Sau khi đã có ảnh) ---
                Text(
                    "Xác nhận thông tin",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )

                Spacer(modifier = Modifier.height(24.dp))

                // HIỂN THỊ ẢNH ĐÃ CHỌN/CHỤP
                Box(modifier = Modifier.size(180.dp)) {
                    if (capturedBitmap != null) {
                        Image(
                            bitmap = capturedBitmap!!.asImageBitmap(),
                            contentDescription = null,
                            modifier = Modifier.fillMaxSize().clip(CircleShape).border(2.dp, MaterialTheme.colorScheme.primary, CircleShape),
                            contentScale = ContentScale.Crop
                        )
                    } else {
                        AsyncImage(
                            model = imageUri,
                            contentDescription = null,
                            modifier = Modifier.fillMaxSize().clip(CircleShape).border(2.dp, MaterialTheme.colorScheme.primary, CircleShape),
                            contentScale = ContentScale.Crop
                        )
                    }
                }

                Spacer(modifier = Modifier.height(32.dp))

                // NHẬP TÊN (Sẽ gửi lên AI Server)
                OutlinedTextField(
                    value = userName,
                    onValueChange = { userName = it },
                    label = { Text(strings.username) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(16.dp))

                // NHẬP VAI TRÒ (Role)
                OutlinedTextField(
                    value = userRole,
                    onValueChange = { userRole = it },
                    label = { Text("Vai trò (Role)") },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                )

                Spacer(modifier = Modifier.weight(1f))

                // NÚT LƯU - GỬI LÊN AI SERVER
                Button(
                    onClick = {
                        // LOGIC: Gửi dữ liệu theo README
                        // 1. Chuyển ảnh sang Base64
                        // 2. Gửi POST request tới http://<AI_SERVER_IP>:8000/register
                        // 3. Metadata: { "name": userName, "location": "house_A" }
                        onBack()
                    },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Text(strings.save)
                }
            }
        }
    }
}