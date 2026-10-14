# Configuração local

Use `config.example.json` como referência para criar `~/.config/vladmir/config.json`. O arquivo ativo não deve ser adicionado ao Git; use permissões `0600`. Não coloque senhas em logs ou exemplos.

Os dados ficam em `~/.local/share/vladmir` e `~/.local/state/vladmir`. `VLADMIR_CONFIG` aponta para outro arquivo de configuração. O Vladmir usa somente variáveis de ambiente com prefixo `VLADMIR_`; ele não lê configurações ou credenciais do MARK.

O Ollama usa `http://127.0.0.1:11434` por padrão. A URL da câmera, credenciais e portas precisam ser configuradas somente na máquina local; o exemplo vem sem host de câmera. A pesquisa web e provedores externos podem ser desativados na configuração.
