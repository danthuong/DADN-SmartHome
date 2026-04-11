package com.example.android_app.ui.screens

import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import com.example.android_app.data.SmartHomeRepository
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
// Chú ý: Đảm bảo các file theme này đã tồn tại trong project của bạn
import com.example.android_app.ui.theme.BackgroundBlack
import com.example.android_app.ui.theme.CardGray
import com.example.android_app.ui.theme.PrimaryPurple
import com.example.android_app.R
import com.example.android_app.data.User
import com.example.android_app.utils.AppStrings
import com.example.android_app.utils.ImageUtils
import com.example.android_app.utils.sendNotification

@Composable
fun ProfileScreen(user: User, strings: AppStrings, onBack: () -> Unit, onLogout: () -> Unit) {
    val context = LocalContext.current
    val sharedPref = remember { context.getSharedPreferences("UserPrefs", Context.MODE_PRIVATE) }
    var imageUri by remember { mutableStateOf<Uri?>(null) }
    val avatarBase64 by SmartHomeRepository.avatarBase64.collectAsState()
    val avatarBytes = remember(avatarBase64) {
        avatarBase64?.let { android.util.Base64.decode(it, android.util.Base64.DEFAULT) }
    }
    // Launcher: Chọn từ Album
    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let {
            imageUri = it

            
            // Upload avatar to server
            try {
                val inputStream = context.contentResolver.openInputStream(it)
                val bytes = inputStream?.readBytes()
                inputStream?.close()
                if (bytes != null) {
                    val base64 = android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)
                    GlobalScope.launch {
                        SmartHomeRepository.uploadAvatar(base64)
                    }
                }
            } catch (e: Exception) {
                println("DEBUG: Failed to upload avatar: ${e.message}")
            }
        }
    }

    // Launcher: Chụp bằng Camera
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicturePreview()) { bitmap ->
        bitmap?.let {
            val uri = ImageUtils.saveBitmapToInternalStorage(context, it)
            uri?.let { validUri ->
                imageUri = validUri

                
                // Upload avatar to server
                try {
                    val inputStream = context.contentResolver.openInputStream(validUri)
                    val bytes = inputStream?.readBytes()
                    inputStream?.close()
                    if (bytes != null) {
                        val base64 = android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)
                        GlobalScope.launch {
                            SmartHomeRepository.uploadAvatar(base64)
                        }
                    }
                } catch (e: Exception) {
                    println("DEBUG: Failed to upload avatar: ${e.message}")
                }
            }
        }
    }

    var showDialog by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(24.dp)
            .statusBarsPadding(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, contentDescription = null, tint = MaterialTheme.colorScheme.onSurface) }
            Text(strings.profile, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onSurface)
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Phần hiển thị Avatar
        // Chỗ hiển thị Avatar trong ProfileScreen
        Box(contentAlignment = Alignment.BottomEnd) {
            if (imageUri != null) {
                AsyncImage(
                    model = imageUri,
                    contentDescription = strings.ava,
                    modifier = Modifier
                        .size(140.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                    contentScale = ContentScale.Crop
                )
            } else if (avatarBytes != null) {
                AsyncImage(
                    model = avatarBytes,
                    contentDescription = strings.ava,
                    modifier = Modifier
                        .size(140.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                    contentScale = ContentScale.Crop
                )
            } else {
                // THAY THẾ DÒNG NÀY: Dùng Icon hệ thống thay vì R.drawable nếu bạn chưa có ảnh
                Surface(
                    modifier = Modifier.size(140.dp),
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Icon(
                        imageVector = Icons.Default.Person, // Dùng icon có sẵn
                        contentDescription = null,
                        modifier = Modifier.padding(30.dp),
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }

            IconButton(
                onClick = { showDialog = true },
                modifier = Modifier.size(40.dp).background(MaterialTheme.colorScheme.primary, CircleShape)
            ) {
                Icon(Icons.Default.PhotoCamera, contentDescription = null, tint = Color.White, modifier = Modifier.size(20.dp))
            }
        }

        // Bảng chọn nguồn ảnh
        if (showDialog) {
            AlertDialog(
                onDismissRequest = { showDialog = false },
                title = { Text(strings.changeAva) },
                text = { Text(strings.PicFrom) },
                confirmButton = {
                    TextButton(onClick = { galleryLauncher.launch("image/*"); showDialog = false }) { Text(strings.lib) }
                },
                dismissButton = {
                    TextButton(onClick = { cameraLauncher.launch(null); showDialog = false }) { Text(strings.cam) }
                }
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // HIỂN THỊ THÔNG TIN USER (Họ tên & Username)
        Text(
            text = user.fullName,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )
        Text(
            text = "@${user.username}",
            color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
            style = MaterialTheme.typography.bodyLarge
        )

        Spacer(modifier = Modifier.height(40.dp))
//
//        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
//            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, contentDescription = null) }
//            Text("Thông tin cá nhân", style = MaterialTheme.typography.titleLarge)
//        }

//        Spacer(modifier = Modifier.height(32.dp))

        // Avatar to
//        Surface(modifier = Modifier.size(120.dp), shape = CircleShape, color = CardGray) {
//            Icon(Icons.Default.AccountCircle, contentDescription = null, modifier = Modifier.fillMaxSize(), tint = PrimaryPurple)
//        }
//
//        Spacer(modifier = Modifier.height(24.dp))
//        Text(userName, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
//        Text("Smart Home Admin", color = Color.Gray)
//
//        Spacer(modifier = Modifier.height(32.dp))

        // Gọi đúng tên hàm là ProfileItem (hoặc đổi tên bên dưới thành SettingItem)
        ProfileItem(Icons.Default.Notifications, strings.warningHistory)

//        Spacer(modifier = Modifier.weight(1f))

        // Phần Settings đơn giản
//        SettingItem(Icons.Default.Lock, "Đổi mật khẩu")
//        SettingItem(Icons.Default.Language, "Ngôn ngữ")

        Spacer(modifier = Modifier.height(30.dp))

        // Các nút cài đặt khác
        Button(
            onClick = onLogout,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
            shape = RoundedCornerShape(16.dp)
        ) {
            Text(strings.logout, fontWeight = FontWeight.Bold,fontSize = 20.sp)
        }
    }
}

@Composable
fun ProfileItem(icon: ImageVector, title: String, color: Color = MaterialTheme.colorScheme.onSurface) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(24.dp))
        Spacer(modifier = Modifier.width(16.dp))
        Text(text = title, style = MaterialTheme.typography.bodyLarge, color = color)
    }
}