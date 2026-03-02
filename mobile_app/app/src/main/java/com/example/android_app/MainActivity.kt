package com.example.android_app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.android_app.data.User
import com.example.android_app.ui.screens.*
import com.example.android_app.ui.theme.Android_appTheme
import com.example.android_app.utils.*

class MainActivity : ComponentActivity() {

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            // 1. Khai báo trạng thái Theme và Ngôn ngữ toàn cục
            var themeChoice by remember { mutableStateOf("system") }
            var languageChoice by remember { mutableStateOf(AppLanguage.VI) }

            // 2. Lấy bộ chữ và cấu hình Dark Mode dựa trên State
            val strings = if (languageChoice == AppLanguage.VI) VietnameseStrings else EnglishStrings
            val isDark = when (themeChoice) {
                "light" -> false
                "dark" -> true
                else -> isSystemInDarkTheme()
            }

            Android_appTheme(darkTheme = isDark) {
                AppNavigation(
                    currentTheme = themeChoice,
                    onThemeChange = { themeChoice = it },
                    currentLanguage = languageChoice,
                    onLanguageChange = { languageChoice = it },
                    strings = strings
                )
            }
        }
    }
}

@Composable
fun AppNavigation(
    currentTheme: String,
    onThemeChange: (String) -> Unit,
    currentLanguage: AppLanguage,
    onLanguageChange: (AppLanguage) -> Unit,
    strings: AppStrings // Nhận bộ chữ từ MainActivity
) {
    val navController = rememberNavController()
    // Lưu trữ User sau khi login hoặc signup
    var currentUser by remember { mutableStateOf<User?>(null) }

    NavHost(navController = navController, startDestination = "login") {

        // --- MÀN HÌNH LOGIN ---
        composable("login") {
            LoginScreen(
                strings = strings,
                onLoginSuccess = { userObj ->
                    currentUser = userObj
                    navController.navigate("dashboard") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onNavigateToSignUp = { navController.navigate("signup") }
            )
        }

        // --- MÀN HÌNH SIGNUP ---
        composable("signup") {
            SignUpScreen(
                strings = strings,
                onSignUpSuccess = { userObj ->
                    currentUser = userObj
                    navController.navigate("dashboard") {
                        popUpTo("signup") { inclusive = true }
                    }
                },
                onBackToLogin = { navController.popBackStack() }
            )
        }

        // --- MÀN HÌNH DASHBOARD ---
        composable("dashboard") {
            currentUser?.let { user ->
                DashboardScreen(
                    user = user,
                    strings = strings,
                    onProfileClick = { navController.navigate("profile") },
                    onSettingsClick = { navController.navigate("settings") },
                    onLogout = {
                        currentUser = null
                        navController.navigate("login") { popUpTo(0) }
                    },
                    // [MỚI] Khi bấm vào thiết bị -> Chuyển sang màn hình chi tiết kèm ID
                    onDeviceClick = { deviceId ->
                        navController.navigate("device_detail/$deviceId")
                    },
                    // [MỚI] Khi bấm tạo Preset -> Chuyển sang màn hình tạo Preset
                    onNavigateToCreatePreset = {
                        navController.navigate("create_preset")
                    },
                    onNavigateToEditPreset = { pid -> navController.navigate("edit_preset/$pid") }
                )
            }
        }

        // --- MÀN HÌNH CHI TIẾT THIẾT BỊ ---
        composable(
            route = "device_detail/{deviceId}",
            arguments = listOf(navArgument("deviceId") { type = NavType.StringType })
        ) { backStackEntry ->
            // Lấy ID từ đường dẫn
            val deviceId = backStackEntry.arguments?.getString("deviceId") ?: ""
            DeviceDetailScreen(
                deviceId = deviceId,
                onBack = { navController.popBackStack() }
            )
        }

        // --- ROUTE TẠO PRESET ---
        composable("create_preset") {
            CreatePresetScreen(
                strings = strings,
                presetIdToEdit = null,
                onBack = { navController.popBackStack() }
            )
        }

        // Route chỉnh sửa (có ID)
        composable(
            route = "edit_preset/{presetId}",
            arguments = listOf(navArgument("presetId") { type = NavType.StringType })
        ) { backStackEntry ->
            val pid = backStackEntry.arguments?.getString("presetId")
            CreatePresetScreen(
                strings = strings,
                presetIdToEdit = pid,
                onBack = { navController.popBackStack() }
            )
        }

        // --- MÀN HÌNH SETTINGS ---
        composable("settings") {
            SettingsScreen(
                strings = strings,
                currentTheme = currentTheme,
                onThemeChange = onThemeChange,
                currentLanguage = currentLanguage,
                onLanguageChange = onLanguageChange,
                onPasswordChange = { old, new ->
                    if (currentUser?.password == old) {
                        // Cập nhật pass mới vào đối tượng đang đăng nhập
                        currentUser = currentUser?.copy(password = new)
                        true
                    } else false
                },
                onBack = { navController.popBackStack() }
            )
        }

        // --- MÀN HÌNH PROFILE ---
        composable("profile") {
            currentUser?.let { user ->
                ProfileScreen(
                    user = user,
                    strings = strings, // Truyền strings vào Profile
                    onBack = { navController.popBackStack() },
                    onLogout = {
                        currentUser = null
                        navController.navigate("login") { popUpTo(0) }
                    }
                )
            }
        }
    }
}