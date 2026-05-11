//package com.example.android_app.data
//
//// Nơi chứa danh sách user tạm thời
//object MockDatabase {
//    val users = mutableListOf<User>(
//        User("Nhi", "nhi", "123")
//    )
//}
//
//class FakeAuthRepository : AuthRepository {
//    override fun login(username: String, password: String): User? {
//        return MockDatabase.users.find { it.username == username && it.password == password }
//    }
//
//    override fun register(user: User): Boolean {
//        if (isUsernameExists(user.username)) return false
//        MockDatabase.users.add(user)
//        return true
//    }
//
//    override fun isUsernameExists(username: String): Boolean {
//        return MockDatabase.users.any { it.username == username }
//    }
//}