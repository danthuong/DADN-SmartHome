package com.example.android_app.data

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Looper
import androidx.core.content.ContextCompat
import com.example.android_app.data.api.ApiClient
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume

data class WeatherInfo(
    val temperatureC: Double,
    val description: String,
    val isDay: Boolean
)

object WeatherHelper {

    suspend fun fetchWeatherForCurrentLocation(context: Context): Result<WeatherInfo> {
        if (!hasLocationPermission(context)) {
            return Result.failure(SecurityException("Chưa cấp quyền vị trí"))
        }

        val location = getCurrentLocation(context)
            ?: return Result.failure(IllegalStateException("Không lấy được vị trí"))

        return runCatching {
            val resp = ApiClient.weatherService.getCurrentWeather(
                latitude = location.latitude,
                longitude = location.longitude
            )
            val temp = resp.current?.temperature_2m
                ?: error("API không trả về nhiệt độ")
            val code = resp.current.weather_code ?: 0
            val hour = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
            WeatherInfo(
                temperatureC = temp,
                description = describeWeather(code),
                isDay = hour in 6..17
            )
        }
    }

    fun hasLocationPermission(context: Context): Boolean {
        val fine = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        return fine || coarse
    }

    @Suppress("MissingPermission")
    private suspend fun getCurrentLocation(context: Context): Location? {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

        // 1. Thử lấy last known từ NETWORK rồi GPS (nhanh, không tốn pin).
        val cached: Location? = listOfNotNull(LocationManager.NETWORK_PROVIDER, LocationManager.GPS_PROVIDER)
            .firstNotNullOfOrNull { provider ->
                runCatching { lm.getLastKnownLocation(provider) }.getOrNull()
            }
        if (cached != null) return cached

        // 2. Không có cache → request 1 lần update, chờ tối đa 8s.
        val provider = when {
            lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            lm.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            else -> return null
        }

        return withTimeoutOrNull(8_000) {
            suspendCancellableCoroutine<Location?> { cont ->
                val listener = object : LocationListener {
                    override fun onLocationChanged(loc: Location) {
                        lm.removeUpdates(this)
                        if (cont.isActive) cont.resume(loc)
                    }
                    override fun onProviderDisabled(p: String) {}
                    override fun onProviderEnabled(p: String) {}
                    @Deprecated("Deprecated in API 29+")
                    override fun onStatusChanged(p: String?, status: Int, extras: android.os.Bundle?) {}
                }
                try {
                    lm.requestSingleUpdate(provider, listener, Looper.getMainLooper())
                } catch (e: Exception) {
                    if (cont.isActive) cont.resume(null)
                }
                cont.invokeOnCancellation { lm.removeUpdates(listener) }
            }
        }
    }

    private fun describeWeather(code: Int): String = when (code) {
        0 -> "Trời quang"
        1, 2 -> "Ít mây"
        3 -> "Nhiều mây"
        45, 48 -> "Sương mù"
        51, 53, 55 -> "Mưa phùn"
        56, 57 -> "Mưa phùn đóng băng"
        61, 63, 65 -> "Mưa"
        66, 67 -> "Mưa đóng băng"
        71, 73, 75 -> "Tuyết rơi"
        77 -> "Hạt tuyết"
        80, 81, 82 -> "Mưa rào"
        85, 86 -> "Tuyết rào"
        95 -> "Giông"
        96, 99 -> "Giông kèm mưa đá"
        else -> "Không xác định"
    }
}
