# Vladmir Mobile

Idiomas: [Português](README.md) · [English](README.en.md)

Aplicativo Android nativo em Kotlin e Jetpack Compose. A interface móvel pode conversar com a API local do Vladmir; câmera, voz, AR e ponte com Wear OS são recursos opcionais.

## Compilar

Use Android Studio com o SDK e JDK compatíveis com a versão do Gradle. A partir desta pasta, execute `./gradlew assembleDebug lintDebug`. Para assinar uma versão de distribuição, forneça `VLADMIR_ANDROID_KEYSTORE` e `VLADMIR_ANDROID_KEY_PASSWORD_FILE` por variáveis de ambiente locais. Nunca versione keystores, senhas ou APKs assinados.

O APK de depuração aparece em `app/build/outputs/apk/debug/`. O aplicativo exige configuração e autorização no PC para acessar o servidor; nenhum endereço pessoal é pré-configurado. Para acesso fora da rede local, o operador precisa fornecer um endereço HTTPS seguro e aprovar o pareamento no Vladmir.
