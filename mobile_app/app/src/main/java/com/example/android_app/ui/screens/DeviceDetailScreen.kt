@file:OptIn(ExperimentalMaterial3Api::class)
package com.example.android_app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.dp
import com.example.android_app.data.SmartDevice
import com.example.android_app.data.SmartFan
import com.example.android_app.data.SmartHomeRepository
import com.example.android_app.data.SmartLight

@Composable
fun DeviceDetailScreen(
    device: SmartDevice,
    strings: com.example.android_app.utils.AppStrings,
    onBack: () -> Unit
) {
    var localBrightness by remember(device.id) { mutableFloatStateOf(if (device is SmartLight) device.brightness else 0f) }
    var localSpeed by remember(device.id) { mutableFloatStateOf(if (device is SmartFan) device.speed else 1f) }
    var localOscillating by remember(device.id) { mutableStateOf(if (device is SmartFan) device.isOscillating else false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(device.name) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.PowerSettingsNew, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Nút nguồn chung
            Button(
                onClick = {
                    if (device is SmartLight) {
                        SmartHomeRepository.updateLight(device.id, isOn = !device.isOn)
                        SmartHomeRepository.syncLightToServer(device.id, isOn = !device.isOn)
                    }
                    if (device is SmartFan) {
                        SmartHomeRepository.updateFan(device.id, isOn = !device.isOn)
                        SmartHomeRepository.syncFanToServer(device.id, isOn = !device.isOn)
                    }
                },
                shape = CircleShape,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (device.isOn) MaterialTheme.colorScheme.primary else Color.Gray
                ),
                modifier = Modifier.size(100.dp)
            ) {
                Icon(Icons.Default.PowerSettingsNew, null, modifier = Modifier.size(48.dp))
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Điều khiển chi tiết
            if (device.isOn) {
                when (device) {
                    is SmartLight -> LightControlPanelLocal(
                        currentBrightness = device.brightness,
                        currentColor = device.color,
                        onBrightnessChange = { localBrightness = it },
                        onSave = {
                            SmartHomeRepository.updateLight(device.id, brightness = localBrightness)
                            SmartHomeRepository.syncLightToServer(device.id, brightness = localBrightness)
                        },
                        onColorSelect = { color ->
                            SmartHomeRepository.updateLight(device.id, color = color.toArgb())
                            SmartHomeRepository.syncLightToServer(device.id, color = color.toArgb())
                        }
                    )
                    is SmartFan -> FanControlPanelLocal(
                        currentSpeed = device.speed,
                        currentOscillating = device.isOscillating,
                        onSpeedChange = { localSpeed = it },
                        onOscillatingChange = { localOscillating = it },
                        onSave = {
                            SmartHomeRepository.updateFan(device.id, speed = localSpeed, isOscillating = localOscillating)
                            SmartHomeRepository.syncFanToServer(device.id, speed = localSpeed, isOscillating = localOscillating)
                        }
                    )
                }
            } else {
                Text("Đang tắt", style = MaterialTheme.typography.titleMedium, color = Color.Gray)
            }
        }
    }
}

@Composable
fun LightControlPanelLocal(
    currentBrightness: Float,
    currentColor: Int,
    onBrightnessChange: (Float) -> Unit,
    onSave: () -> Unit,
    onColorSelect: (Color) -> Unit
) {
    var localBrightness by remember { mutableFloatStateOf(currentBrightness) }

    Column {
        Text("Độ sáng: ${localBrightness.toInt()} Lux")
        Slider(
            value = localBrightness,
            onValueChange = { localBrightness = it },
            valueRange = 0f..1000f
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Button(
            onClick = {
                onBrightnessChange(localBrightness)
                onSave()
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Lưu độ sáng")
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text("Màu sắc")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(Color.White, Color.Yellow, Color.Red, Color.Blue).forEach { color ->
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(color)
                        .border(
                            2.dp,
                            if(currentColor == color.toArgb()) Color.Black else Color.Transparent,
                            CircleShape
                        )
                        .clickable { onColorSelect(color) }
                )
            }
        }
    }
}

@Composable
fun FanControlPanelLocal(
    currentSpeed: Float,
    currentOscillating: Boolean,
    onSpeedChange: (Float) -> Unit,
    onOscillatingChange: (Boolean) -> Unit,
    onSave: () -> Unit
) {
    var localSpeed by remember { mutableFloatStateOf(currentSpeed) }
    var localOscillating by remember { mutableStateOf(currentOscillating) }

    @Composable
    fun FanControlPanelLocal(
        currentSpeed: Float,
        currentOscillating: Boolean,
        onSpeedChange: (Float) -> Unit,
        onOscillatingChange: (Boolean) -> Unit,
        onSave: () -> Unit
    ) {
        var localSpeed by remember { mutableFloatStateOf(currentSpeed) }
        var localOscillating by remember { mutableStateOf(currentOscillating) }

        Column {
            Text("Tốc độ gió: ${localSpeed.toInt()}")
            Slider(
                value = localSpeed,
                onValueChange = { localSpeed = it },
                valueRange = 1f..3f,
                steps = 1
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = {
                    onSpeedChange(localSpeed)
                    onOscillatingChange(localOscillating)
                    onSave()
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Lưu cài đặt")
            }

            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text("Chế độ quay (Oscillation)")
                Switch(
                    checked = localOscillating,
                    onCheckedChange = { localOscillating = it }
                )
            }
        }
    }
}