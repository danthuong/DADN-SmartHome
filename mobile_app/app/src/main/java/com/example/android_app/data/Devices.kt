package com.example.android_app.data

import java.util.UUID

// Enum loại thiết bị
enum class DeviceType { LIGHT, FAN }

// --- 1. MODEL CHO THIẾT BỊ (STATE HIỆN TẠI) ---
sealed class SmartDevice(
    open val id: String,
    open val name: String,
    open val type: DeviceType,
    open val isOn: Boolean
)

data class SmartLight(
    override val id: String,
    override val name: String,
    override val isOn: Boolean,
    val brightness: Float, // 0-100
    val color: Int         // Color Int
) : SmartDevice(id, name, DeviceType.LIGHT, isOn)

data class SmartFan(
    override val id: String,
    override val name: String,
    override val isOn: Boolean,
    val speed: Float,      // 1-3
    val isOscillating: Boolean
) : SmartDevice(id, name, DeviceType.FAN, isOn)


// --- 2. MODEL CHO PRESET (CẤU HÌNH MONG MUỐN) ---
// Config chung
sealed interface DeviceConfig

// Config lưu settings cho đèn
data class LightConfig(
    val isOn: Boolean,
    val brightness: Float,
    val color: Int
) : DeviceConfig

// Config lưu settings cho quạt
data class FanConfig(
    val isOn: Boolean,
    val speed: Float,
    val isOscillating: Boolean
) : DeviceConfig

// Một Preset chứa tên và Map: ID thiết bị -> Cấu hình muốn áp dụng
data class Preset(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val icon: String = "✨",
    // Map<DeviceId, Config>
    val deviceConfigs: Map<String, DeviceConfig>
)