# Third-party components in the Android app

Vladmir's original code is distributed under the MIT License, as described in the repository-root `LICENSE`. Included libraries keep their own licenses.

- [ZXing Android Embedded](https://github.com/journeyapps/zxing-android-embedded), version 4.3.0: Apache License 2.0. Used to scan pairing QR codes.
- [ZXing Core](https://github.com/zxing/zxing): Apache License 2.0, transitive dependency of the QR reader.
- AndroidX/Jetpack Compose and Kotlin: their respective licenses are distributed by their authors and Gradle dependencies.

The build does not embed owner credentials. The signing file and its password remain on the PC, outside the repository.

[Português](THIRD_PARTY.md) · [English](THIRD_PARTY.en.md)
