plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "app.vladmir.mobile"
    compileSdk = 37

    defaultConfig {
        applicationId = "app.vladmir.mobile"
        minSdk = 31
        targetSdk = 37
        versionCode = 23
        versionName = "0.3.17"
    }

    val releaseStore = System.getenv("VLADMIR_ANDROID_KEYSTORE")
    val releasePasswordFile = System.getenv("VLADMIR_ANDROID_KEY_PASSWORD_FILE")
    if (releaseStore != null && releasePasswordFile != null) {
        signingConfigs {
            create("owner") {
                storeFile = file(releaseStore)
                val password = file(releasePasswordFile).readText().trim()
                storePassword = password
                keyAlias = "vladmir-mobile"
                keyPassword = password
            }
        }
    }
    buildTypes {
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (releaseStore != null && releasePasswordFile != null) {
                signingConfig = signingConfigs.getByName("owner")
            }
        }
    }

    buildFeatures { compose = true }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    implementation(project(":wear-protocol"))
    implementation("com.google.android.gms:play-services-wearable:20.0.1")
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.activity.compose)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.zxing.android.embedded)
    implementation("androidx.camera:camera-core:1.6.2")
    implementation("androidx.camera:camera-camera2:1.6.2")
    implementation("androidx.camera:camera-lifecycle:1.6.2")
    implementation("androidx.camera:camera-view:1.6.2")
    implementation("io.github.sceneview:arsceneview:4.42.0")
}
