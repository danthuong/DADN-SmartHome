package com.example.android_app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Save
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.dp
import com.example.android_app.data.*
import com.example.android_app.utils.AppStrings
import java.util.UUID

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreatePresetScreen(
    strings: AppStrings,
    presetIdToEdit: String? = null, // Nếu null là tạo mới, có ID là sửa
    onBack: () -> Unit
) {
    val allDevices by SmartHomeRepository.devices.collectAsState()

    // Load dữ liệu cũ nếu là chế độ Edit
    val existingPreset = remember(presetIdToEdit) {
        if (presetIdToEdit != null) SmartHomeRepository.getPresetById(presetIdToEdit) else null
    }

    var presetName by remember { mutableStateOf(existingPreset?.name ?: "") }

    // Map cấu hình
    val selectedConfigs = remember {
        mutableStateMapOf<String, DeviceConfig>().apply {
            // Nếu edit, load config cũ vào map
            existingPreset?.deviceConfigs?.let { putAll(it) }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (presetIdToEdit == null) strings.createPreset else strings.editPreset) },
                actions = {
                    IconButton(onClick = {
                        if (presetName.isNotEmpty() && selectedConfigs.isNotEmpty()) {
                            val presetToSave = Preset(
                                id = presetIdToEdit ?: UUID.randomUUID().toString(), // Giữ ID nếu edit
                                name = presetName,
                                deviceConfigs = selectedConfigs.toMap()
                            )
                            SmartHomeRepository.savePreset(presetToSave)
                            onBack()
                        }
                    }) {
                        Icon(Icons.Default.Save, contentDescription = "Save")
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).padding(16.dp)) {
            OutlinedTextField(
                value = presetName,
                onValueChange = { presetName = it },
                label = { Text(strings.enterPresetName) },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(16.dp))

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(allDevices) { device ->
                    val displayName = when(device.type) {
                        DeviceType.LIGHT -> "${strings.led} ${device.id.takeLast(1)}"
                        DeviceType.FAN -> "${strings.fan} ${device.id.takeLast(1)}"
                    }

                    DeviceSelectionCard(
                        device = device,
                        displayName = displayName,
                        strings = strings,
                        currentConfig = selectedConfigs[device.id],
                        onConfigChanged = { newConfig ->
                            if (newConfig == null) selectedConfigs.remove(device.id)
                            else selectedConfigs[device.id] = newConfig
                        }
                    )
                }
            }
        }
    }
}

@Composable
fun DeviceSelectionCard(
    device: SmartDevice,
    displayName: String,
    strings: AppStrings,
    currentConfig: DeviceConfig?,
    onConfigChanged: (DeviceConfig?) -> Unit
) {
    val isSelected = currentConfig != null

    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
        ),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = isSelected,
                    onCheckedChange = { checked ->
                        if (checked) {
                            // Default config khi tick chọn
                            val default = when(device) {
                                is SmartLight -> LightConfig(true, 50f, Color.White.toArgb())
                                is SmartFan -> FanConfig(true, 1f, false)
                            }
                            onConfigChanged(default)
                        } else {
                            onConfigChanged(null)
                        }
                    }
                )
                Text(displayName, style = MaterialTheme.typography.titleMedium)
            }

            if (isSelected && currentConfig != null) {
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                when {
                    device is SmartLight && currentConfig is LightConfig -> {
                        // 1. Chỉnh độ sáng
                        Text("${strings.brightness}: ${currentConfig.brightness.toInt()}%")
                        Slider(
                            value = currentConfig.brightness,
                            onValueChange = { onConfigChanged(currentConfig.copy(brightness = it)) },
                            valueRange = 0f..100f
                        )

                        // 2. Chỉnh màu (Rainbow Slider)
                        Text(strings.color)
                        Spacer(modifier = Modifier.height(4.dp))
                        RainbowColorPicker(
                            selectedColor = Color(currentConfig.color),
                            onColorSelected = { onConfigChanged(currentConfig.copy(color = it.toArgb())) }
                        )
                    }
                    device is SmartFan && currentConfig is FanConfig -> {
                        Text("${strings.speed}: ${currentConfig.speed.toInt()}")
                        Slider(
                            value = currentConfig.speed,
                            onValueChange = { onConfigChanged(currentConfig.copy(speed = it)) },
                            valueRange = 1f..3f,
                            steps = 1
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(strings.osc)
                            Switch(
                                checked = currentConfig.isOscillating,
                                onCheckedChange = { onConfigChanged(currentConfig.copy(isOscillating = it)) }
                            )
                        }
                    }
                }
            }
        }
    }
}

// Custom Component: Thanh trượt chọn màu full spectrum
@Composable
fun RainbowColorPicker(
    selectedColor: Color,
    onColorSelected: (Color) -> Unit
) {
    // Gradient 7 màu cầu vồng
    val rainbowColors = listOf(
        Color.Red, Color(0xFFFF7F00), Color.Yellow, Color.Green,
        Color.Blue, Color(0xFF4B0082), Color(0xFF8B00FF)
    )
    val brush = Brush.horizontalGradient(rainbowColors)

    // Dùng Slider để chọn Hue (giả lập đơn giản)
    // Thực tế để chính xác cần HSL/HSV conversion, nhưng ở đây ta map vị trí Slider vào danh sách màu
    var sliderPos by remember { mutableStateOf(0f) }

    Column {
        // Hiển thị màu đang chọn
        Box(
            modifier = Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(selectedColor)
                .align(Alignment.CenterHorizontally)
        )

        Spacer(modifier = Modifier.height(4.dp))

        // Thanh trượt
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(10.dp)
                .clip(RoundedCornerShape(5.dp))
                .background(brush)
        )

        Slider(
            value = sliderPos,
            onValueChange = { pos ->
                sliderPos = pos
                // Logic nội suy màu đơn giản
                val index = (pos * (rainbowColors.size - 1)).toInt()
                val nextIndex = (index + 1).coerceAtMost(rainbowColors.size - 1)
                val fraction = (pos * (rainbowColors.size - 1)) - index

                // Trộn màu giữa 2 điểm
                val color = androidx.compose.ui.graphics.lerp(
                    rainbowColors[index],
                    rainbowColors[nextIndex],
                    fraction
                )
                onColorSelected(color)
            },
            valueRange = 0f..1f,
            modifier = Modifier.offset(y = (-12).dp) // Kéo Slider đè lên thanh màu
        )
    }
}