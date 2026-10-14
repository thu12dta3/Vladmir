pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "Vladmir Mobile"
include(":app")

include(":wear", ":wear-protocol")
project(":wear").projectDir = file("../vladmir-wear/app")
project(":wear-protocol").projectDir = file("../vladmir-wear/protocol")

include(":companion", ":store-test")
project(":companion").projectDir = file("../vladmir-companion/app")
project(":store-test").projectDir = file("../vladmir-companion/store-test")
