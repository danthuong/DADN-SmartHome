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
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SmartHomeRepository.init(this)

        val sharedPref = getSharedPreferences("UserPrefs", Context.MODE_PRIVATE)

        // Load saved token for auto-login restoration
        SmartHomeRepository.loadToken(this)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            // SỬA LỖI 1: Lấy đúng giá trị từ SharedPreferences để khởi tạo State
            val savedTheme = sharedPref.getString("theme_choice", "system") ?: "system"
            val savedLangString = sharedPref.getString("lang_choice", "VI") ?: "VI"
            val savedLanguage = try {
                AppLanguage.valueOf(savedLangString)
            } catch (e: Exception) {
                AppLanguage.VI
            }
            val savedUsername = sharedPref.getString("saved_username", null)

            // Gán giá trị đã lưu vào mutableStateOf
            var themeChoice by remember { mutableStateOf(savedTheme) }
            var languageChoice by remember { mutableStateOf(savedLanguage) }
            val strings = if (languageChoice == AppLanguage.VI) VietnameseStrings else EnglishStrings

            // SỬA LỖI 2: Nếu đã lưu user (vào thẳng dashboard), phải load data cho Repository
            LaunchedEffect(savedUsername) {
                if (savedUsername != null) {
                    SmartHomeRepository.loadUserData(savedUsername, strings)
                    
                    // Fetch avatar from server
                    GlobalScope.launch {
                        val result = SmartHomeRepository.fetchAvatar()
                        result.onSuccess { response ->
                            response.avatar?.let { avatarBase64 ->
                                println("DEBUG: Loaded avatar from server")
                            }
                        }.onFailure {
                            println("DEBUG: Failed to fetch avatar: ${it.message}")
                        }
                    }
                }
            }

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
                AppNavigation(
                    currentTheme = themeChoice,
                    onThemeChange = { themeChoice = it },
                    currentLanguage = languageChoice,
                    onLanguageChange = { languageChoice = it },
                    strings = strings,
                    sharedPref = sharedPref,
                    savedUsername = savedUsername // Truyền savedUsername vào Navigation
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
    sharedPref: SharedPreferences,
    savedUsername: String?
) {
    val navController = androidx.navigation.compose.rememberNavController()

    // If savedUsername exists in SharedPreferences, user is considered logged in
    val initialDestination = if (savedUsername != null) "dashboard" else "login"

    // Create User object from saved username (no password needed since we're using token auth)
    var currentUser by remember { mutableStateOf<User?>(savedUsername?.let { User(0, it) }) }

    androidx.navigation.compose.NavHost(
        navController = navController,
        startDestination = initialDestination
    ) {
        composable("login") {
            LoginScreen(
                strings = strings,
                onLoginSuccess = { userObj : User ->
                    SmartHomeRepository.loadUserData(userObj.username, strings)
                    currentUser = userObj
                    sharedPref.edit().putString("saved_username", userObj.username).apply()

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
                    // Cần load data cho repository sau khi đăng ký thành công
                    SmartHomeRepository.loadUserData(userObj.username, strings)

                    navController.navigate("dashboard") {
                        popUpTo("signup") { inclusive = true }
                    }
                },
                onBackToLogin = { navController.popBackStack() }
            )
        }

        composable("dashboard") {
            if (currentUser != null) {
                DashboardScreen(
                    user = currentUser!!,
                    strings = strings,
                    onProfileClick = { navController.navigate("profile") },
                    onSettingsClick = { navController.navigate("settings") },
                    onLogout = {
                        sharedPref.edit().remove("saved_username").apply()
                        SmartHomeRepository.clearToken()
                        SmartHomeRepository.clearData()
                        currentUser = null
                        navController.navigate("login") { popUpTo(0) }
                    },
                    onDeviceClick = { /* ... */ },
                    onNavigateToCreatePreset = { navController.navigate("create_preset") },
                    onNavigateToEditPreset = { pid -> navController.navigate("edit_preset/$pid") },
                )
            } else {
                // Đề phòng trường hợp bất thường currentUser null ở đây, văng ra login
                LaunchedEffect(Unit) {
                    sharedPref.edit().remove("saved_username").apply()
                    navController.navigate("login") { popUpTo(0) }
                }
            }
        }

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
                onNavigateToFaceScan = { navController.navigate("face_scan") },
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
                        SmartHomeRepository.clearToken()
                        SmartHomeRepository.clearData()
                        currentUser = null
                        navController.navigate("login") { popUpTo(0) }
                    }
                )
            }
        }

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