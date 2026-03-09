package com.example.android_app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.android_app.data.*
import com.example.android_app.utils.AppStrings

@Composable
fun PresetEditSheet(
    preset: Preset,
    selectedRoom: String, // Nhận vào phòng hiện tại để lọc thiết bị
    strings: AppStrings,
    onDismiss: () -> Unit
) {
    // --- 1. LOCAL STATE ĐỂ LƯU THÔNG TIN CHỈNH SỬA ---
    var editedName by remember { mutableStateOf(preset.name) }
    var selectedIcon by remember { mutableStateOf(preset.icon) }
    // Tạo một bản sao của Map cấu hình cũ để chỉnh sửa mà không ảnh hưởng data gốc ngay lập tức
    val editedConfigs = remember {
        mutableStateMapOf<String, DeviceConfig>().apply { putAll(preset.deviceConfigs) }
    }

    // Lấy danh sách thiết bị thuộc phòng hiện tại từ Repository
    val allDevices by SmartHomeRepository.devices.collectAsState()
    val devicesInRoom = allDevices.filter { it.roomID == selectedRoom }

    var showEmojiPicker by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .fillMaxHeight(0.8f) // Chiếm 80% màn hình
            .padding(horizontal = 20.dp, vertical = 8.dp)
    ) {
        Text(strings.createPreset, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)

        Spacer(modifier = Modifier.height(20.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Ô CHỌN ICON (Bên trái)
            Surface(
                onClick = { showEmojiPicker = !showEmojiPicker },
                modifier = Modifier
                    .size(56.dp)
                    .clip(RoundedCornerShape(12.dp)),
                color = MaterialTheme.colorScheme.surfaceVariant,
                border = if (showEmojiPicker) BorderStroke(4.dp, MaterialTheme.colorScheme.primary) else null
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(text = selectedIcon, fontSize = 28.sp)
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Ô NHẬP TÊN (Bên phải)
            OutlinedTextField(
                value = editedName,
                onValueChange = { editedName = it },
                label = { Text(strings.enterPresetName) },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp),
                singleLine = true
            )
        }

        AnimatedVisibility(visible = showEmojiPicker) {
            Column {
                Spacer(modifier = Modifier.height(16.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp) // Giới hạn chiều cao để không choán hết chỗ chọn thiết bị
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f), RoundedCornerShape(16.dp))
                        .padding(8.dp)
                ) {
                    EmojiPickerGrid(
                        selectedIcon = selectedIcon,
                        strings = strings,
                        onIconSelected = {
                            selectedIcon = it
                            showEmojiPicker = false // Chọn xong tự đóng lại cho gọn
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "${strings.devicesIn} $selectedRoom",
            style = MaterialTheme.typography.labelLarge,
            color = Color.Gray
        )

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(devicesInRoom) { device ->
                // Kiểm tra xem thiết bị này có đang nằm trong Preset không
                val currentConfig = editedConfigs[device.id]

                DeviceSelectionCard(
                    device = device,
                    displayName = device.name,
                    strings = strings,
                    currentConfig = currentConfig,
                    onConfigChanged = { newConfig ->
                        if (newConfig == null) {
                            editedConfigs.remove(device.id) // Bỏ thiết bị khỏi preset
                        } else {
                            editedConfigs[device.id] = newConfig // Cập nhật cấu hình mới
                        }
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // --- NÚT LƯU THAY ĐỔI ---
        Button(
            onClick = {
                if (editedName.isNotEmpty()) {
                    // Tạo object Preset mới với thông tin đã sửa
                    val updatedPreset = preset.copy(
                        name = editedName,
                        deviceConfigs = editedConfigs.toMap(),
                        roomID = selectedRoom
                    )
                    // Lưu vào Repository
                    SmartHomeRepository.savePreset(updatedPreset)
                    onDismiss()
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
        ) {
            Text(strings.save, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        }

        Spacer(modifier = Modifier.height(8.dp))
    }
}