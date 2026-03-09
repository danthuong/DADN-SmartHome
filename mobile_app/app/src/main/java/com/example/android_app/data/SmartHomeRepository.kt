package com.example.android_app.data

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import com.example.android_app.utils.AppStrings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import java.util.UUID

object SmartHomeRepository {
    // --- 1. QUẢN LÝ DỮ LIỆU ---
    private lateinit var prefs: SharedPreferences
    // Danh sách thiết bị (Logic chính dùng roomID)
    private val _devices = MutableStateFlow<List<SmartDevice>>(emptyList())
    val devices: StateFlow<List<SmartDevice>> = _devices.asStateFlow()

    // Danh sách Tên phòng để hiển thị lên UI (Sẽ thay đổi theo ngôn ngữ)
    private val _rooms = MutableStateFlow<List<String>>(emptyList())
    val rooms: StateFlow<List<String>> = _rooms.asStateFlow()

    // Danh sách ID phòng cố định để làm logic (Không bao giờ đổi)
    private val _roomIDs = MutableStateFlow(listOf("LIVING", "BED", "KITCHEN", "GARDEN"))
    val roomIDs = _roomIDs.asStateFlow()
    private val _roomDisplayNames = MutableStateFlow<Map<String, String>>(emptyMap())
    val roomDisplayNames = _roomDisplayNames.asStateFlow()

    private val _presets = MutableStateFlow<List<Preset>>(emptyList())
    val presets: StateFlow<List<Preset>> = _presets.asStateFlow()

    private val _activePresetId = MutableStateFlow<String?>(null)
    val activePresetId = _activePresetId.asStateFlow()

    private var deviceHistorySnapshot: Map<String, SmartDevice>? = null

    // --- 2. HÀM CẬP NHẬT NGÔN NGỮ (Kích hoạt khi đổi ngôn ngữ) ---
//    fun updateLanguage(strings: AppStrings) {
//        // Cập nhật tên phòng hiển thị dựa trên bộ ID cố định
//        _rooms.value = _roomIDs.value.map { id ->
//            when(id) {
//                "LIVING" -> strings.roomLiving
//                "BED" -> strings.roomBed
//                "KITCHEN" -> strings.roomKitchen
//                "GARDEN" -> strings.Garden
//                else -> id // Nếu là ID do user tự thêm thì giữ nguyên tên ID đó
//            }
//        }
//
//        // Khởi tạo thiết bị mặc định bằng roomID nếu danh sách đang trống
//        if (_devices.value.isEmpty()) {
//            _devices.value = listOf(
//                SmartLight("light1", "${strings.led} 1", true, 80f, Color.Yellow.toArgb(), "LIVING"),
//                SmartLight("light2", "${strings.led} 2", false, 30f, Color.Magenta.toArgb(), "BED"),
//                SmartFan("fan1", "${strings.fan} 1", true, 2f, true, false, "LIVING")
//            )
//        }
//    }

    fun init(context: Context) {
        prefs = context.getSharedPreferences("SmartHomeData", Context.MODE_PRIVATE)
        // Nếu không dùng GSON, bạn sẽ chỉ load được ID phòng đơn giản
        val savedRooms = prefs.getStringSet("room_ids_list", null)
        if (savedRooms != null) {
            _roomIDs.value = savedRooms.toList()
        }
    }

    fun updateLanguage(strings: AppStrings) {
        // Cập nhật bản đồ dịch: ID -> Tên hiển thị
        _roomDisplayNames.value = mapOf(
            "LIVING" to strings.roomLiving,
            "BED" to strings.roomBed,
            "KITCHEN" to strings.roomKitchen,
            "GARDEN" to strings.Garden
        )

        // Chỉ nạp thiết bị mặc định NẾU danh sách đang trống hoàn toàn (Tránh mất đồ khi đổi ngôn ngữ)
        if (_devices.value.isEmpty()) {
            _devices.value = listOf(
                // Lưu ý: roomID ở đây phải là ID cố định "LIVING", không phải strings.roomLiving
                SmartLight("light1", "${strings.led} 1", true, 80f, Color.Yellow.toArgb(), "LIVING"),
                SmartLight("light2", "${strings.led} 2", false, 30f, Color.Magenta.toArgb(), "BED"),
                SmartFan("fan1", "${strings.fan} 1", true, 2f, true, false, "LIVING")
            )
        } else {
            // Nếu đã có thiết bị, ta chỉ cập nhật lại Tên của các thiết bị mặc định cho đúng ngôn ngữ
            _devices.update { currentList ->
                currentList.map { device ->
                    if (device.id.startsWith("light") || device.id.startsWith("fan")) {
                        val newDefaultName = if (device.type == DeviceType.LIGHT)
                            "${strings.led} ${device.id.takeLast(1)}"
                        else "${strings.fan} ${device.id.takeLast(1)}"

                        when (device) {
                            is SmartLight -> device.copy(name = newDefaultName)
                            is SmartFan -> device.copy(name = newDefaultName)
                        }
                    } else device // Giữ nguyên tên nếu là thiết bị user tự đặt tên riêng
                }
            }
        }
    }

//    fun loadUserData(username: String, strings: AppStrings) {
//        if (!::prefs.isInitialized) return
//        // Đọc danh sách thiết bị đã lưu của riêng username này
//        val savedDevices = prefs.getString("devices_$username", null)
//
//        if (savedDevices == null) {
//            // Nếu user này chưa có dữ liệu, nạp đồ mặc định
//            _devices.value = listOf(
//                SmartLight("light1", "${strings.led} 1", false, 50f, Color.Yellow.toArgb(), "LIVING"),
//                SmartFan("fan1", "${strings.fan} 1", false, 1f, false, false, "LIVING")
//            )
//        } else {
//            // Ở đây nếu không dùng GSON thì việc parse List phức tạp sẽ rất khó.
//            // Tui khuyên bạn nên lưu những thứ đơn giản như Tên Phòng/Tên Thiết bị đã đổi.
//        }
//    }

    fun loadUserData(username: String, strings: AppStrings) {
        // Reset trạng thái khi user mới đăng nhập
        _activePresetId.value = null
        updateLanguage(strings)
    }

    // Mỗi khi đổi tên hoặc thêm đồ, bạn lưu Username hiện tại vào máy
    fun saveCurrentState(username: String) {
        val editor = prefs.edit()
        // Lưu danh sách phòng của user
        editor.putString("rooms_$username", _roomIDs.value.joinToString(","))
        editor.apply()
    }

    // --- 3. HÀM XỬ LÝ THEO roomID ---

    // [QUAN TRỌNG] Thêm thiết bị vào phòng bằng roomID
    fun addDevice(roomID: String, type: DeviceType, strings: AppStrings): SmartDevice {
        // Lọc thiết bị cùng loại trong cùng roomID để đếm số thứ tự
        val devicesInRoom = _devices.value.filter { it.roomID == roomID && it.type == type }
        val nextNumber = devicesInRoom.size + 1

        val typeName = if (type == DeviceType.LIGHT) strings.led else strings.fan
        val newName = "$typeName $nextNumber"
        val newId = UUID.randomUUID().toString()

        val device = when(type) {
            DeviceType.LIGHT -> SmartLight(newId, newName, false, 50f, Color.White.toArgb(), roomID)
            DeviceType.FAN -> SmartFan(newId, newName, false, 1f, false, false, roomID)
        }
        _devices.update { it + device }
        return device
    }

    // [QUAN TRỌNG] Lưu Preset kèm theo roomID
    fun savePreset(preset: Preset) {
        _presets.update { current ->
            val index = current.indexOfFirst { it.id == preset.id }
            if (index >= 0) {current.toMutableList().apply { set(index, preset) } }
            else {
                current + preset
            }
        }
    }

    // [QUAN TRỌNG] Xóa phòng bằng roomID
    fun deleteRoom(roomID: String, username: String) {
        _roomIDs.update { it.filterNot { id -> id == roomID } }
        // Xóa luôn tất cả thiết bị thuộc roomID đó
        _devices.update { it.filterNot { dev -> dev.roomID == roomID } }
        // Xóa luôn tất cả preset thuộc roomID đó
        _presets.update { it.filterNot { pre -> pre.roomID == roomID } }
        saveCurrentState(username)
    }

    fun addRoom(name: String) {
        val newID = "CUSTOM_${UUID.randomUUID().toString().take(4)}"
        _roomIDs.update { it + newID }
        // Cập nhật tên hiển thị cho ID mới này
        _roomDisplayNames.update { it + (newID to name) }
    }

    // --- 4. CÁC HÀM LOGIC KHÁC ---

    fun initializeForUser(username: String) {
        _devices.value = emptyList()
        _presets.value = emptyList()
        _activePresetId.value = null
    }

    fun clearData() {
        _devices.value = emptyList()
        _rooms.value = emptyList()
    }

    fun deleteDevice(deviceId: String) {
        _devices.update { it.filterNot { it.id == deviceId } }
    }

    fun renameDevice(id: String, newName: String) {
        _devices.update { list ->
            list.map { device ->
                if (device.id == id) {
                    when(device) {
                        is SmartLight -> device.copy(name = newName)
                        is SmartFan -> device.copy(name = newName)
                    }
                } else device
            }
        }
    }

    fun togglePreset(presetId: String) {
        if (_activePresetId.value == presetId) {
            revertToSnapshot()
            _activePresetId.value = null
        } else {
            saveSnapshot()
            applyPresetLogic(presetId)
            _activePresetId.value = presetId
        }
    }

    private fun saveSnapshot() {
        deviceHistorySnapshot = _devices.value.associateBy { it.id }
    }

    private fun revertToSnapshot() {
        val history = deviceHistorySnapshot ?: return
        _devices.update { current ->
            current.map { history[it.id] ?: it }
        }
        deviceHistorySnapshot = null
    }

    private fun applyPresetLogic(presetId: String) {
        val preset = _presets.value.find { it.id == presetId } ?: return
        _devices.update { current ->
            current.map { device ->
                val config = preset.deviceConfigs[device.id]
                if (config != null) {
                    when (device) {
                        is SmartLight -> if (config is LightConfig) {
                            device.copy(isOn = config.isOn, brightness = config.brightness, color = config.color)
                        } else device
                        is SmartFan -> if (config is FanConfig) {
                            device.copy(isOn = config.isOn, speed = config.speed, isOscillating = config.isOscillating, isTracking = config.isTracking)
                        } else device
                    }
                } else device
            }
        }
    }

    fun deletePreset(presetId: String) {
        _presets.update { list -> list.filterNot { it.id == presetId } }
    }

    fun updateLight(id: String, isOn: Boolean? = null, brightness: Float? = null, color: Int? = null) {
        _activePresetId.value = null
        _devices.update { list ->
            list.map { device ->
                if (device.id == id && device is SmartLight) {
                    val finalBrightness = brightness ?: device.brightness
                    val finalIsOn = if (brightness == 0f) false else (isOn ?: device.isOn)
                    device.copy(isOn = finalIsOn, brightness = finalBrightness, color = color ?: device.color)
                } else device
            }
        }
    }

    fun updateFan(id: String, isOn: Boolean? = null, speed: Float? = null, isOscillating: Boolean? = null, isTracking: Boolean? = null) {
        _activePresetId.value = null
        _devices.update { list ->
            list.map { device ->
                if (device.id == id && device is SmartFan) {
                    device.copy(
                        isOn = isOn ?: device.isOn,
                        speed = speed ?: device.speed,
                        isOscillating = isOscillating ?: device.isOscillating,
                        isTracking = isTracking ?: device.isTracking
                    )
                } else device
            }
        }
    }

    fun getPresetById(id: String?): Preset? = if (id == null) null else _presets.value.find { it.id == id }
}