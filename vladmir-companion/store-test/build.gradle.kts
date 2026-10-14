plugins { alias(libs.plugins.android.application) }
android {
    namespace = "app.vladmir.storetest"
    compileSdk = 37
    defaultConfig {
        applicationId = "app.vladmir.storetest"
        minSdk = 25
        targetSdk = 35
        versionCode = providers.gradleProperty("storeFixtureVersion").orElse("1").get().toInt()
        versionName = "0.1.0-test-${versionCode}"
    }
    val store = System.getenv("VLADMIR_ANDROID_KEYSTORE")
    val passwordFile = System.getenv("VLADMIR_ANDROID_KEY_PASSWORD_FILE")
    if (store != null && passwordFile != null) {
        signingConfigs { create("owner") {
            storeFile = file(store)
            val password = file(passwordFile).readText().trim()
            storePassword = password; keyPassword = password; keyAlias = "vladmir-mobile"
        } }
        buildTypes { getByName("release") {signingConfig = signingConfigs.getByName("owner")} }
    }
}
