package com.example.android_app.data

data class User(
    val fullName: String,
    val username: String,
    val password: String,
    val avatarUri: String? = null // Lưu đường dẫn ảnh avatar
)