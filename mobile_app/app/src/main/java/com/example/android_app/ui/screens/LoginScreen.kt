package com.example.android_app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.example.android_app.ui.theme.PrimaryPurple
import com.example.android_app.ui.theme.BackgroundBlack

@Composable
fun LoginScreen(
    onLoginSuccess: (String) -> Unit,
    onNavigateToSignUp: () -> Unit // THÊM THAM SỐ NÀY
) {
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            "Smart Home",
            color = MaterialTheme.colorScheme.onBackground,
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold
        )
        Text("Hệ thống IoT & AI", color = Color.Gray)

        Spacer(modifier = Modifier.height(48.dp))

        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = {Text("Tên đăng nhập")},
            modifier = Modifier.fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(
                focusedTextColor = com.example.android_app.ui.theme.PrimaryPurple,
                unfocusedTextColor = Color.Gray,
                focusedBorderColor = com.example.android_app.ui.theme.PrimaryPurple,
                focusedLabelColor = com.example.android_app.ui.theme.PrimaryPurple,
                unfocusedLabelColor = Color.Gray,
                cursorColor = PrimaryPurple
            )
        )

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Mật khẩu") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(
                focusedTextColor = com.example.android_app.ui.theme.PrimaryPurple,
                unfocusedTextColor = Color.Gray,
                focusedBorderColor = com.example.android_app.ui.theme.PrimaryPurple,
                focusedLabelColor = com.example.android_app.ui.theme.PrimaryPurple,
                unfocusedLabelColor = Color.Gray,
                cursorColor = PrimaryPurple
            )
        )

        Spacer(modifier = Modifier.height(32.dp))

        Button(
            onClick = { if(username.isNotEmpty()) onLoginSuccess(username) },
            modifier = Modifier.fillMaxWidth().height(50.dp),
            colors = ButtonDefaults.buttonColors(containerColor = com.example.android_app.ui.theme.PrimaryPurple)
        ) {
            Text("Đăng nhập", fontWeight = FontWeight.Bold)
        }

        TextButton(onClick = onNavigateToSignUp) {
            Text("Không có tài khoản? Đăng kí tại đây", color = com.example.android_app.ui.theme.PrimaryPurple)
        }
    }
}