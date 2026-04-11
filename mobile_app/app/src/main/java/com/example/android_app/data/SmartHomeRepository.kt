package com.example.android_app.data

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import com.example.android_app.utils.AppStrings
import com.example.android_app.data.api.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch
import kotlinx.coroutines.GlobalScope
import java.util.UUID

object SmartHomeRepository {
    // --- 1. QUẢN LÝ DỮ LIỆU ---
    private lateinit var prefs: SharedPreferences
    private var authToken: String? = null
    
    // Avatar state (lưu từ server để hiển thị)
    private val _avatarBase64 = MutableStateFlow<String?>(null)
    val avatarBase64: StateFlow<String?> = _avatarBase64.asStateFlow()
    
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
    // Lưu ý: Gọi API đồng bộ để đảm bảo có device_id từ server trước khi trả về
    suspend fun addDevice(roomID: String, type: DeviceType, strings: AppStrings): SmartDevice {
        // Lọc thiết bị cùng loại trong cùng roomID để đếm số thứ tự
        val devicesInRoom = _devices.value.filter { it.roomID == roomID && it.type == type }
        val nextNumber = devicesInRoom.size + 1

        val typeName = if (type == DeviceType.LIGHT) strings.led else strings.fan
        val newName = "$typeName $nextNumber"
        val typeStr = if (type == DeviceType.LIGHT) "light" else "fan"

        // Gọi API ĐỒNG BỘ (suspend) để lấy device_id từ server
        val token = authToken ?: return if (type == DeviceType.LIGHT) 
            SmartLight(UUID.randomUUID().toString(), newName, false, 50f, Color.White.toArgb(), roomID)
        else
            SmartFan(UUID.randomUUID().toString(), newName, false, 1f, false, false, roomID)
        
        var serverDeviceId: String? = null
        try {
            val response = ApiClient.apiService.createDevice(
                token,
                DeviceCreateRequest(name = newName, type = typeStr, roomId = roomID)
            )
            if (response.success) {
                serverDeviceId = response.device_id
            }
        } catch (e: Exception) {
            println("DEBUG: createDevice error - ${e.message}")
        }

        // Nếu API lỗi, dùng UUID tạm
        val finalDeviceId = serverDeviceId ?: UUID.randomUUID().toString()

        val device = when(type) {
            DeviceType.LIGHT -> SmartLight(finalDeviceId, newName, false, 50f, Color.White.toArgb(), roomID)
            DeviceType.FAN -> SmartFan(finalDeviceId, newName, false, 1f, false, false, roomID)
        }
        
        _devices.update { it + device }
        return device
    }

    // Version sync cho AlertDialog (gọi trong coroutine)
    fun addDeviceSync(roomID: String, type: DeviceType, strings: AppStrings, callback: (SmartDevice?) -> Unit) {
        kotlinx.coroutines.GlobalScope.launch {
            try {
                val device = addDevice(roomID, type, strings)
                callback(device)
            } catch (e: Exception) {
                println("DEBUG: addDeviceSync error - ${e.message}")
                callback(null)
            }
        }
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

    fun deleteRoom(roomID: String, username: String) {
        _roomIDs.update { it.filterNot { id -> id == roomID } }
        // Xóa luôn tất cả thiết bị thuộc roomID đó
        _devices.update { it.filterNot { dev -> dev.roomID == roomID } }
        // Xóa luôn tất cả preset thuộc roomID đó
        _presets.update { it.filterNot { pre -> pre.roomID == roomID } }
        saveCurrentState(username)
        
        GlobalScope.launch(Dispatchers.IO) {
            try {
                val token = authToken ?: return@launch
                ApiClient.apiService.deleteRoom(token, roomID)
            } catch (e: Exception) {
                println("DEBUG: Failed to delete room on server - ${e.message}")
            }
        }
    }

    fun addRoom(name: String) {
        val newID = "CUSTOM_${UUID.randomUUID().toString().take(4)}"
        _roomIDs.update { it + newID }
        // Cập nhật tên hiển thị cho ID mới này
        _roomDisplayNames.update { it + (newID to name) }
        
        GlobalScope.launch(Dispatchers.IO) {
            try {
                val token = authToken ?: return@launch
                ApiClient.apiService.createRoom(token, RoomCreateRequest(newID, name))
            } catch (e: Exception) {
                println("DEBUG: Failed to add room to server - ${e.message}")
            }
        }
    }

    // --- 4. CÁC HÀM LOGIC KHÁC ---

    fun initializeForUser(username: String) {
        _devices.value = emptyList()
        _presets.value = emptyList()
        _activePresetId.value = null
    }

    fun setDevicesFromApi(devices: List<SmartDevice>) {
        _devices.value = devices
    }

    fun clearData() {
        _devices.value = emptyList()
        _rooms.value = emptyList()
        _presets.value = emptyList()
        _activePresetId.value = null
        _avatarBase64.value = null
        _roomIDs.value = listOf("LIVING", "BED", "KITCHEN", "GARDEN")
        _roomDisplayNames.value = emptyMap()
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
        println("DEBUG: applyPresetLogic - preset: ${preset.name}, deviceConfigs: ${preset.deviceConfigs.size}")
        
        _devices.update { current ->
            current.map { device ->
                val config = preset.deviceConfigs[device.id]
                println("DEBUG: Checking device ${device.id}, config found: ${config != null}")
                if (config != null) {
                    // Apply preset config
                    when (device) {
                        is SmartLight -> if (config is LightConfig) {
                            device.copy(isOn = config.isOn, brightness = config.brightness, color = config.color)
                        } else device
                        is SmartFan -> if (config is FanConfig) {
                            device.copy(isOn = config.isOn, speed = config.speed, isOscillating = config.isOscillating, isTracking = config.isTracking)
                        } else device
                    }
                } else {
                    // Turn OFF devices NOT in preset
                    when (device) {
                        is SmartLight -> device.copy(isOn = false)
                        is SmartFan -> device.copy(isOn = false)
                        else -> device
                    }
                }
            }
        }
    }

    fun deletePreset(presetId: String) {
        _presets.update { list -> list.filterNot { it.id == presetId } }
        
        // Also delete from server
        GlobalScope.launch {
            deletePresetFromServer(presetId)
        }
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

    fun syncLightToServer(id: String, isOn: Boolean? = null, brightness: Float? = null, color: Int? = null) {
        if (isOn != null) {
            GlobalScope.launch {
                val result = controlDevice(id, "toggle", isOn)
                result.onFailure { e ->
                    println("ERROR: Failed to sync light toggle - ${e.message}")
                }
            }
        }
    }

    fun syncFanToServer(id: String, isOn: Boolean? = null, speed: Float? = null, isOscillating: Boolean? = null, isTracking: Boolean? = null) {
        if (isOn != null) {
            GlobalScope.launch {
                val result = controlDevice(id, "toggle", isOn)
                result.onFailure { e ->
                    println("ERROR: Failed to sync fan toggle - ${e.message}")
                }
            }
        }
        if (speed != null) {
            GlobalScope.launch {
                val result = controlDevice(id, "setSpeed", speed.toInt())
                result.onFailure { e ->
                    println("ERROR: Failed to sync fan speed - ${e.message}")
                }
            }
        }
        if (isOscillating != null) {
            GlobalScope.launch {
                val result = controlDevice(id, "setOscillation", isOscillating)
                result.onFailure { e ->
                    println("ERROR: Failed to sync fan oscillation - ${e.message}")
                }
            }
        }
        if (isTracking != null) {
            GlobalScope.launch {
                val result = controlDevice(id, "setTracking", isTracking)
                result.onFailure { e ->
                    println("ERROR: Failed to sync fan tracking - ${e.message}")
                }
            }
        }
    }

    fun getPresetById(id: String?): Preset? = if (id == null) null else _presets.value.find { it.id == id }
    
    // ==================== API FUNCTIONS ====================
    fun setToken(token: String) {
        authToken = "Bearer $token"
    }

    fun getToken(): String? = authToken

    fun getAvatar(): String? = _avatarBase64.value

    fun saveToken(token: String, context: Context) {
        prefs = context.getSharedPreferences("SmartHomeData", Context.MODE_PRIVATE)
        prefs.edit().putString("auth_token", token).apply()
    }

    fun loadToken(context: Context): String? {
        prefs = context.getSharedPreferences("SmartHomeData", Context.MODE_PRIVATE)
        val token = prefs.getString("auth_token", null)
        if (token != null) {
            authToken = "Bearer $token"
            println("DEBUG: Token loaded from SharedPrefs: $token")
        } else {
            println("DEBUG: No token found in SharedPrefs")
        }
        return token
    }

    fun clearToken() {
        authToken = null
    }

    suspend fun login(username: String, password: String): Result<LoginResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val response = ApiClient.apiService.login(LoginRequest(username, password))
                authToken = "Bearer ${response.token}"
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun register(username: String, password: String): Result<RegisterResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val response = ApiClient.apiService.register(RegisterRequest(username, password))
                authToken = "Bearer ${response.token}"
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    fun setTokenDirectly(token: String) {
        authToken = "Bearer $token"
    }

    suspend fun fetchDevices(): Result<List<DeviceData>> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                println("DEBUG: fetchDevices - authToken = $authToken")
                val response = ApiClient.apiService.getDevices(token)
                Result.success(response.devices)
            } catch (e: Exception) {
                println("DEBUG: fetchDevices error - ${e.message}")
                Result.failure(e)
            }
        }
    }

    suspend fun controlDevice(deviceId: String, command: String, value: Any?): Result<ControlResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                println("DEBUG: controlDevice - authToken = $authToken, deviceId = $deviceId, command = $command")
                val response = ApiClient.apiService.controlDevice(
                    token,
                    deviceId,
                    DeviceControlRequest(command, value)
                )
                Result.success(response)
            } catch (e: Exception) {
                println("DEBUG: controlDevice error - ${e.message}")
                Result.failure(e)
            }
        }
    }

    suspend fun fetchRooms(): Result<List<RoomData>> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                val response = ApiClient.apiService.getRooms(token)
                
                // Save rooms to local state
                val roomIds = response.rooms.map { it.id }
                _roomIDs.value = roomIds
                val roomNamesMap = response.rooms.associate { it.id to it.name }
                _roomDisplayNames.value = roomNamesMap
                
                Result.success(response.rooms)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun fetchStatus(): Result<StatusResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                val response = ApiClient.apiService.getStatus(token)
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun refreshDevices(): Result<List<DeviceData>> {
        return fetchDevices()
    }

    // ==================== AVATAR FUNCTIONS ====================
    suspend fun uploadAvatar(avatarBase64: String): Result<AvatarResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                val response = ApiClient.apiService.updateAvatar(token, AvatarUpdateRequest(avatarBase64))
                // Lưu vào state để hiển thị ngay
                _avatarBase64.value = avatarBase64
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun fetchAvatar(): Result<AvatarResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                val response = ApiClient.apiService.getAvatar(token)
                // Lưu vào state để hiển thị
                _avatarBase64.value = response.avatar
                println("DEBUG: Avatar saved to state: ${response.avatar?.take(50)}...")
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    // ==================== DELETE DEVICE ====================
    suspend fun deleteDeviceSync(deviceId: String): Result<DeleteDeviceResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                val response = ApiClient.apiService.deleteDevice(token, deviceId)
                if (response.success) {
                    _devices.update { list -> list.filterNot { it.id == deviceId } }
                }
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    // Wrapper for non-suspend context (e.g., Button.onClick)
    fun deleteDeviceAsync(deviceId: String) {
        GlobalScope.launch {
            deleteDeviceSync(deviceId)
        }
    }

    // ==================== PRESET FUNCTIONS ====================
    // Convert local DeviceConfig to API DeviceConfig
    private fun toApiDeviceConfig(config: DeviceConfig): ApiDeviceConfig {
        return when (config) {
            is LightConfig -> ApiDeviceConfig(
                isOn = config.isOn,
                brightness = config.brightness.toInt(),
                speed = 1,
                isOscillating = false,
                isTracking = false
            )
            is FanConfig -> ApiDeviceConfig(
                isOn = config.isOn,
                brightness = 50,
                speed = config.speed.toInt(),
                isOscillating = config.isOscillating,
                isTracking = config.isTracking
            )
            else -> ApiDeviceConfig()
        }
    }

    // Convert API DeviceConfig to local DeviceConfig
    private fun toLocalDeviceConfig(apiConfig: ApiDeviceConfig, localConfig: DeviceConfig): DeviceConfig {
        return when (localConfig) {
            is LightConfig -> LightConfig(
                isOn = apiConfig.isOn,
                brightness = apiConfig.brightness.toFloat(),
                color = localConfig.color
            )
            is FanConfig -> FanConfig(
                isOn = apiConfig.isOn,
                speed = apiConfig.speed.toFloat(),
                isOscillating = apiConfig.isOscillating,
                isTracking = apiConfig.isTracking
            )
            else -> localConfig
        }
    }

    suspend fun fetchPresets(): Result<PresetsResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                val response = ApiClient.apiService.getPresets(token)
                
                // Convert API presets to local Preset objects
                val localPresets = response.presets.map { presetData ->
                    // Get device types from current devices to properly convert configs
                    val deviceTypes = _devices.value.associate { it.id to it.type }
                    
                    val convertedConfigs = presetData.deviceConfigs.mapValues { (deviceId, apiConfig) ->
                        val deviceType = deviceTypes[deviceId]
                        val defaultConfig: DeviceConfig = when (deviceType) {
                            DeviceType.LIGHT -> LightConfig(false, 50f, -256)
                            DeviceType.FAN -> FanConfig(false, 1f, false, false)
                            else -> LightConfig(false, 50f, -256) as DeviceConfig
                        }
                        toLocalDeviceConfig(apiConfig, defaultConfig)
                    }
                    
                    Preset(
                        id = presetData.id,
                        name = presetData.name,
                        icon = presetData.icon,
                        roomID = presetData.roomId ?: "LIVING",
                        deviceConfigs = convertedConfigs
                    )
                }
                _presets.value = localPresets
                
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    suspend fun savePresetToServer(preset: Preset): Result<DeleteDeviceResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                
                // Convert local configs to API configs
                val apiConfigs = preset.deviceConfigs.mapValues { (_, config) ->
                    toApiDeviceConfig(config)
                }
                
                // Check if preset exists - update or create
                val existingIndex = _presets.value.indexOfFirst { it.id == preset.id }
                if (existingIndex >= 0) {
                    val request = PresetUpdateRequest(
                        name = preset.name,
                        icon = preset.icon,
                        roomId = preset.roomID,
                        deviceConfigs = apiConfigs
                    )
                    val response = ApiClient.apiService.updatePreset(token, preset.id, request)
                    // Update local state
                    _presets.update { current ->
                        val idx = current.indexOfFirst { it.id == preset.id }
                        if (idx >= 0) {
                            current.toMutableList().apply { set(idx, preset) }
                        } else current + preset
                    }
                    Result.success(response)
                } else {
                    val request = PresetCreateRequest(
                        id = preset.id,
                        name = preset.name,
                        icon = preset.icon,
                        roomId = preset.roomID,
                        deviceConfigs = apiConfigs
                    )
                    val response = ApiClient.apiService.createPreset(token, request)
                    // Update local state
                    _presets.value = _presets.value + preset
                    Result.success(response)
                }
            } catch (e: Exception) {
                println("DEBUG: savePresetToServer error - ${e.message}")
                Result.failure(e)
            }
        }
    }

    suspend fun deletePresetFromServer(presetId: String): Result<DeleteDeviceResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val token = authToken ?: return@withContext Result.failure(Exception("No token"))
                val response = ApiClient.apiService.deletePreset(token, presetId)
                // Update local state
                _presets.update { list -> list.filterNot { it.id == presetId } }
                Result.success(response)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
}