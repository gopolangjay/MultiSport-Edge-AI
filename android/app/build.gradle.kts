plugins { id("com.android.application") }

android {
    namespace = "za.co.multisportedge"
    compileSdk = 35

    defaultConfig {
        applicationId = "za.co.multisportedge"
        minSdk = 24
        targetSdk = 35
        versionCode = 2
        versionName = "1.1.0-private"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}
