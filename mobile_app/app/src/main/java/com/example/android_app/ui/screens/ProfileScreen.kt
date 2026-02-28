package com.example.android_app.ui.screens

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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
// Chú ý: Đảm bảo các file theme này đã tồn tại trong project của bạn
import com.example.android_app.ui.theme.BackgroundBlack
import com.example.android_app.ui.theme.CardGray
import com.example.android_app.ui.theme.PrimaryPurple
import com.example.android_app.R
import com.example.android_app.utils.sendNotification

@Composable
fun ProfileScreen(userName: String, onBack: () -> Unit, onLogout: () -> Unit) {
    var imageUri by remember { mutableStateOf<Uri?>(null) }
    val context = LocalContext.current

    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        imageUri = uri
    }

    Column(
        modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, contentDescription = null) }
            Text("Profile", style = MaterialTheme.typography.titleLarge)
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Phần hiển thị Avatar
        // Chỗ hiển thị Avatar trong ProfileScreen
        Box(contentAlignment = Alignment.BottomEnd) {
            if (imageUri != null) {
                AsyncImage(
                    model = imageUri,
                    contentDescription = null,
                    modifier = Modifier.size(120.dp).clip(CircleShape),
                    contentScale = ContentScale.Crop
                )
            } else {
                // THAY THẾ DÒNG NÀY: Dùng Icon hệ thống thay vì R.drawable nếu bạn chưa có ảnh
                Surface(
                    modifier = Modifier.size(120.dp),
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Icon(
                        imageVector = Icons.Default.AccountCircle, // Dùng icon có sẵn
                        contentDescription = null,
                        modifier = Modifier.padding(20.dp),
                        tint = PrimaryPurple
                    )
                }
            }

            IconButton(
                onClick = { launcher.launch("image/*") },
                modifier = Modifier.size(40.dp).background(PrimaryPurple, CircleShape)
            ) {
                Icon(Icons.Default.PhotoCamera, contentDescription = null, tint = Color.White, modifier = Modifier.size(20.dp))
            }
        }
//
//        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
//            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, contentDescription = null) }
//            Text("Thông tin cá nhân", style = MaterialTheme.typography.titleLarge)
//        }

        Spacer(modifier = Modifier.height(32.dp))

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
        ProfileItem(Icons.Default.Lock, "Đổi mật khẩu")
        ProfileItem(Icons.Default.Language, "Ngôn ngữ")
        ProfileItem(Icons.Default.Notifications, "Lịch sử cảnh báo")

//        Spacer(modifier = Modifier.weight(1f))

        // Phần Settings đơn giản
//        SettingItem(Icons.Default.Lock, "Đổi mật khẩu")
//        SettingItem(Icons.Default.Language, "Ngôn ngữ")

        Spacer(modifier = Modifier.height(30.dp))

        // Các nút cài đặt khác
        Button(
            onClick = onLogout, // Gọi hàm logout đã định nghĩa ở AppNavigation
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
        ) {
            Text("Đăng xuất")
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