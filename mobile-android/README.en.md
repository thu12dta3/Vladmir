# Vladmir Mobile

Native Android application written in Kotlin and Jetpack Compose. The mobile UI can connect to the Vladmir local API; camera, voice, AR, and Wear OS bridge are optional features.

## Build

Use Android Studio with an SDK and JDK compatible with the Gradle version. From this directory, run `./gradlew assembleDebug lintDebug`. To sign a release build, provide `VLADMIR_ANDROID_KEYSTORE` and `VLADMIR_ANDROID_KEY_PASSWORD_FILE` through local environment variables. Never commit keystores, passwords, or signed APKs.

The debug APK is generated at `app/build/outputs/apk/debug/`. The app requires local configuration and PC authorization to access the server; no personal address is preconfigured. For access outside the local network, the operator must provide a secure HTTPS address and approve pairing in Vladmir.

[Português](README.md) · [English](README.en.md)
