package com.example.android_app.data.api

// Request models
data class LoginRequest(val username: String, val password: String)
data class RegisterRequest(val username: String, val password: String)
data class DeviceControlRequest(val command: String, val value: Any?)
data class DeviceCreateRequest(val name: String, val type: String, val roomId: String)
data class AvatarUpdateRequest(val avatar: String)
data class RoomCreateRequest(val roomId: String, val name: String)

// Response models
data class LoginResponse(val token: String, val user_id: Int, val username: String)
data class RegisterResponse(val token: String, val user_id: Int, val username: String)
data class DeviceCreateResponse(val success: Boolean, val device_id: String)
data class DevicesResponse(val devices: List<DeviceData>)
data class DeviceData(
    val id: String,
    val name: String,
    val type: String,
    val roomId: String,
    val isOn: Boolean = false,
    val brightness: Int = 50,
    val speed: Int = 1,
    val isOscillating: Boolean = false,
    val isTracking: Boolean = false
)
data class ControlResponse(val success: Boolean, val message: String)
data class RoomsResponse(val rooms: List<RoomData>)
data class RoomData(val id: String, val name: String)
data class StatusResponse(val temperature: Double, val light: Int, val pir: Boolean, val human_detect: Boolean)
data class AvatarResponse(val success: Boolean, val avatar: String?)
data class DeleteDeviceResponse(val success: Boolean)
data class PresetsResponse(val presets: List<PresetData>)
data class PresetData(
    val id: String,
    val name: String,
    val icon: String,
    val roomId: String?,
    val deviceConfigs: Map<String, ApiDeviceConfig>
)
data class PresetCreateRequest(
    val id: String,
    val name: String,
    val icon: String,
    val roomId: String?,
    val deviceConfigs: Map<String, ApiDeviceConfig>
)
data class PresetUpdateRequest(
    val name: String? = null,
    val icon: String? = null,
    val roomId: String? = null,
    val deviceConfigs: Map<String, ApiDeviceConfig>? = null
)

// API-friendly DeviceConfig (separate from app's DeviceConfig to avoid typealias issues)
data class ApiDeviceConfig(
    val isOn: Boolean = false,
    val brightness: Int = 50,
    val speed: Int = 1,
    val isOscillating: Boolean = false,
    val isTracking: Boolean = false
)
