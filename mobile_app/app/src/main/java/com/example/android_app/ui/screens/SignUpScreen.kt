package com.example.android_app.ui.screens

import android.content.Context
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
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
fun SignUpScreen(
    strings: AppStrings,
    onSignUpSuccess: (User) -> Unit,
    onBackToLogin: () -> Unit
) {
    val context = LocalContext.current
    var name by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }

    Box(modifier = Modifier.fillMaxSize()) {
        // Ảnh nền
        Image(
            painter = painterResource(id = R.drawable.background),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = strings.signUp,
                color = MaterialTheme.colorScheme.onBackground,
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(32.dp))

            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text(strings.fullName) },
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
                value = username,
                onValueChange = { username = it },
                label = { Text(strings.username) },
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
                label = { Text(strings.password) },
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
                    if (username.isNotEmpty() && password.isNotEmpty()) {
                        isLoading = true
                        errorMessage = ""

                        CoroutineScope(Dispatchers.IO).launch {
                            val result = SmartHomeRepository.register(username, password)

                            withContext(Dispatchers.Main) {
                                isLoading = false
                                result.fold(
                                    onSuccess = { response ->
                                        // Save token to memory and SharedPrefs
                                        SmartHomeRepository.setToken(response.token)
                                        SmartHomeRepository.saveToken(response.token, context)
                                        
                                        // Save full name locally
                                        val prefs = context.getSharedPreferences("UserPrefs", Context.MODE_PRIVATE)
                                        prefs.edit().putString("fullname_${response.username}", name).apply()
                                        
                                        onSignUpSuccess(User(response.user_id, response.username, fullName = name))
                                    },
                                    onFailure = { exception ->
                                        errorMessage = exception.message ?: "Registration failed"
                                    }
                                )
                            }
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
                    Text(strings.signUp)
                }
            }

            if (errorMessage.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(errorMessage, color = Color.Red, style = MaterialTheme.typography.bodySmall)
            }

            TextButton(onClick = onBackToLogin) {
                Text(
                    text = strings.loginAsk,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}