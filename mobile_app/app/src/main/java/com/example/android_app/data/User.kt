package com.example.android_app.data

data class User(
    val id: Int,
    val username: String,
    val fullName: String = "",
    val password: String = "",
    val avatarUri: String? = null
)