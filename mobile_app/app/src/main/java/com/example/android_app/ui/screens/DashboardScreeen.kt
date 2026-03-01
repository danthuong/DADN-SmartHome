package com.example.android_app.ui.screens

import android.content.Context
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
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
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.android_app.data.User
import com.example.android_app.ui.theme.PrimaryPurple
import com.example.android_app.utils.sendNotification
import java.util.Calendar
import coil.compose.AsyncImage
import com.example.android_app.utils.AppStrings

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    user: User,
    strings: AppStrings,
    onLogout: () -> Unit,
    onProfileClick: () -> Unit,
    onSettingsClick: () -> Unit // Thêm callback cho settings
) {
    val context = LocalContext.current
    val sharedPref = remember { context.getSharedPreferences("UserPrefs", Context.MODE_PRIVATE) }

    // Đọc Avatar từ SharedPreferences (Đảm bảo đồng bộ khi quay lại từ Profile)
    val savedAvatarUri = sharedPref.getString("avatar_uri", null)?.let { Uri.parse(it) }

    // Logic thời tiết dựa trên giờ hệ thống
    val calendar = Calendar.getInstance()
    val hour = calendar.get(Calendar.HOUR_OF_DAY)
    val weatherIcon = if (hour in 6..17) Icons.Default.WbSunny else Icons.Default.NightsStay
    val weatherText = if (hour in 6..17) strings.sun else strings.clear

    // Danh sách phòng giả lập (Mục 8)
    val rooms = listOf(strings.roomLiving, strings.roomBed, strings.roomKitchen, strings.Garden)
    var selectedRoom by remember { mutableStateOf(strings.roomLiving) }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding(),
        // 7. Thanh công cụ phía trên (Top Bar)
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("YOLO HOME", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold) },
                navigationIcon = {
                    IconButton(onClick = onProfileClick) {
                        if (savedAvatarUri != null) {
                            // Nếu đã có ảnh
                            coil.compose.AsyncImage(
                                model = savedAvatarUri,
                                contentDescription = strings.profileAva,
                                modifier = Modifier
                                    .size(36.dp) // Tăng nhẹ kích thước cho dễ nhìn
                                    .clip(CircleShape),
                                contentScale = ContentScale.Crop
                            )
                        } else {
                            // NẾU CHƯA CÓ ẢNH - FIX LỖI Ở ĐÂY
                            Surface(
                                modifier = Modifier.size(36.dp),
                                shape = CircleShape,
                                color = MaterialTheme.colorScheme.surfaceVariant // Màu xám nhạt/tối tùy theme
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Person,
                                    contentDescription = null,
                                    // CHỈ để padding nhỏ (ví dụ 6.dp) để icon nằm gọn trong vòng tròn
                                    modifier = Modifier.padding(6.dp),
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                },
                actions = {
                    // Nút Settings ở góc phải phía trên
                    IconButton(onClick = onSettingsClick) {
                        Icon(Icons.Default.Settings, contentDescription = null)
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        // 9. Nút '+' hình tròn ở giữa cuối màn hình
        floatingActionButton = {
            FloatingActionButton(
                onClick = { /* Logic thêm thiết bị */ },
                shape = CircleShape,
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.surface
            ) {
                Icon(Icons.Default.Add, contentDescription = null)
            }
        },
        floatingActionButtonPosition = FabPosition.Center
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .statusBarsPadding()
                .background(MaterialTheme.colorScheme.background)
                .padding(horizontal = 16.dp)
        ) {
            // 1. Card Welcome mới (Gọn gàng hơn)
            Card(
                modifier = Modifier.fillMaxWidth().height(140.dp),
                shape = RoundedCornerShape(28.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(strings.welcome, style = MaterialTheme.typography.bodyLarge)
                    Text(user.fullName, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(weatherIcon, contentDescription = null, tint = Color(0xFFFFB300), modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("28°C - $weatherText", style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // 8. Lựa chọn gian phòng (LazyRow)
            Text(strings.room, color = Color.Gray, style = MaterialTheme.typography.labelLarge)
            Spacer(modifier = Modifier.height(8.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                items(rooms) { room ->
                    FilterChip(
                        selected = selectedRoom == room,
                        onClick = { selectedRoom = room },
                        label = { Text(room) },
                        shape = RoundedCornerShape(20.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Thông số cảm biến (Cố định hoặc lọc theo phòng)
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                SensorCard(strings.temp, "28°C", modifier = Modifier.weight(1f))
                Spacer(modifier = Modifier.width(16.dp))
                SensorCard(strings.lit, "150 Lux", modifier = Modifier.weight(1f))
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text("${strings.devicesIn} ${selectedRoom.uppercase()}", color = Color.Gray, style = MaterialTheme.typography.labelLarge)
            Spacer(modifier = Modifier.height(12.dp))

            // 1. Sửa lỗi Card Device không đổi màu (Dùng surfaceVariant)
            DeviceControlCard(strings.led, icon = Icons.Default.Lightbulb)
            Spacer(modifier = Modifier.height(12.dp))
            DeviceControlCard(strings.fan, icon = Icons.Default.Air)
        }
    }
}

@Composable
fun SensorCard(title: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), // Đổi màu card đồng bộ
        shape = RoundedCornerShape(20.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f), fontSize = 12.sp)
            Text(value, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
fun DeviceControlCard(name: String, icon: ImageVector) {
    var isOn by remember { mutableStateOf(false) }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Icon tự đổi màu theo theme và trạng thái
            Icon(
                icon,
                contentDescription = null,
                tint = if (isOn) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                modifier = Modifier.size(28.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))
            Text(name, modifier = Modifier.weight(1f), fontWeight = FontWeight.Medium)

            // Switch tự đổi màu thumb trắng cho nổi bật
            Switch(
                checked = isOn,
                onCheckedChange = { isOn = it },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.White,
                    checkedTrackColor = MaterialTheme.colorScheme.primary
                )
            )
        }
    }
}