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
import com.example.android_app.ui.theme.*

@Composable
fun SignUpScreen(
    onSignUpSuccess: (String) -> Unit,
    onBackToLogin: () -> Unit
) {
    var name by remember { mutableStateOf("") }
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
        Text("Tạo tài khoản", color = MaterialTheme.colorScheme.onBackground, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)

        Spacer(modifier = Modifier.height(32.dp))

        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            label = { Text("Họ & tên") },
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
            value = username,
            onValueChange = { username = it },
            label = { Text("Tên đăng nhập") },
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
            onClick = { if(name.isNotEmpty()) onSignUpSuccess(name) },
            modifier = Modifier.fillMaxWidth().height(50.dp),
            colors = ButtonDefaults.buttonColors(containerColor = PrimaryPurple)
        ) {
            Text("Đăng kí")
        }

        TextButton(onClick = onBackToLogin) {
            Text("Đã có tài khoản? Đăng nhập tại đây", color = PrimaryPurple)
        }
    }
}