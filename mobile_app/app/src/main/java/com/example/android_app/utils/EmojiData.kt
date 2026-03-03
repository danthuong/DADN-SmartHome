package com.example.android_app.utils

data class EmojiCategory(val name: String, val emojis: List<String>)

fun getTranslatedEmojiCategories(strings: AppStrings): List<EmojiCategory> {
    return listOf(
        EmojiCategory(strings.popular, listOf("✨", "💡", "🏠", "🌙", "☀️")),
        EmojiCategory(strings.home, listOf("🛏️", "🛋️", "🛁", "🚿", "🚪", "🍽️", "☕", "🔌", "🔒")),
        EmojiCategory(strings.weahther, listOf("☁️", "❄️", "⚡", "🌅", "🌃", "🌈", "🔥", "💧")),
        EmojiCategory(strings.activity, listOf("🎮", "🎬", "📖", "💤", "🥳", "🏃", "🧘", "🎵", "📺", "🔊")),
        EmojiCategory(strings.other, listOf("🔔", "🚨", "🛡️", "📍", "💎", "🍀", "🌸", "🎨", "🚀", "🛸"))
    )
}