package com.example.android_app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Air
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.NightsStay
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
// Chú ý: Đảm bảo các file theme này đã tồn tại trong project của bạn
import com.example.android_app.ui.theme.BackgroundBlack
import com.example.android_app.ui.theme.CardGray
import com.example.android_app.ui.theme.PrimaryPurple
import com.example.android_app.utils.sendNotification
import java.util.Calendar

@Composable
fun DashboardHeader(userName: String, onProfileClick: () -> Unit) {
    val calendar = Calendar.getInstance()
    val hour = calendar.get(Calendar.HOUR_OF_DAY)
    // Chọn Icon theo giờ thực tế
    val weatherIcon = when (hour) {
        in 6..17 -> {
            Icons.Default.WbSunny // Ban ngày
        }

        else -> Icons.Default.NightsStay // Ban đêm
    }
    val weatherText = if (hour in 6..17) "Trời nắng" else "Trời quang"

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(180.dp),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = PrimaryPurple.copy(alpha = 0.9f))
    ) {
        Row(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text("CHÀO MỪNG ĐẾN SMART HOME", color = Color.White.copy(alpha = 0.8f))
                Text(userName, style = MaterialTheme.typography.headlineMedium, color = Color.White, fontWeight = FontWeight.Bold)

                Spacer(modifier = Modifier.height(16.dp))

                //Weather Row (Giả lập lấy từ cảm biến DHT20)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(weatherIcon, contentDescription = null, tint = Color.Yellow, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(weatherText, color = Color.White, style = MaterialTheme.typography.bodyMedium)
                }
            }

            // Avatar Người dùng
            IconButton(
                onClick = onProfileClick,
                modifier = Modifier.size(64.dp).background(Color.White.copy(alpha = 0.2f), CircleShape)
            ) {
                Icon(Icons.Default.Person, contentDescription = "Profile", tint = Color.White, modifier = Modifier.size(32.dp))
            }
        }
    }
}

@Composable
fun DashboardScreen(userName: String, onLogout: () -> Unit, onProfileClick: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding()
            .padding(16.dp)
    ) {
        DashboardHeader(userName = userName, onProfileClick = onProfileClick)

        Spacer(modifier = Modifier.height(24.dp))

        // Khu vực hiển thị thông số (Nhiệt độ/Ánh sáng)
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            SensorCard("Nhiệt độ", "28°C", modifier = Modifier.weight(1f))
            Spacer(modifier = Modifier.width(16.dp))
            SensorCard("Ánh sáng", "150 Lux", modifier = Modifier.weight(1f))
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text("THIẾT BỊ", color = Color.Gray, style = MaterialTheme.typography.labelMedium)
        Spacer(modifier = Modifier.height(8.dp))

        // Khu vực điều khiển thiết bị
        DeviceControlCard("Đèn", icon = Icons.Default.Lightbulb)
        Spacer(modifier = Modifier.height(16.dp))
        DeviceControlCard("Quạt", icon = Icons.Default.Air)

        Spacer(modifier = Modifier.height(30.dp))

        Button(
            onClick = { sendNotification(context, "Cảnh báo!", "Có người lạ trước cửa!") },
            colors = ButtonDefaults.buttonColors(containerColor = PrimaryPurple)
        ) {
            Text("Test Notification")
        }
    }
}

@Composable
fun SensorCard(title: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f), style = MaterialTheme.typography.bodySmall)
            Text(value, color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.headlineMedium)
        }
    }
}

@Composable
fun DeviceControlCard(name: String, icon: ImageVector) {
    // Sửa lỗi: Cần import androidx.compose.runtime.setValue để dùng 'by'
    var isOn by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant )
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (isOn) PrimaryPurple else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Text(name, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
            Switch(
                checked = isOn,
                onCheckedChange = { isOn = it },
                colors = SwitchDefaults.colors(
                    // Khi đang BẬT
                    checkedThumbColor = Color.White,           // Nút tròn màu trắng (cho nổi bật)
                    checkedTrackColor = PrimaryPurple, // Thanh trượt màu tím/xanh đậm

                    // Khi đang TẮT
                    uncheckedThumbColor = Color.Gray,          // Nút tròn màu xám
                    uncheckedTrackColor = Color.LightGray.copy(alpha = 0.5f), // Thanh trượt xám nhạt

                    // Màu viền khi tắt (tùy chọn)
                    uncheckedBorderColor = Color.Gray
                )
            )
        }
    }
}