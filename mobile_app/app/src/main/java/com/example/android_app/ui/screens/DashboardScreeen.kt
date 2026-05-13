package com.example.android_app.ui.screens

import android.Manifest
import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.android_app.data.*
import com.example.android_app.ui.theme.PrimaryPurple
import com.example.android_app.utils.AppStrings
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import java.util.Calendar
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.toArgb
import com.example.android_app.utils.getTranslatedEmojiCategories
import kotlinx.coroutines.launch
import androidx.compose.ui.draw.alpha
import com.example.android_app.data.api.AvailableDevice

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    user: User,
    strings: AppStrings,
    onLogout: () -> Unit,
    onProfileClick: () -> Unit,
    onSettingsClick: () -> Unit,
    onDeviceClick: (String) -> Unit,
    onNavigateToCreatePreset: () -> Unit,
    onNavigateToEditPreset: (String) -> Unit,
    // onNavigateToFaceScan: () -> Unit
) {
    val context = LocalContext.current
    val sharedPref = remember { context.getSharedPreferences("UserPrefs", Context.MODE_PRIVATE) }
    val avatarBase64 by SmartHomeRepository.avatarBase64.collectAsState()
    val avatarBytes = remember(avatarBase64) {
        avatarBase64?.let { android.util.Base64.decode(it, android.util.Base64.DEFAULT) }
    }

    // --- 1. LẤY DATA TỪ REPO (PHÒNG, THIẾT BỊ, PRESETS) ---
    val rooms by SmartHomeRepository.rooms.collectAsState() // Lấy từ Repo để thêm/xóa được
    val roomIDs by SmartHomeRepository.roomIDs.collectAsState()
    val roomNames by SmartHomeRepository.roomDisplayNames.collectAsState()
    var selectedRoomID by remember { mutableStateOf("LIVING") } // Dùng ID để làm State

    val allDevices by SmartHomeRepository.devices.collectAsState()
    val filteredDevices = allDevices.filter { it.roomID == selectedRoomID }

    val presets by SmartHomeRepository.presets.collectAsState()
    val activePresetId by SmartHomeRepository.activePresetId.collectAsState()

    // --- 2. QUẢN LÝ TRẠNG THÁI UI ---
    // Khởi tạo phòng mặc định sau khi data load
    LaunchedEffect(rooms) { if (selectedRoomID == "" && rooms.isNotEmpty()) selectedRoomID = rooms[0] }

    // Load devices from API when screen opens
    LaunchedEffect(Unit) {
        // Check if token is available, if not, try to load it
        if (SmartHomeRepository.getToken() == null) {
            SmartHomeRepository.loadToken(context)
        }
        
        // Fetch devices from API
        val result = SmartHomeRepository.fetchDevices()
        result.onSuccess { deviceList ->
            val convertedDevices = deviceList.map { deviceData ->
                when (deviceData.type) {
                    "light" -> SmartLight(
                        id = deviceData.id,
                        name = deviceData.name,
                        isOn = deviceData.isOn,
                        brightness = deviceData.brightness.toFloat(),
                        color = Color.Yellow.toArgb(),
                        roomID = deviceData.roomId
                    )
                    "fan" -> SmartFan(
                        id = deviceData.id,
                        name = deviceData.name,
                        isOn = deviceData.isOn,
                        speed = deviceData.speed.toFloat(),
                        isOscillating = deviceData.isOscillating,
                        isTracking = deviceData.isTracking,
                        roomID = deviceData.roomId
                    )
                    else -> SmartLight(deviceData.id, deviceData.name, false, 50f, Color.White.toArgb(), deviceData.roomId)
                }
            }
            SmartHomeRepository.setDevicesFromApi(convertedDevices)
        }.onFailure { error ->
            println("Error fetching devices: ${error.message}")
        }
        
        // Fetch rooms from API
        val roomsResult = SmartHomeRepository.fetchRooms()
        roomsResult.onSuccess { roomList ->
            println("DEBUG: Fetched ${roomList.size} rooms from API")
        }.onFailure { error ->
            println("Error fetching rooms: ${error.message}")
        }
        
        // Fetch presets from API
        val presetsResult = SmartHomeRepository.fetchPresets()
        presetsResult.onSuccess { presetList ->
            println("DEBUG: Fetched ${presetList.presets.size} presets from API")
        }.onFailure { error ->
            println("Error fetching presets: ${error.message}")
        }
    }

    var selectedDeviceForEdit by remember { mutableStateOf<SmartDevice?>(null) }
    var selectedPresetToEdit by remember { mutableStateOf<Preset?>(null) }
    var showAddRoomDialog by remember { mutableStateOf(false) }

    val calendar = Calendar.getInstance()
    val hour = calendar.get(Calendar.HOUR_OF_DAY)

    // --- THỜI TIẾT THEO VỊ TRÍ ---
    var weatherInfo by remember { mutableStateOf<WeatherInfo?>(null) }
    val scope = rememberCoroutineScope()
    val fetchWeather: () -> Unit = {
        scope.launch {
            WeatherHelper.fetchWeatherForCurrentLocation(context)
                .onSuccess { weatherInfo = it }
                .onFailure { println("Weather fetch failed: ${it.message}") }
        }
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        if (result[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            result[Manifest.permission.ACCESS_COARSE_LOCATION] == true) {
            fetchWeather()
        }
    }
    LaunchedEffect(Unit) {
        if (WeatherHelper.hasLocationPermission(context)) {
            fetchWeather()
        } else {
            permissionLauncher.launch(arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            ))
        }
    }

    val isDay = weatherInfo?.isDay ?: (hour in 6..17)
    val weatherIcon = if (isDay) Icons.Default.WbSunny else Icons.Default.NightsStay
    val weatherDesc = weatherInfo?.description ?: if (isDay) strings.sun else strings.clear
    val weatherTempText = weatherInfo?.let { "${it.temperatureC.toInt()}°C" } ?: "--°C"
    var showAddDeviceDialog by remember { mutableStateOf(false) }

    var showCreatePresetSheet by remember { mutableStateOf(false) }
    var newPresetName by remember { mutableStateOf("") }
    val selectedConfigs = remember { mutableStateMapOf<String, DeviceConfig>() }

    val filteredPresets = presets.filter { it.roomID == selectedRoomID }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("YOLO HOME", fontWeight = FontWeight.ExtraBold) },
                navigationIcon = {
                    IconButton(onClick = onProfileClick) {
                        if (avatarBytes != null) {
                            AsyncImage(model = avatarBytes, contentDescription = null, modifier = Modifier.size(32.dp).clip(CircleShape), contentScale = ContentScale.Crop)
                        } else {
                            Surface(Modifier.size(32.dp), shape = CircleShape, color = MaterialTheme.colorScheme.surfaceVariant) {
                                Icon(Icons.Default.Person, null, Modifier.padding(6.dp), tint = MaterialTheme.colorScheme.primary)
                            }
                        }
                    }
                },
                actions = { IconButton(onClick = onSettingsClick) { Icon(Icons.Default.Settings, null) } }
            )
        },
        /*
        floatingActionButton = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                // 1. NÚT QUÉT KHUÔN MẶT (MỚI)
                FloatingActionButton(
                    onClick = onNavigateToFaceScan,
                    shape = CircleShape,
                    containerColor = MaterialTheme.colorScheme.primary, // Màu khác nút + để phân biệt
                    contentColor = Color.White
                ) {
                    // Icon hình gương mặt/quét
                    Icon(imageVector = Icons.Default.Face, contentDescription = "Face Scan")
                }
            }
        }
        */
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize().padding(horizontal = 16.dp)) {

            Row(
            modifier = Modifier.fillMaxWidth().height(100.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Card Welcome (Chiếm 65%)
                Card(
                    modifier = Modifier.weight(0.65f).fillMaxHeight(),
                    shape = RoundedCornerShape(28.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(strings.welcome, style = MaterialTheme.typography.bodySmall)
                        Text(
                            text = user.fullName.ifBlank { user.username },
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.weight(1f))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = weatherIcon,
                                contentDescription = null,
                                tint = Color(0xFFFFB300),
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "$weatherTempText - $weatherDesc",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }

                // Card Temp (Chiếm 35%)
                SensorCard(
                    title = strings.temp,
                    value = weatherTempText,
                    modifier = Modifier.weight(0.35f).fillMaxHeight()
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 1. QUẢN LÝ PHÒNG (CÓ NÚT +)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(strings.room, style = MaterialTheme.typography.labelLarge, color = Color.Gray, modifier = Modifier.weight(1f))
                IconButton(onClick = { showAddRoomDialog = true }) {
                    Icon(Icons.Default.AddCircle, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                }
            }
            LazyRow(horizontalArrangement = Arrangement.spacedBy(5.dp), modifier = Modifier.padding(vertical = 5.dp)) {
                items(roomIDs) { id ->
                    val displayName = roomNames[id] ?: id
                    FilterChip(
                        selected = selectedRoomID == id,
                        onClick = { selectedRoomID = id },
                        label = { Text(displayName) },
                        trailingIcon = {
                            Icon(Icons.Default.Cancel, null, Modifier.size(16.dp).clickable { 
                                SmartHomeRepository.deleteRoom(id, user.username) 
                                if (selectedRoomID == id) {
                                    selectedRoomID = roomIDs.firstOrNull { it != id } ?: ""
                                }
                            })
                        }
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // PRESETS (SCENES) - Có chức năng chỉnh sửa khi nhấn giữ
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = strings.presets,
                    style = MaterialTheme.typography.labelLarge,
                    color = Color.Gray,
                    modifier = Modifier.weight(1f)
                )
                IconButton(onClick = {
                    if (selectedRoomID.isNotEmpty()) {
                        newPresetName = ""
                        selectedConfigs.clear()
                        showCreatePresetSheet = true
                    } else {
                        android.widget.Toast.makeText(context, "Vui lòng tạo phòng trước!", android.widget.Toast.LENGTH_SHORT).show()
                    }
                }) {
                    Icon(
                        imageVector = Icons.Default.AddCircle, // Dùng AddCircle cho giống phần Phòng
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
            LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(vertical = 8.dp)) {

                items(filteredPresets) { preset ->
                    PresetCard(
                        preset = preset,
                        isActive = preset.id == activePresetId,
                        onClick = { SmartHomeRepository.togglePreset(preset.id) },
                        onLongClick = { selectedPresetToEdit = preset }, // 2. CHỈNH SỬA PRESET
                        onDelete = { SmartHomeRepository.deletePreset(preset.id)}
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // 4. DANH SÁCH THIẾT BỊ (QUẸT ĐỂ XOÁ)
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = strings.devices,
                    style = MaterialTheme.typography.labelLarge,
                    color = Color.Gray,
                    modifier = Modifier.weight(1f)
                )
                IconButton(onClick = { 
                    if (selectedRoomID.isNotEmpty()) {
                        showAddDeviceDialog = true 
                    } else {
                        android.widget.Toast.makeText(context, "Vui lòng tạo phòng trước!", android.widget.Toast.LENGTH_SHORT).show()
                    }
                }) {
                    Icon(
                        imageVector = Icons.Default.AddCircle,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.weight(1f).padding(vertical = 8.dp)) {
                items(filteredDevices, key = { it.id }) { device ->
                    var showDeleteDialog by remember { mutableStateOf(false) }
                    
                    val dismissState = rememberSwipeToDismissBoxState(
                        confirmValueChange = {
                            if (it == SwipeToDismissBoxValue.EndToStart) {
                                showDeleteDialog = true
                            }
                            false // Don't delete yet, wait for dialog confirmation
                        }
                    )

                    // Delete Confirmation Dialog
                    if (showDeleteDialog) {
                        AlertDialog(
                            onDismissRequest = { showDeleteDialog = false },
                            title = { Text("Xóa thiết bị") },
                            text = { Text("Bạn có chắc muốn xóa ${device.name}?") },
                            confirmButton = {
                                Button(onClick = {
                                    // Delete locally first (sync), then call API (async)
                                    SmartHomeRepository.deleteDevice(device.id)
                                    GlobalScope.launch {
                                        SmartHomeRepository.deleteDeviceSync(device.id)
                                    }
                                    showDeleteDialog = false
                                }) { Text("Xóa") }
                            },
                            dismissButton = {
                                Button(onClick = { showDeleteDialog = false }) { Text("Hủy") }
                            }
                        )
                    }

                    SwipeToDismissBox(
                        state = dismissState,
                        enableDismissFromStartToEnd = false,
                        backgroundContent = {
                            val color = if (dismissState.targetValue == SwipeToDismissBoxValue.EndToStart) Color.Red else Color.Transparent
                            Box(Modifier.fillMaxSize().background(color,RoundedCornerShape(20.dp) ).padding(horizontal = 20.dp), contentAlignment = Alignment.CenterEnd) {
                                if (color == Color.Red) Icon(Icons.Default.Delete, null, tint = Color.White)
                            }
                        }
                    ) {
                        DeviceItemCard(
                            device = device,
                            strings = strings,
                            onClick = { selectedDeviceForEdit = device }
                        )
                    }
                }
            }
        }
    }

    if (showCreatePresetSheet) {
        var showEmojiPicker by remember { mutableStateOf(false) }
        var selectedIcon by remember { mutableStateOf("✨") }

        ModalBottomSheet(
            onDismissRequest = { showCreatePresetSheet = false },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ) {
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
                        value = newPresetName,
                        onValueChange = { newPresetName = it },
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
                    text = "${strings.devicesIn} $selectedRoomID",
                    style = MaterialTheme.typography.labelLarge,
                    color = Color.Gray
                )

                // Danh sách thiết bị để chọn cấu hình cho Preset
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredDevices) { device ->
                        DeviceSelectionCard(
                            device = device,
                            displayName = device.name,
                            strings = strings,
                            currentConfig = selectedConfigs[device.id],
                            onConfigChanged = { config ->
                                if (config == null) selectedConfigs.remove(device.id)
                                else selectedConfigs[device.id] = config
                            }
                        )
                    }
                }

                // NÚT LƯU
                Button(
                    onClick = {
                        println("DEBUG: Saving preset - name: $newPresetName, icon: $selectedIcon, configs: ${selectedConfigs.size}")
                        selectedConfigs.forEach { (id, config) ->
                            println("DEBUG: Device $id config: $config")
                        }
                        
                        if (newPresetName.isNotEmpty() && selectedConfigs.isNotEmpty()) {
                            val newPreset = Preset(
                                name = newPresetName,
                                icon = selectedIcon,
                                deviceConfigs = selectedConfigs.toMap(),
                                roomID = selectedRoomID
                            )
                            // 1. Save to server (which will update local repo on success)
                            GlobalScope.launch {
                                val result = SmartHomeRepository.savePresetToServer(newPreset)
                                result.onSuccess {
                                    println("DEBUG: Preset saved to server!")
                                }.onFailure {
                                    println("DEBUG: Failed to save preset to server: ${it.message}")
                                }
                            }
                            println("DEBUG: Preset saved successfully!")
                            // 3. Đóng Pop-up
                            showCreatePresetSheet = false

                        } else {
                            println("DEBUG: Cannot save preset - name empty: ${newPresetName.isEmpty()}, configs empty: ${selectedConfigs.isEmpty()}")
                        }
                    },
                    modifier = Modifier.fillMaxWidth().height(56.dp).padding(vertical = 8.dp)
                ) {
                    Text(strings.save)
                }
            }
        }
    }

    // --- HIỂN THỊ POP-UP CHỈNH SỬA PRESET ---
    if (selectedPresetToEdit != null) {
        ModalBottomSheet(
            onDismissRequest = { selectedPresetToEdit = null },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ) {
            var showEmojiPicker by remember { mutableStateOf(false) } // State để ẩn/hiện bảng chọn icon
            var selectedIcon by remember { mutableStateOf("✨") }
            // Ở đây bạn có thể tái sử dụng logic của CreatePresetScreen
            // nhưng truyền ID vào để Edit
            PresetEditSheet(
                preset = selectedPresetToEdit!!,
                selectedRoom = selectedRoomID,
                strings = strings,
                onDismiss = { selectedPresetToEdit = null }
            )
        }
    }

    if (showAddDeviceDialog) {
        var availableDevices by remember { mutableStateOf<List<AvailableDevice>>(emptyList()) }
        var isLoading by remember { mutableStateOf(true) }

        LaunchedEffect(Unit) {
            val result = SmartHomeRepository.fetchAvailableDevices()
            result.onSuccess { availableDevices = it }
            isLoading = false
        }

        AlertDialog(
            onDismissRequest = { showAddDeviceDialog = false },
            title = { Text(strings.addDevice) },
            text = {
                if (isLoading) {
                    CircularProgressIndicator()
                } else {
                    LazyColumn(modifier = Modifier.fillMaxWidth().heightIn(max = 400.dp)) {
                        items(availableDevices) { device ->
                            val isAdded = device.is_added == 1
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 12.dp)
                                    .alpha(if (isAdded) 0.5f else 1f)
                                    .clickable(enabled = !isAdded) {
                                        SmartHomeRepository.addDeviceSync(
                                            roomID = selectedRoomID,
                                            deviceId = device.device_id,
                                            name = device.description,
                                            strings = strings
                                        ) { }
                                        showAddDeviceDialog = false
                                    },
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = if (device.device_id.contains("LED", ignoreCase = true) || device.device_id.contains("LIGHT", ignoreCase = true)) Icons.Default.Lightbulb else Icons.Default.WindPower,
                                    contentDescription = null,
                                    modifier = Modifier.size(32.dp),
                                    tint = MaterialTheme.colorScheme.primary
                                )
                                Spacer(modifier = Modifier.width(16.dp))
                                Column {
                                    Text(device.description, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                                    Text("ID: ${device.device_id}", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = { showAddDeviceDialog = false }) { Text("Đóng") }
            }
        )
    }

    // --- 5. POP-UP CHỈNH SỬA (BOTTOM SHEET) ---
    if (selectedDeviceForEdit != null) {
        ModalBottomSheet(
            onDismissRequest = { selectedDeviceForEdit = null },
            sheetState = rememberModalBottomSheetState()
        ) {
            EditDeviceSheet(device = selectedDeviceForEdit!!, strings = strings) {
                selectedDeviceForEdit = null
            }
        }
    }

    // --- 1. DIALOG THÊM PHÒNG ---
    if (showAddRoomDialog) {
        var roomName by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showAddRoomDialog = false },
            title = { Text(strings.addRoomTitle) }, // Đã dùng strings
            text = {
                OutlinedTextField(
                    value = roomName,
                    onValueChange = { roomName = it },
                    label = { Text(strings.roomNameInput) } // Đã dùng strings
                )
            },
            confirmButton = {
                Button(onClick = {
                    SmartHomeRepository.addRoom(roomName)
                    showAddRoomDialog = false
                }) {
                    Text(strings.addBtn) // Đã dùng strings
                }
            }
        )
    }
}

// --- 1. CARD HIỂN THỊ THÔNG SỐ (Sensor) ---
@Composable
fun SensorCard(title: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        shape = RoundedCornerShape(20.dp)
    ) {
        Column(modifier = Modifier
            .fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally, // Căn giữa ngang
            verticalArrangement = Arrangement.Center // Căn giữa dọc
        ) {
            Text(title, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f), fontSize = 12.sp)
            Text(value, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        }
    }
}

// --- 2. CARD HIỂN THỊ NGỮ CẢNH (Preset) ---
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun PresetCard(
    preset: Preset,
    isActive: Boolean,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
    onDelete: () -> Unit// Xử lý xóa khi nhấn giữ
) {
    Box(modifier = Modifier.padding(top = 4.dp, end = 4.dp)) {
        Card(
            modifier = Modifier
                .size(width = 110.dp, height = 80.dp)
                .combinedClickable(
                    onClick = onClick,
                    onLongClick = onLongClick
                ),
            colors = CardDefaults.cardColors(
                containerColor = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
            ),
            shape = RoundedCornerShape(16.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(preset.icon, fontSize = 24.sp)
                Text(
                    preset.name,
                    style = MaterialTheme.typography.labelMedium,
                    color = if (isActive) Color.White else MaterialTheme.colorScheme.onSurface
                )
            }
        }
        // NÚT 'X' ĐỂ XOÁ Ở GÓC PHẢI TRÊN (Yêu cầu 1)
        Surface(
            modifier = Modifier
                .size(20.dp)
                .align(Alignment.TopEnd)
                .offset(x = 4.dp, y = (-6).dp) // Đẩy nút ra góc
                .clickable { onDelete() },
            shape = CircleShape,
            color = Color.Gray,
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "Delete",
                tint = Color.White,
                modifier = Modifier.padding(4.dp)
            )
        }
    }
}

// --- 3. CARD HIỂN THỊ THIẾT BỊ (Device) ---
@Composable
fun DeviceItemCard(
    device: SmartDevice,
    strings: AppStrings,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // --- LOGIC CHỌN ICON ĐỘNG CHO QUẠT VÀ ĐÈN ---
            val displayIcon = when (device) {
                is SmartLight -> Icons.Default.Lightbulb
                is SmartFan -> Icons.Default.WindPower
            }

            // Màu sắc và độ chói (giữ nguyên logic cũ cho đèn)
            val iconColor = if (device is SmartLight) Color(device.color) else MaterialTheme.colorScheme.primary
            val alphaValue = if (device is SmartLight && device.isOn) {
                (device.brightness / 100f).coerceAtLeast(0.3f)
            } else 1f

            // HIỂN THỊ ICON CHÍNH ĐÃ ĐƯỢC THAY ĐỔI
            Icon(
                imageVector = displayIcon,
                contentDescription = null,
                tint = if (device.isOn) iconColor.copy(alpha = alphaValue) else Color.Gray,
                modifier = Modifier.size(32.dp)
            )

            Spacer(modifier = Modifier.width(16.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = device.name,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )

                // Hiển thị trạng thái bằng chữ (Optional)
                if (device is SmartLight) {
                    // Nếu là Đèn: Hiện % độ sáng (hoặc "Off")
                    Text(
                        text = if (device.isOn) "${device.brightness.toInt()}%" else strings.off,
                        color = Color.Gray,
                        style = MaterialTheme.typography.bodySmall
                    )
                } else if (device is SmartFan) {
                    WindSpeedBar(speed = device.speed.toInt(), isOn = device.isOn)
                } else strings.off
            }

            // Nút gạt nhanh On/Off
            Switch(
                checked = device.isOn,
                onCheckedChange = { isChecked ->
                    if (device is SmartLight) {
                        SmartHomeRepository.updateLight(device.id, isOn = isChecked)
                        SmartHomeRepository.syncLightToServer(device.id, isOn = isChecked)
                    }
                    if (device is SmartFan) {
                        SmartHomeRepository.updateFan(device.id, isOn = isChecked)
                        SmartHomeRepository.syncFanToServer(device.id, isOn = isChecked)
                    }
                },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.White,
                    checkedTrackColor = MaterialTheme.colorScheme.primary
                )
            )
        }
    }
}

@Composable
fun WindSpeedBar(speed: Int, isOn: Boolean) {
    Row(
        modifier = Modifier.padding(top = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(3.dp) // Khoảng cách giữa các vạch
    ) {
        repeat(3) { index ->
            Box(
                modifier = Modifier
                    .width(18.dp)       // Độ dài mỗi vạch
                    .height(5.dp)       // Độ dày mỗi vạch
                    .clip(RoundedCornerShape(2.dp))
                    .background(
                        if (isOn && speed > index) MaterialTheme.colorScheme.primary
                        else Color.LightGray.copy(alpha = 0.4f)
                    )
            )
        }
    }
}
@OptIn(ExperimentalLayoutApi::class) // Chỉ cần cái này cho FlowRow
@Composable
fun EmojiPickerGrid(
    selectedIcon: String,
    strings: AppStrings,
    onIconSelected: (String) -> Unit
) {
    val translatedCategories = getTranslatedEmojiCategories(strings)
    // Dùng LazyColumn để có thể cuộn danh sách icon dài
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        translatedCategories.forEach { category ->
            item {
                Text(
                    text = category.name,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                // FlowRow tự động xuống hàng
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    category.emojis.forEach { emoji ->
                        Box(
                            modifier = Modifier
                                .size(44.dp)
                                .clip(CircleShape)
                                .background(
                                    if (selectedIcon == emoji) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
                                    else Color.Transparent
                                )
                                .border(
                                    width = if (selectedIcon == emoji) 2.dp else 0.dp,
                                    color = if (selectedIcon == emoji) MaterialTheme.colorScheme.primary else Color.Transparent,
                                    shape = CircleShape
                                )
                                .clickable { onIconSelected(emoji) },
                            contentAlignment = Alignment.Center
                        ) {
                            Text(emoji, fontSize = 22.sp)
                        }
                    }
                }
            }
        }
    }
}

fun getRoomDisplayName(id: String, strings: AppStrings): String {
    return when(id) {
        "LIVING" -> strings.roomLiving
        "BED" -> strings.roomBed
        "KITCHEN" -> strings.roomKitchen
        "GARDEN" -> strings.Garden
        else -> id // Nếu là phòng user tự tạo thì hiện nguyên tên
    }
}
