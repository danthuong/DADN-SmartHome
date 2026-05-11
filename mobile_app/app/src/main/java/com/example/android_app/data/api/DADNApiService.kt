package com.example.android_app.data.api

import retrofit2.http.*

interface DADNApiService {
    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    @POST("api/auth/register")
    suspend fun register(@Body request: RegisterRequest): RegisterResponse

    @GET("api/devices")
    suspend fun getDevices(@Header("Authorization") token: String): DevicesResponse

    @POST("api/devices")
    suspend fun createDevice(
        @Header("Authorization") token: String,
        @Body request: DeviceCreateRequest
    ): DeviceCreateResponse

    @POST("api/devices/{id}/control")
    suspend fun controlDevice(
        @Header("Authorization") token: String,
        @Path("id") deviceId: String,
        @Body control: DeviceControlRequest
    ): ControlResponse

    @DELETE("api/devices/{id}")
    suspend fun deleteDevice(
        @Header("Authorization") token: String,
        @Path("id") deviceId: String
    ): DeleteDeviceResponse

    @GET("api/rooms")
    suspend fun getRooms(@Header("Authorization") token: String): RoomsResponse

    @POST("api/rooms")
    suspend fun createRoom(
        @Header("Authorization") token: String,
        @Body request: RoomCreateRequest
    ): DeleteDeviceResponse

    @DELETE("api/rooms/{id}")
    suspend fun deleteRoom(
        @Header("Authorization") token: String,
        @Path("id") roomId: String
    ): DeleteDeviceResponse

    @GET("api/status")
    suspend fun getStatus(@Header("Authorization") token: String): StatusResponse

    @POST("api/users/avatar")
    suspend fun updateAvatar(
        @Header("Authorization") token: String,
        @Body request: AvatarUpdateRequest
    ): AvatarResponse

    @GET("api/users/avatar")
    suspend fun getAvatar(@Header("Authorization") token: String): AvatarResponse

    @GET("api/presets")
    suspend fun getPresets(@Header("Authorization") token: String): PresetsResponse

    @POST("api/presets")
    suspend fun createPreset(
        @Header("Authorization") token: String,
        @Body request: PresetCreateRequest
    ): DeleteDeviceResponse

    @PUT("api/presets/{id}")
    suspend fun updatePreset(
        @Header("Authorization") token: String,
        @Path("id") presetId: String,
        @Body request: PresetUpdateRequest
    ): DeleteDeviceResponse

    @DELETE("api/presets/{id}")
    suspend fun deletePreset(
        @Header("Authorization") token: String,
        @Path("id") presetId: String
    ): DeleteDeviceResponse
}
