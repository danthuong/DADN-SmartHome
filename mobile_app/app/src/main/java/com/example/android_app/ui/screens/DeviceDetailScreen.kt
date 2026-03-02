package com.example.android_app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.dp
import com.example.android_app.data.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceDetailScreen(
    deviceId: String,
    onBack: () -> Unit
) {
    // Collect StateFlow để tự động update UI khi Cloud thay đổi
    val devices by SmartHomeRepository.devices.collectAsState()
    val device = devices.find { it.id == deviceId }

    if (device == null) {
        // Handle error or back
        Box(Modifier.fillMaxSize()) { Text("Device not found") }
        return
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(device.name) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, null) }
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
            // Nút nguồn chung
            Button(
                onClick = {
                    // Gửi lệnh lên Repo
                    if (device is SmartLight) SmartHomeRepository.updateLight(device.id, isOn = !device.isOn)
                    if (device is SmartFan) SmartHomeRepository.updateFan(device.id, isOn = !device.isOn)
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
                    is SmartLight -> LightControlPanel(device)
                    is SmartFan -> FanControlPanel(device)
                }
            } else {
                Text("Đang tắt", style = MaterialTheme.typography.titleMedium, color = Color.Gray)
            }
        }
    }
}

@Composable
fun LightControlPanel(light: SmartLight) {
    Column {
        Text("Độ sáng: ${(light.brightness).toInt()} Lux")
        Slider(
            value = light.brightness,
            onValueChange = { SmartHomeRepository.updateLight(light.id, brightness = it) }, // Gửi real-time
            valueRange = 0f..1000f // Giả lập Lux tối đa 1000
        )
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
                            if(light.color == color.toArgb()) Color.Black else Color.Transparent,
                            CircleShape
                        )
                        .clickable { SmartHomeRepository.updateLight(light.id, color = color.toArgb()) }
                )
            }
        }
    }
}

@Composable
fun FanControlPanel(fan: SmartFan) {
    Column {
        Text("Tốc độ gió: ${fan.speed.toInt()}")
        Slider(
            value = fan.speed,
            onValueChange = { SmartHomeRepository.updateFan(fan.id, speed = it) },
            valueRange = 1f..3f,
            steps = 1
        )
        Spacer(modifier = Modifier.height(16.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("Chế độ quay (Oscillation)")
            Switch(
                checked = fan.isOscillating,
                onCheckedChange = { SmartHomeRepository.updateFan(fan.id, isOscillating = it) }
            )
        }
    }
}