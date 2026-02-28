package com.example.android_app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.*
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.android_app.ui.screens.DashboardScreen
import com.example.android_app.ui.screens.LoginScreen
import com.example.android_app.ui.screens.ProfileScreen
import com.example.android_app.ui.screens.SignUpScreen
import com.example.android_app.ui.theme.Android_appTheme

class MainActivity : ComponentActivity() {

    // Xin quyền thông báo cho Android 13+
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        // Xử lý nếu người dùng từ chối/đồng ý
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            Android_appTheme {
                AppNavigation()
            }
        }
    }
}

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    var currentUserName by remember { mutableStateOf("User") }

    NavHost(navController = navController, startDestination = "login") {
        composable("login") {
            LoginScreen(
                onLoginSuccess = { typedName ->
                    currentUserName = typedName // Lấy tên từ màn hình login
                    navController.navigate("dashboard")
                },
                onNavigateToSignUp = { navController.navigate("signup") }
            )
        }
        composable("signup") {
            SignUpScreen(
                onSignUpSuccess = { typedName ->
                    currentUserName = typedName
                    navController.navigate("login")
                },
                onBackToLogin = { navController.popBackStack() }
            )
        }
        composable("dashboard") {
            DashboardScreen(
                userName = currentUserName,
                onLogout = { navController.navigate("login") { popUpTo(0) } },
                onProfileClick = { navController.navigate("profile") } // THÊM DÒNG NÀY
            )
        }
        composable("profile") {
            ProfileScreen(
                userName = currentUserName,
                onBack = { navController.popBackStack() },
                onLogout = {
                    navController.navigate("login") {
                        popUpTo(0) // Xóa sạch lịch sử để không quay lại Dashboard được
                    }
                }
            )
        }
    }
}