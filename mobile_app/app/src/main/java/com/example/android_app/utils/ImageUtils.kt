package com.example.android_app.utils

import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import java.io.File
import java.io.FileOutputStream

object ImageUtils {
    fun saveBitmapToInternalStorage(context: Context, bitmap: Bitmap): Uri? {
        val directory = File(context.filesDir, "Images")
        if (!directory.exists()) directory.mkdirs()

        val file = File(directory, "user_avatar.jpg")
        return try {
            val stream = FileOutputStream(file)
            bitmap.compress(Bitmap.CompressFormat.JPEG, 100, stream)
            stream.flush()
            stream.close()
            Uri.fromFile(file)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}