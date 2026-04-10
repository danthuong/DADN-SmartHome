package com.example.android_app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Air
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Cyclone
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.ModeFanOff
import androidx.compose.material.icons.filled.Storm
import androidx.compose.material.icons.filled.WindPower
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.android_app.data.DeviceType
import com.example.android_app.data.SmartDevice
import com.example.android_app.data.SmartFan
import com.example.android_app.data.SmartHomeRepository
import com.example.android_app.data.SmartLight
import com.example.android_app.utils.AppStrings

@Composable
fun EditDeviceSheet(
    device: SmartDevice,
    strings: AppStrings,
    onDismiss: () -> Unit
) {
    // --- 1. LOCAL STATES ---
    var localBrightness by remember(device.id) { mutableFloatStateOf(if (device is SmartLight) device.brightness else 0f) }
    var localSpeed by remember(device.id) { mutableFloatStateOf(if (device is SmartFan) device.speed else 1f) }
    var localOscillating by remember(device.id) { mutableStateOf(if (device is SmartFan) device.isOscillating else false) }
    var localTracking by remember(device.id) { mutableStateOf(if (device is SmartFan) device.isTracking else false) }

    // State màu sắc
    var localColor by remember(device.id) {
        mutableStateOf(if (device is SmartLight) Color(device.color) else Color.White)
    }

    var isEditingName by remember { mutableStateOf(false) }
    var currentName by remember { mutableStateOf(device.name) }

    Column(
        modifier = Modifier.fillMaxWidth().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // --- PHẦN ICON HIỂN THỊ ĐỘNG ---
        val displayColor = if (device is SmartLight) localColor else MaterialTheme.colorScheme.primary

        // 2. TÍNH TOÁN ĐỘ CHÓI (Alpha) DỰA TRÊN ĐỘ SÁNG (0.2 là tối thiểu để vẫn nhìn thấy icon)
        val brightnessAlpha = if (device is SmartLight) (localBrightness / 100f).coerceAtLeast(0.2f) else 1f

        Box(contentAlignment = Alignment.Center) {
            // 1. VÒNG TRÒN XUNG QUANH (Đổi màu theo localColor)
            Surface(
                modifier = Modifier.size(120.dp),
                shape = CircleShape,
                color = displayColor.copy(alpha = 0.15f * brightnessAlpha) // Vòng tròn cũng mờ tỏ theo độ sáng
            ) {}

            // ICON CHÍNH
            if (device is SmartLight) {
                Icon(
                    imageVector = Icons.Default.Lightbulb,
                    contentDescription = null,
                    modifier = Modifier.size(60.dp),
                    // 2. ICON ĐỔI MÀU VÀ ĐỘ CHÓI LẬP TỨC
                    tint = localColor.copy(alpha = brightnessAlpha)
                )
            } else {
                Icon(
                    imageVector = Icons.Default.WindPower,
                    contentDescription = null,
                    modifier = Modifier.size(60.dp),
                    tint = if (device.isOn) MaterialTheme.colorScheme.primary else Color.Gray
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
            modifier = Modifier.fillMaxWidth().height(60.dp)
        ) {
            if (isEditingName) {
                OutlinedTextField(
                    value = currentName,
                    onValueChange = { currentName = it },
                    modifier = Modifier.width(200.dp),
                    singleLine = true,
                    textStyle = MaterialTheme.typography.bodyLarge,
                    shape = RoundedCornerShape(12.dp)
                )
                IconButton(onClick = {
                    SmartHomeRepository.renameDevice(device.id, currentName)
                    isEditingName = false
                }) { Icon(Icons.Default.Check, null) }
            } else {
                Text(
                    text = currentName,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                // 2. ICON RENAME
                IconButton(onClick = { isEditingName = true }, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Edit, contentDescription = strings.rename , modifier = Modifier.size(18.dp))
                }
            }
        }
//        Text(text = device.name, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)

        Spacer(modifier = Modifier.height(16.dp))

        // Hiển thị mức độ gió bằng text/icon phụ (Mục 3)
        if (device is SmartFan) {
            Row(
                modifier = Modifier.padding(top = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                repeat(3) { index ->
                    Box(
                        modifier = Modifier
                            .width(30.dp)
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(
                                if (localSpeed.toInt() > index) MaterialTheme.colorScheme.primary
                                else Color.LightGray.copy(alpha = 0.5f)
                            )
                    )
                }
            }
        }

//        Row(
//            verticalAlignment = Alignment.CenterVertically,
//            horizontalArrangement = Arrangement.Center,
//            modifier = Modifier.fillMaxWidth().height(60.dp)
//        ) {
//            if (isEditingName) {
//                OutlinedTextField(
//                    value = currentName,
//                    onValueChange = { currentName = it },
//                    modifier = Modifier.width(200.dp),
//                    singleLine = true,
//                    textStyle = MaterialTheme.typography.bodyLarge,
//                    shape = RoundedCornerShape(12.dp)
//                )
//                IconButton(onClick = {
//                    SmartHomeRepository.renameDevice(device.id, currentName)
//                    isEditingName = false
//                }) { Icon(Icons.Default.Check, null) }
//            } else {
//                Text(
//                    text = currentName,
//                    style = MaterialTheme.typography.headlineSmall,
//                    fontWeight = FontWeight.Bold,
//                    color = MaterialTheme.colorScheme.onSurface
//                )
//                // 2. ICON RENAME
//                IconButton(onClick = { isEditingName = true }, modifier = Modifier.size(32.dp)) {
//                    Icon(Icons.Default.Edit, contentDescription = strings.rename , modifier = Modifier.size(18.dp))
//                }
//            }
//        }

        // --- ĐIỀU KHIỂN CHI TIẾT ---
        if (device is SmartLight) {
            Text("${strings.brightness}: ${localBrightness.toInt()}%", modifier = Modifier.align(Alignment.Start))
            Slider(
                value = localBrightness,
                onValueChange = {
                    localBrightness = it
                    SmartHomeRepository.updateLight(
                        device.id,
                        brightness = it,
                        isOn = it > 0f
                    )
                },
                valueRange = 0f..100f
            )

            Spacer(modifier = Modifier.height(16.dp))
            Text(strings.color, modifier = Modifier.align(Alignment.Start))

            RainbowColorPicker(
                selectedColor = localColor,
                onColorSelected = { newColor ->
                    localColor = newColor
                    SmartHomeRepository.updateLight(device.id, color = newColor.toArgb())
                }
            )
        }

        if (device is SmartFan) {
            Text("${strings.speed}: ${localSpeed.toInt()}", modifier = Modifier.align(Alignment.Start))
            Slider(
                value = localSpeed,
                onValueChange = {
                    localSpeed = it
                    SmartHomeRepository.updateFan(device.id, speed = it)
                },
                valueRange = 1f..3f,
                steps = 1
            )

            Spacer(modifier = Modifier.height(16.dp))
            ToggleSettingRow(strings.osc, localOscillating) {
                localOscillating = it
                SmartHomeRepository.updateFan(device.id, isOscillating = it)
            }
            ToggleSettingRow(strings.track, localTracking) {
                localTracking = it
                SmartHomeRepository.updateFan(device.id, isTracking = it)
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
        Button(onClick = onDismiss, modifier = Modifier.fillMaxWidth().height(56.dp)) {
            Text(strings.save)
        }
    }
}

@Composable
fun ToggleSettingRow(title: String, isChecked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(title, style = MaterialTheme.typography.bodyLarge)
        Switch(checked = isChecked, onCheckedChange = onCheckedChange)
    }
}