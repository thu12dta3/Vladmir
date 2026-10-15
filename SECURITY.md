# Segurança

Idiomas: [Português](SECURITY.md) · [English](SECURITY.en.md)

## Configuração segura

Nunca adicione chaves de API, senhas, tokens, arquivos de assinatura Android, URLs privadas de câmera ou endereços de rede pessoal ao Git. O arquivo local recomendado é `~/.config/vladmir/config.json`, com permissões `0600`.

A API móvel escuta somente em loopback por padrão. Se você optar por expô-la em outra interface, use um túnel autenticado sob seu controle, limite quem pode acessar e não publique credenciais. Nenhum endereço Tailscale ou serviço remoto vem configurado neste repositório.

## Relato privado

Abra um aviso privado de segurança no GitHub do projeto e inclua os passos mínimos para reproduzir o problema, versão afetada e impacto. Não publique tokens, dados pessoais ou provas de conceito que atinjam terceiros.
