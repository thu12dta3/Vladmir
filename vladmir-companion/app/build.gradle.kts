plugins { alias(libs.plugins.android.application) }
android {
    namespace = "app.vladmir.companion"
    compileSdk = 37
    defaultConfig {
        applicationId = "app.vladmir.companion"
        minSdk = 31
        targetSdk = 35
        versionCode = 6
        versionName = "0.1.5-persistent-session"
        testInstrumentationRunner = "app.vladmir.companion.CompanionSmokeInstrumentation"
    }
    testBuildType = "release"
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
dependencies {
    implementation(project(":wear-protocol"))
    testImplementation("junit:junit:4.13.2")
}

// Only our own signed fixture; generated artifact stays outside Git.
val generatedStore = layout.buildDirectory.dir("generated/store-assets")
val storeFixture = tasks.register<Copy>("prepareStoreFixture") {
    dependsOn(":store-test:assembleRelease")
    from(project(":store-test").layout.buildDirectory.file("outputs/apk/release/store-test-release.apk"))
    into(generatedStore)
    rename { "vladmir-store-test.apk" }
}
android.sourceSets.getByName("main").assets.srcDir(generatedStore.get().asFile)
tasks.named("preBuild").configure { dependsOn(storeFixture) }
