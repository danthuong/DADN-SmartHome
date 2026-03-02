package com.example.android_app.data

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

object SmartHomeRepository {
    // MÔ PHỎNG DATABASE CLOUD ĐỂ DEMO, MỐT CÓ SERVER CHỈ CẦN CHỈNH LOGIC FILE NÀY, UI SẼ GIỮ NGUYÊN
    // TỨC LÀ DATA SẼ RA VÔ Ở REPOSITORY NÀY ĐỂ SYNC LÊN CLOUD -> ĐỒNG BỘ VỚI CÁC THIẾT BỊ VÀ USER KHÁC KHI CÓ THAY ĐỔI

    // Danh sách thiết bị với state hiện tại, demo thì đang để hardcode, mốt thêm logic để lấy từ server (Real-time stream)
    private val _devices = MutableStateFlow<List<SmartDevice>>(
        listOf(
            SmartLight("light1", "Light 1", true, 80f, Color.Yellow.toArgb()),
            SmartLight("light2", "Light 2", false, 30f, Color.Magenta.toArgb()),
            SmartFan("fan1", "Fan 1", true, 2f, true)
        )
    )
    val devices: StateFlow<List<SmartDevice>> = _devices.asStateFlow()

    // 2. Danh sách Preset (Real-time stream)
    private val _presets = MutableStateFlow<List<Preset>>(emptyList())
    val presets: StateFlow<List<Preset>> = _presets.asStateFlow()



    // --- LOGIC HOÀN TÁC (REVERT STATE) ---
    // Map lưu trạng thái cũ: DeviceID -> SmartDevice (bản copy)
    private var deviceHistorySnapshot: Map<String, SmartDevice>? = null
    // ID của preset đang kích hoạt
    private val _activePresetId = MutableStateFlow<String?>(null)
    val activePresetId = _activePresetId.asStateFlow()


    // --- HÀM XỬ LÝ ---

    // 1. Logic Toggle Preset (Bật/Hoàn tác)
    fun togglePreset(presetId: String) {
        if (_activePresetId.value == presetId) {
            // Đang bật preset này -> Tắt và Hoàn tác
            revertToSnapshot()
            _activePresetId.value = null
        } else {
            // Đang tắt hoặc đang ở preset khác -> Lưu snapshot mới và Apply
            saveSnapshot()
            applyPresetLogic(presetId)
            _activePresetId.value = presetId
        }
    }

    private fun saveSnapshot() {
        // Copy toàn bộ list device hiện tại vào map history
        deviceHistorySnapshot = _devices.value.associate { it.id to copyDevice(it) }
    }

    private fun revertToSnapshot() {
        val history = deviceHistorySnapshot ?: return
        _devices.update { currentList ->
            currentList.map { currentDevice ->
                // Nếu trong history có lưu thiết bị này thì lấy lại, ko thì giữ nguyên
                history[currentDevice.id] ?: currentDevice
            }
        }
        deviceHistorySnapshot = null
    }

    private fun applyPresetLogic(presetId: String) {
        val preset = _presets.value.find { it.id == presetId } ?: return

        _devices.update { currentList ->
            currentList.map { device ->
                val config = preset.deviceConfigs[device.id]
                if (config != null) {
                    when (device) {
                        is SmartLight -> if (config is LightConfig) {
                            device.copy(isOn = config.isOn, brightness = config.brightness, color = config.color)
                        } else device
                        is SmartFan -> if (config is FanConfig) {
                            device.copy(isOn = config.isOn, speed = config.speed, isOscillating = config.isOscillating)
                        } else device
                    }
                } else {
                    // Thiết bị không có trong preset thì giữ nguyên (hoặc tắt tùy logic bạn muốn)
                    device
                }
            }
        }
    }

    // Hàm copy sâu (Deep copy helper)
    private fun copyDevice(device: SmartDevice): SmartDevice {
        return when (device) {
            is SmartLight -> device.copy()
            is SmartFan -> device.copy()
        }
    }

    // 2. Logic Tạo/Sửa Preset
    fun savePreset(preset: Preset) {
        _presets.update { currentList ->
            // Kiểm tra xem ID đã tồn tại chưa để update hay thêm mới
            val index = currentList.indexOfFirst { it.id == preset.id }
            if (index >= 0) {
                // Update (Edit mode)
                val newList = currentList.toMutableList()
                newList[index] = preset
                newList
            } else {
                // Add new
                currentList + preset
            }
        }
    }

    // Các hàm update lẻ tẻ cho UI điều khiển trực tiếp
    fun updateLight(id: String, isOn: Boolean? = null, brightness: Float? = null, color: Int? = null) {
        _activePresetId.value = null // User can thiệp thủ công -> Mất trạng thái Preset
        _devices.update { list ->
            list.map { if (it.id == id && it is SmartLight) it.copy(isOn = isOn ?: it.isOn, brightness = brightness ?: it.brightness, color = color ?: it.color) else it }
        }
    }

    fun updateFan(id: String, isOn: Boolean? = null, speed: Float? = null, isOscillating: Boolean? = null) {
        _activePresetId.value = null
        _devices.update { list ->
            list.map { if (it.id == id && it is SmartFan) it.copy(isOn = isOn ?: it.isOn, speed = speed ?: it.speed, isOscillating = isOscillating ?: it.isOscillating) else it }
        }
    }

    fun getPresetById(id: String): Preset? = _presets.value.find { it.id == id }
}