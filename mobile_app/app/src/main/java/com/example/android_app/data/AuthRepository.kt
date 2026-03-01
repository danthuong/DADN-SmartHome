package com.example.android_app.data

interface AuthRepository {
    fun login(username: String, password: String): User?
    fun register(user: User): Boolean
    fun isUsernameExists(username: String): Boolean
}