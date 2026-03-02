package com.example.android_app.ui.screens

import android.content.Context
import android.net.Uri
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.android_app.data.*
import com.example.android_app.utils.AppStrings
import java.util.Calendar

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    user: User,
    strings: AppStrings,
    onLogout: () -> Unit,
    onProfileClick: () -> Unit,
    onSettingsClick: () -> Unit,
    onDeviceClick: (String) -> Unit, // Callback mở chi tiết thiết bị
    onNavigateToCreatePreset: () -> Unit, // Callback mở màn hình tạo Preset
    onNavigateToEditPreset: (String) -> Unit
) {
    val context = LocalContext.current
    val sharedPref = remember { context.getSharedPreferences("UserPrefs", Context.MODE_PRIVATE) }
    val savedAvatarUri = sharedPref.getString("avatar_uri", null)?.let { Uri.parse(it) }

    // --- LẤY DỮ LIỆU TỪ REPOSITORY (REAL-TIME) ---
    // Bất cứ thay đổi nào từ Repo (do cloud trả về hoặc user thao tác) đều cập nhật vào 2 biến này
    val devices by SmartHomeRepository.devices.collectAsState()
    val presets by SmartHomeRepository.presets.collectAsState()
    val activePresetId by SmartHomeRepository.activePresetId.collectAsState()

    // Logic thời tiết & Phòng (Giữ nguyên)
    val calendar = Calendar.getInstance()
    val hour = calendar.get(Calendar.HOUR_OF_DAY)
    val weatherIcon = if (hour in 6..17) Icons.Default.WbSunny else Icons.Default.NightsStay
    val weatherText = if (hour in 6..17) strings.sun else strings.clear
    val rooms = listOf(strings.roomLiving, strings.roomBed, strings.roomKitchen, strings.Garden)
    var selectedRoom by remember { mutableStateOf(strings.roomLiving) }

    Scaffold(
        modifier = Modifier.fillMaxSize().statusBarsPadding(),
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("YOLO HOME", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold) },
                navigationIcon = {
                    IconButton(onClick = onProfileClick) {
                        if (savedAvatarUri != null) {
                            AsyncImage(
                                model = savedAvatarUri,
                                contentDescription = strings.profileAva,
                                modifier = Modifier.size(36.dp).clip(CircleShape),
                                contentScale = ContentScale.Crop
                            )
                        } else {
                            Surface(modifier = Modifier.size(36.dp), shape = CircleShape, color = MaterialTheme.colorScheme.surfaceVariant) {
                                Icon(Icons.Default.Person, null, modifier = Modifier.padding(6.dp), tint = MaterialTheme.colorScheme.primary)
                            }
                        }
                    }
                },
                actions = {
                    IconButton(onClick = onSettingsClick) {
                        Icon(Icons.Default.Settings, contentDescription = null)
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(horizontal = 16.dp)
        ) {
            // 1. WELCOME CARD (Giữ nguyên)
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

            Spacer(modifier = Modifier.height(16.dp))

            // 2. ROOM FILTER & SENSORS (Giữ nguyên UI)
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
            Spacer(modifier = Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                SensorCard(strings.temp, "28°C", modifier = Modifier.weight(1f))
                Spacer(modifier = Modifier.width(16.dp))
                SensorCard(strings.lit, "150 Lux", modifier = Modifier.weight(1f))
            }

            Spacer(modifier = Modifier.height(24.dp))

            // ---------------------------------------------------------
            // 3. KHU VỰC PRESET (SCENES)
            // ---------------------------------------------------------
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(strings.presets, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onBackground)

                // Nút Add nhỏ gọn nằm ngang hàng
                IconButton(onClick = onNavigateToCreatePreset) {
                    Icon(
                        imageVector = Icons.Default.Add,
                        contentDescription = "Add Preset",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                items(presets) { preset ->
                    PresetCard(
                        preset = preset,
                        isActive = preset.id == activePresetId,
                        onClick = { SmartHomeRepository.togglePreset(preset.id) },
                        onLongClick = { onNavigateToEditPreset(preset.id) }
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // ---------------------------------------------------------
            // 4. KHU VỰC DANH SÁCH THIẾT BỊ - MỚI
            // ---------------------------------------------------------
            Text(strings.devices, style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))

            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(devices) { device ->
                    // Logic đặt tên hiển thị:
                    // Nếu device.name rỗng hoặc mặc định -> Dùng strings + số ID
                    // Ở đây demo cách ghép chuỗi đơn giản
                    val displayName = when(device.type) {
                        DeviceType.LIGHT -> "${strings.led} ${device.id.takeLast(1)}"
                        DeviceType.FAN -> "${strings.fan} ${device.id.takeLast(1)}"
                    }

                    DeviceItemCard(
                        device = device,
                        displayName = displayName, // Truyền tên đã dịch
                        strings = strings,
                        onClick = { onDeviceClick(device.id) }
                    )
                }
            }
        }
    }
}

// --- CÁC COMPOSABLE CON ---

@Composable
fun SensorCard(title: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        shape = RoundedCornerShape(20.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f), fontSize = 12.sp)
            Text(value, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun PresetCard(
    preset: Preset,
    isActive: Boolean,
    onClick: () -> Unit,
    onLongClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .size(width = 120.dp, height = 80.dp)
            .combinedClickable(
                onClick = onClick,
                onLongClick = onLongClick
            ),
        colors = CardDefaults.cardColors(
            // Đổi màu nếu đang Active
            containerColor = if(isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(preset.icon, style = MaterialTheme.typography.headlineSmall)
            Text(
                preset.name,
                style = MaterialTheme.typography.bodyMedium,
                color = if(isActive) Color.White else MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceItemCard(
    device: SmartDevice,
    displayName: String,
    strings: AppStrings,
    onClick: () -> Unit
) {
    // Xác định icon dựa trên loại thiết bị
    val icon = when(device) {
        is SmartLight -> Icons.Default.Lightbulb
        is SmartFan -> Icons.Default.Air
    }

    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Icon đổi màu theo trạng thái On/Off
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (device.isOn) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                modifier = Modifier.size(28.dp)
            )
            Spacer(modifier = Modifier.width(16.dp))

            Column(modifier = Modifier.weight(1f)) {
                // SỬ DỤNG displayName THAY VÌ device.name
                Text(displayName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

                // Hiển thị thông tin phụ (Dùng strings để lấy từ khóa đa ngôn ngữ)
                val statusText = if (!device.isOn) "Off" else when (device) {
                    is SmartLight -> "${strings.brightness}: ${device.brightness.toInt()}"
                    is SmartFan -> "${strings.speed}: ${device.speed.toInt()}"
                }
                Text(statusText, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            }

            // Switch toggle nhanh -> Gọi Repository update
            Switch(
                checked = device.isOn,
                onCheckedChange = { isChecked ->
                    when (device) {
                        is SmartLight -> SmartHomeRepository.updateLight(device.id, isOn = isChecked)
                        is SmartFan -> SmartHomeRepository.updateFan(device.id, isOn = isChecked)
                    }
                },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.White,
                    checkedTrackColor = MaterialTheme.colorScheme.primary
                )
            )
        }
    }
}