package com.example.android_app.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.android_app.data.SmartHomeRepository
import com.example.android_app.data.User
import com.example.android_app.utils.AppStrings
import com.example.android_app.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun LoginScreen(
    strings: AppStrings,
    onLoginSuccess: (User) -> Unit,
    onNavigateToSignUp: () -> Unit
) {
    val context = LocalContext.current
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }

    Box(modifier = Modifier.fillMaxSize()) {

        // 1. LỚP DƯỚI CÙNG: ẢNH NỀN
        Image(
            painter = painterResource(id = R.drawable.background), // Tên file ảnh của bạn
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop // Phủ kín màn hình
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
//                .background(MaterialTheme.colorScheme.background)
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "YOLO HOME",
                color = MaterialTheme.colorScheme.onBackground,
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(48.dp))

            OutlinedTextField(
                value = username,
                onValueChange = { username = it },
                label = { Text(strings.username) }, // Dùng strings.username
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = MaterialTheme.colorScheme.primary,
                    unfocusedTextColor = Color.Gray,
                    focusedBorderColor = MaterialTheme.colorScheme.primary,
                    focusedLabelColor = MaterialTheme.colorScheme.primary,
                    unfocusedLabelColor = Color.Gray,
                    cursorColor = MaterialTheme.colorScheme.primary
                )
            )

            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text(strings.password) }, // Dùng strings.password
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = MaterialTheme.colorScheme.primary,
                    unfocusedTextColor = Color.Gray,
                    focusedBorderColor = MaterialTheme.colorScheme.primary,
                    focusedLabelColor = MaterialTheme.colorScheme.primary,
                    unfocusedLabelColor = Color.Gray,
                    cursorColor = MaterialTheme.colorScheme.primary
                )
            )

            Spacer(modifier = Modifier.height(32.dp))

            Button(
                onClick = {
                    isLoading = true
                    errorMessage = ""
                    
                    // Gọi API login
                    CoroutineScope(Dispatchers.IO).launch {
                        val result = SmartHomeRepository.login(username, password)
                        
                        withContext(Dispatchers.Main) {
                            isLoading = false
                            result.fold(
                                onSuccess = { response ->
                                    // Save token to memory and SharedPrefs
                                    SmartHomeRepository.setToken(response.token)
                                    SmartHomeRepository.saveToken(response.token, context)
                                    // Login thành công - chuyển sang Dashboard
                                    onLoginSuccess(User(response.user_id, response.username))
                                },
                                onFailure = { exception ->
                                    // Login thất bại - hiển thị lỗi
                                    errorMessage = exception.message ?: "Login failed"
                                }
                            )
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(50.dp),
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text(text = strings.login, fontWeight = FontWeight.Bold)
                }
            }

            TextButton(onClick = onNavigateToSignUp) {
                Text(
                    text = strings.signUpAsk,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            if (errorMessage.isNotEmpty()) {
                Text(errorMessage, color = Color.Red, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}