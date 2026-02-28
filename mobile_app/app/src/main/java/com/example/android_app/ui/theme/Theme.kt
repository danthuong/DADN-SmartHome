package com.example.android_app.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

val BackgroundBlack = Color(0xFF121212)
val CardGray = Color(0xFF1E1E1E)
val PrimaryPurple = Color(0xFFBB86FC)
val AccentBlue = Color(0xFF03DAC5)

//private val DarkColorScheme = darkColorScheme(
//    primary = Purple80,
//    secondary = PurpleGrey80,
//    tertiary = Pink80
//)

//private val LightColorScheme = lightColorScheme(
//    primary = Purple40,
//    secondary = PurpleGrey40,
//    tertiary = Pink40
//
//    /* Other default colors to override
//    background = Color(0xFFFFFBFE),
//    surface = Color(0xFFFFFBFE),
//    onPrimary = Color.White,
//    onSecondary = Color.White,
//    onTertiary = Color.White,
//    onBackground = Color(0xFF1C1B1F),
//    onSurface = Color(0xFF1C1B1F),
//    */
//)

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF6200EE),   // Màu thương hiệu của app
    secondary = AccentBlue,    // Màu nhấn (Ánh sáng, nhiệt độ)
    background = Color(0xFF0F0F0F), // Màu nền tối
    surface = Color(0xFF1C1C1E),    // Màu của các ô Card trong chế độ tối
    onPrimary = Color.Black,
    onBackground = Color.White,     // Màu chữ trên nền tối
    onSurface = Color.White,        // Màu chữ trên ô Card tối
    error = Color(0xFFFF453A)       // Màu đỏ cho các cảnh báo/người lạ
)

private val LightColorScheme = lightColorScheme(
    primary = PrimaryPurple,  // Purple đậm hơn cho chế độ sáng
    secondary = Color(0xFF03DAC5),
    background = Color(0xFFF8F9FA), // Màu nền sáng
    surface = Color(0xFFFFFFFF),    // Màu Card trắng
    onPrimary = Color.White,
    onBackground = Color.Black,     // Màu chữ trên nền sáng
    onSurface = Color.Black,        // Màu chữ trên Card sáng
    error = Color(0xFFB00020)       // Màu đỏ báo lỗi cho chế độ sáng
)

@Composable
fun Android_appTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}

@Composable
fun SecurityStatus(isStrangerDetected: Boolean) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            // Nếu có người lạ thì Card đổi sang màu Đỏ (error),
            // nếu bình thường thì dùng màu tím nhạt (primaryContainer)
            containerColor = if (isStrangerDetected)
                MaterialTheme.colorScheme.error
            else
                MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Text(
            text = if (isStrangerDetected) "CẢNH BÁO: NGƯỜI LẠ!" else "An ninh: Bình thường",
            // Chữ tự động đổi màu tương phản với nền (onDetailedColor)
            color = if (isStrangerDetected)
                MaterialTheme.colorScheme.onError
            else
                MaterialTheme.colorScheme.onPrimaryContainer
        )
    }
}