package com.example.android_app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.example.android_app.data.User
import com.example.android_app.utils.AppLanguage
import com.example.android_app.utils.AppStrings

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    currentTheme: String,
    onThemeChange: (String) -> Unit,
    onPasswordChange: (String, String) -> Boolean,
    currentLanguage: AppLanguage,
    onLanguageChange: (AppLanguage) -> Unit,
    strings: AppStrings,
    onBack: () -> Unit
) {
    var showThemeDialog by remember { mutableStateOf(false) }
    var showLangDialog by remember { mutableStateOf(false) }
    var showPasswordDialog by remember { mutableStateOf(false) }

    val themeDisplayName = when (currentTheme) {
        "light" -> strings.Light
        "dark" -> strings.Dark
        else -> strings.Sys
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(strings.sysSetting) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = null)
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(16.dp)
        ) {
            Text(strings.interf, style = MaterialTheme.typography.labelLarge, color = Color.Gray)

            // Mục đổi Theme
            SettingItem(
                icon = Icons.Default.Palette,
                title = strings.themes,
                subtitle = "${strings.current}: $themeDisplayName",
                onClick = { showThemeDialog = true }
            )

            Spacer(modifier = Modifier.height(24.dp))
            Text(strings.security, style = MaterialTheme.typography.labelLarge, color = Color.Gray)

            // Mục đổi mật khẩu
            SettingItem(
                icon = Icons.Default.Lock,
                title = strings.changePass,
                subtitle = strings.updatePass,
                onClick = { showPasswordDialog = true }
            )

            // Mục đổi Ngôn ngữ (Giả lập)
            SettingItem(
                icon = Icons.Default.Language,
                title = strings.language,
                subtitle = if (currentLanguage == AppLanguage.VI) "Tiếng Việt" else "English",
                onClick = { showLangDialog = true }
            )
        }
    }

    // --- Dialog chọn Theme ---
    if (showThemeDialog) {
        AlertDialog(
            onDismissRequest = { showThemeDialog = false },
            title = { Text(strings.selectThemes) },
            text = {
                Column {
                    val options = listOf(
                        "light" to strings.Light,
                        "dark" to strings.Dark,
                        "system" to strings.Sys
                    )
                    options.forEach { (id, label) ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .selectable(
                                    selected = (id == currentTheme),
                                    onClick = {
                                        onThemeChange(id) // Gửi cái ID "dark" về MainActivity
                                        showThemeDialog = false
                                    }
                                )
                                .padding(vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(selected = (id == currentTheme), onClick = null)
                            Text(text = label, modifier = Modifier.padding(start = 16.dp))
                        }
                    }
                }
            },
            confirmButton = {}
        )
    }

    // --- Dialog đổi mật khẩu (Mục 4) ---
    if (showPasswordDialog) {
        var oldPass by remember { mutableStateOf("") }
        var newPass by remember { mutableStateOf("") }
        var error by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showPasswordDialog = false },
            title = { Text(strings.changePass) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = oldPass, onValueChange = { oldPass = it }, label = { Text(strings.oldPass) })
                    OutlinedTextField(value = newPass, onValueChange = { newPass = it }, label = { Text(strings.newPass) })
                    if (error.isNotEmpty()) Text(error, color = Color.Red)
                }
            },
            confirmButton = {
                Button(onClick = {
                    if (onPasswordChange(oldPass, newPass)) {
                        showPasswordDialog = false
                    } else {
                        error = strings.errorPass
                    }
                }) { Text(strings.save) }
            }
        )
    }

    if (showLangDialog) {
        AlertDialog(
            onDismissRequest = { showLangDialog = false },
            title = { Text(strings.language) },
            text = {
                Column {
                    LanguageOption("Tiếng Việt", isSelected = currentLanguage == AppLanguage.VI) {
                        onLanguageChange(AppLanguage.VI)
                        showLangDialog = false
                    }
                    LanguageOption("English", isSelected = currentLanguage == AppLanguage.EN) {
                        onLanguageChange(AppLanguage.EN)
                        showLangDialog = false
                    }
                }
            },
            confirmButton = {}
        )
    }
}

@Composable
fun SettingItem(icon: ImageVector, title: String, subtitle: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        color = Color.Transparent,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.width(16.dp))
            Column {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            }
        }
    }
}

@Composable
fun LanguageOption(name: String, isSelected: Boolean, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().selectable(selected = isSelected, onClick = onClick).padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        RadioButton(selected = isSelected, onClick = null)
        Text(name, modifier = Modifier.padding(start = 16.dp))
    }
}