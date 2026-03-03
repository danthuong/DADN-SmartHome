package com.example.android_app

import android.Manifest
import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.*
import androidx.navigation.compose.composable
import com.example.android_app.data.SmartHomeRepository
import com.example.android_app.data.User
import com.example.android_app.ui.screens.*
import com.example.android_app.ui.theme.Android_appTheme
import com.example.android_app.utils.*

class MainActivity : ComponentActivity() {

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SmartHomeRepository.init(this)
        // 1. Khai báo sharedPref ở đây để dùng cho startDestination
        val sharedPref = getSharedPreferences("UserPrefs", Context.MODE_PRIVATE)
        val savedUsername = sharedPref.getString("saved_username", null)

        // 2. Logic: Nếu đã có username lưu lại thì vào thẳng Dashboard
        val startDestination = if (savedUsername != null) "dashboard" else "login"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            val savedTheme = sharedPref.getString("theme_choice", "system") ?: "system"
            val savedLang = sharedPref.getString("lang_choice", "VI") ?: "VI"
            val savedUsername = sharedPref.getString("saved_username", null)

            var themeChoice by remember { mutableStateOf("system") }
            var languageChoice by remember { mutableStateOf(AppLanguage.VI) }
            val strings = if (languageChoice == AppLanguage.VI) VietnameseStrings else EnglishStrings
            val startDestination = "login"

            LaunchedEffect(languageChoice) {
                sharedPref.edit().putString("lang_choice", languageChoice.name).apply()
                SmartHomeRepository.updateLanguage(strings)
            }

            LaunchedEffect(themeChoice) {
                sharedPref.edit().putString("theme_choice", themeChoice).apply()
            }

            val isDark = when (themeChoice) {
                "light" -> false
                "dark" -> true
                else -> isSystemInDarkTheme()
            }

            Android_appTheme(darkTheme = isDark) {
                // TRUYỀN sharedPref vào AppNavigation
                AppNavigation(
                    currentTheme = themeChoice,
                    onThemeChange = { themeChoice = it },
                    currentLanguage = languageChoice,
                    onLanguageChange = { languageChoice = it },
                    strings = strings,
                    sharedPref = sharedPref, // TRUYỀN VÀO ĐÂY
                    initialDestination = if (savedUsername != null) "dashboard" else "login" // TRUYỀN ĐIỂM BẮT ĐẦU
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
    strings: AppStrings,
    sharedPref: SharedPreferences, // NHẬN sharedPref
    initialDestination: String // NHẬN ĐIỂM BẮT ĐẦU
) {
    val navController = androidx.navigation.compose.rememberNavController()

    // Khởi tạo user mặc định nếu đã lưu login
    val savedUsername = sharedPref.getString("saved_username", null)
    val userFromDb = remember(savedUsername) {
        com.example.android_app.data.MockDatabase.users.find { it.username == savedUsername }
    }

    // 3. Khởi tạo currentUser bằng user tìm được (nếu không thấy thì để null)
    var currentUser by remember { mutableStateOf<User?>(userFromDb) }

    androidx.navigation.compose.NavHost(
        navController = navController,
        startDestination = initialDestination // DÙNG GIÁ TRỊ TÍNH TOÁN ĐƯỢC
    ) {
        composable("login") {
            LoginScreen(
                strings = strings,
                onLoginSuccess = { userObj : User ->
                    // GỌI HÀM RESET DATA (Đảm bảo bạn đã thêm hàm này vào Repo ở Bước 2 bên dưới)
                    SmartHomeRepository.loadUserData(userObj.username, strings)

                    currentUser = userObj
                    // LƯU LOGIN VÀO MÁY (Mục 6)
//                    sharedPref.edit().putString("saved_username", userObj.username).apply()

                    navController.navigate("dashboard") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onNavigateToSignUp = { navController.navigate("signup") }
            )
        }

        composable("signup") {
            SignUpScreen(
                strings = strings,
                onSignUpSuccess = { userObj ->
                    sharedPref.edit().putString("saved_username", userObj.username).apply()
                    currentUser = userObj
                    navController.navigate("dashboard") {
                        popUpTo("signup") { inclusive = true }
                    }
                },
                onBackToLogin = { navController.popBackStack() }
            )
        }

        composable("dashboard") {
            currentUser?.let { user ->
                DashboardScreen(
                    user = user,
                    strings = strings,
                    onProfileClick = { navController.navigate("profile") },
                    onSettingsClick = { navController.navigate("settings") },
                    onLogout = {
                        // XÓA DỮ LIỆU KHI LOGOUT (Mục 6)
                        sharedPref.edit().remove("saved_username").apply()
                        currentUser = null
                        navController.navigate("login") { popUpTo(0) }
                    },
                    onDeviceClick = { /* ... */ },
                    onNavigateToCreatePreset = { navController.navigate("create_preset") },
                    onNavigateToEditPreset = { pid -> navController.navigate("edit_preset/$pid") },
                    onNavigateToFaceScan = { navController.navigate("face_scan") }
                )
            }
        }

        // --- GIỮ NGUYÊN CÁC COMPOSABLE KHÁC (settings, profile, device_detail,...) ---
        // Nhớ truyền 'strings' vào SettingsScreen và ProfileScreen nhé!
        composable("settings") {
            SettingsScreen(
                strings = strings,
                currentTheme = currentTheme,
                onThemeChange = onThemeChange,
                currentLanguage = currentLanguage,
                onLanguageChange = onLanguageChange,
                onPasswordChange = { old, new ->
                    if (currentUser?.password == old) {
                        currentUser = currentUser?.copy(password = new)
                        true
                    } else false
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable("profile") {
            currentUser?.let { user ->
                ProfileScreen(
                    user = user,
                    strings = strings,
                    onBack = { navController.popBackStack() },
                    onLogout = {
                        sharedPref.edit().remove("saved_username").apply()
                        currentUser = null
                        navController.navigate("login") { popUpTo(0) }
                    }
                )
            }
        }

        // --- 1. MÀN HÌNH TẠO PRESET (MỚI) ---
//        composable("create_preset") {
//            CreatePresetScreen(
//                strings = strings, // Truyền bộ ngôn ngữ vào đây
//                presetIdToEdit = null,
//                onBack = { navController.popBackStack() }
//            )
//        }

        // --- 2. MÀN HÌNH SỬA PRESET (MỚI) ---
        composable(
            route = "edit_preset/{presetId}",
            arguments = listOf(androidx.navigation.navArgument("presetId") {
                type = androidx.navigation.NavType.StringType
            })
        ) { backStackEntry ->
            val pid = backStackEntry.arguments?.getString("presetId")
            CreatePresetScreen(
                strings = strings,
                presetIdToEdit = pid,
                onBack = { navController.popBackStack() }
            )
        }

        composable("face_scan") {
            FaceRecognitionScreen(
                strings = strings,
                onBack = { navController.popBackStack() }
            )
        }
    }
}