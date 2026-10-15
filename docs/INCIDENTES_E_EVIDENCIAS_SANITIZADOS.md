# Incidentes e evidências de desenvolvimento — versão sanitizada

Este apêndice reúne exemplos reais de investigação e validação registrados durante o desenvolvimento relacionado ao MARK. Ele complementa a apresentação pública do Vladmir com falhas, correções e limites observados, sem publicar registros brutos.

## Proveniência e limites

- Os relatos foram derivados de relatórios internos do MARK, projeto relacionado e separado do repositório público Vladmir.
- Os resultados abaixo **não certificam o Vladmir atual**, não provam que cada componente tenha código idêntico e não substituem validação reproduzível no repositório público.
- Os registros originais incluem logs e informações locais. Nenhum log, configuração, credencial, imagem original ou dump foi copiado para este documento.
- Foram omitidos nomes de usuário, emails, endereços de rede, domínios privados, nomes Bluetooth, números de série, caminhos pessoais, chaves, tokens e identificadores de sessão/dispositivo.
- Nenhuma captura de tela do Recovery foi republicada; ela continha detalhes de aparelho e contexto. A evidência é descrita em texto agregado.

## Caso 1 — revisão adversarial da API móvel

**Período:** 30/09/2026. **Alvo:** versão de teste do MARK Mobile e uma cópia local da API do MARK. **Tipo:** inspeção do APK/código e requisições locais de laboratório.

### O que aconteceu

A revisão encontrou problemas concretos na autorização de histórico, na ordem de validação de requisições, no tratamento de campos malformados e nos limites de leitura de respostas. Em um caso histórico, um cliente legado autenticado ainda conseguia ler histórico depois de uma opção de bloqueio ser ativada. Em outro, o servidor começava a aguardar um corpo grande antes de negar uma identidade sem sessão válida. Esses resultados pertencem à versão avaliada naquela campanha; credenciais e o conteúdo sentinela não são publicados.

### Correção e evidência registrada

- O bloqueio passou a ser verificado também para clientes legados e antes da entrega de resposta em andamento; o caso de regressão corrigido negou o histórico.
- A identidade passou a ser conferida antes de ler o corpo. O cenário sem sessão recebeu rejeição imediata no teste local.
- Tipos inválidos, caracteres não ASCII na autenticação e enquadramento ambíguo de cabeçalhos passaram a ser rejeitados com erro controlado.
- Leituras de respostas e PDFs escolhidos pelo usuário receberam limites por tamanho real dos bytes.
- O relatório daquela campanha registrou **165 testes Python aprovados** (150 existentes e 15 cenários adversariais) e mais de **950 requisições** nos cenários de mutação, repetição, pareamento e rotação de sessão.

### O que não foi demonstrado

O celular não estava conectado durante o teste de segurança. Parte dos casos TLS foi exercitada com uma classe Kotlin compilada em uma JVM e certificados de laboratório; isso não equivale a ataque MITM contra o app instalado. Não houve teste de OOM físico, revisão integral de todas as dependências ou auditoria completa de APK. O relatório original manteve o status **SECURITY INCOMPLETE**.

**Fonte interna:** relatório de red team do MARK Mobile/API, datado de 30/09/2026. Os artefatos brutos permaneceram privados.

## Caso 2 — recuperação após remover uma dependência do sistema do relógio

**Período:** 10/10/2026. **Alvo:** app Wear OS e serviços originais do fabricante em um relógio de teste. **Tipo:** foto fornecida pelo proprietário, logs de sistema obtidos em janela USB e observação posterior.

### O que aconteceu

Depois que um pacote OEM de saúde foi removido durante uma limpeza solicitada, um serviço persistente do relógio passou a falhar repetidamente porque não encontrava um provedor de passos fornecido por aquele pacote. O proprietário observou a tela Android Recovery com a mensagem de que o sistema não podia carregar. A relação entre o crash loop e o Recovery era uma hipótese sustentada pelos logs e pelo mecanismo do Android, não uma reconstrução perfeita de todo o histórico do boot.

### Recuperação e resultado observado

- O pacote OEM original foi restaurado para o usuário principal; não houve comando de factory reset, wipe, root ou alteração de partição.
- Em amostras posteriores, o serviço voltou a encontrar o provedor e não houve novas falhas Java daquele serviço no buffer observado.
- Após reinício normal, o relógio voltou ao mostrador. A observação mais longa registrada chegou a aproximadamente **53 minutos** na mesma inicialização, sem novas falhas Java observadas do serviço investigado.

### Limites

Persistiram erros nativos sem causa isolada e instabilidade na janela de comunicação USB. O período observado não certifica estabilidade prolongada, GPS, sensores, configurações intactas nem ausência de outros defeitos. A conclusão prática foi preservar a dependência OEM até existir alternativa comprovada.

**Fonte interna:** relatório de recuperação do Companion/Wear, datado de 10/10/2026. Foto e dumps originais não foram republicados.

## Caso 3 — música em mono ao iniciar chamadas

**Período:** 11/10/2026. **Alvo:** roteamento de áudio de uma instalação Linux com fone Bluetooth e chamada. **Tipo:** inspeção do estado do servidor de áudio, configuração do serviço local e confirmação do usuário.

### Diagnóstico e correção

O serviço de escuta seguia a entrada de microfone padrão. Quando um microfone separado não estava disponível, o sistema usava o microfone do fone Bluetooth e mudava a conexão para o perfil de chamada HFP/mSBC, que naquele aparelho entregava áudio de reprodução mono. O player de música também estava saindo em mono.

O ajuste daquela máquina separou o microfone da saída do fone, manteve A2DP estéreo como perfil de reprodução e encaminhou os fluxos de música para dois canais a 48 kHz. O usuário confirmou que a música voltou ao normal e o áudio direcional estéreo permaneceu.

### Limites

Essa foi uma correção local de roteamento, não uma mudança universal do Vladmir. Com essa política, o microfone do fone Bluetooth clássico não é usado para a chamada; é necessário outro microfone. O teste não garante comportamento idêntico em outras versões de PipeWire, perfis Bluetooth ou headsets.

**Fonte interna:** relatório de áudio estéreo do MARK, datado de 11/10/2026. Configuração anterior e backups privados não foram copiados.

## Caso 4 — câmera e reconhecimento visual em tempo real

**Período:** 11/10/2026. **Alvo:** captura local de câmera USB no desktop e modelo de visão local já instalado. **Tipo:** captura física, inferências locais e conjunto pequeno de imagens de avaliação.

### Evidências registradas

- Captura pontual de um quadro de **1280 × 720** em cerca de **1,02 s** naquela configuração.
- Em uma amostra de fluxo físico, foram recebidos 195 quadros em aproximadamente 20 segundos; isso mede captura, não taxa de inferência da IA.
- Quatro imagens de teste conhecidas passaram tarefas visuais definidas pelos autores. Em outra comparação, quatro imagens passaram tanto com a cena inteira como com recorte; o recorte não demonstrou ganho de precisão e elevou a latência média medida de **1,52 s para 2,29 s**.
- A suíte de regressão do MARK registrou **327 testes aprovados** naquela etapa, incluindo cenários de validação de imagem, concorrência e encerramento.

### Limites

O conjunto era pequeno, conhecido e não cego; não permite inferir precisão geral. A captura física não prova que a câmera funcione em outros computadores, sob baixa luz ou com fontes RTSP. Os resultados de teste pertencem ao MARK e não são um benchmark independente do Vladmir.

**Fonte interna:** relatórios de visão ao vivo e foco do MARK, datados de 11/10/2026. Nenhuma foto real da câmera ou descrição de cena privada foi publicada.

## Caso 5 — ajuste de modelo sem ganho demonstrado

**Período:** 11/10/2026. **Alvo:** experimento local de adaptadores QLoRA para um modelo base existente. **Tipo:** treino isolado, comparação de respostas e relatório agregado.

### Resultado

Dois candidatos completaram 14 atualizações cada usando 56 exemplos de treino por rodada. O primeiro reduziu a loss, mas regrediu em respostas qualitativas e foi rejeitado. O segundo preservou aproximadamente as respostas iniciais, sem ganho claro. **Nenhum adaptador foi ativado**; os modelos base foram mantidos.

### Limites

A avaliação era pequena e não cega; câmera, voz, AR e segurança ampla dos pesos não foram avaliados. O resultado é evidência de que a rodada não justificou trocar os modelos, não prova de melhoria geral ou de inexistência de outras oportunidades de treino.

**Fonte interna:** relatório de treino experimental do MARK, datado de 11/10/2026. Pesos, checkpoints e dataset permanecem locais e não foram copiados.

## Estado de recursos móveis que não devem ser anunciados como concluídos

Um relatório de teste do aplicativo Android registrou que o app abriu e a tela AR apareceu em um aparelho; detecção física de planos, colocação do objeto, nitidez da câmera e mapa persistente ainda não estavam comprovados. A AR não guardava o mapa ao sair da sessão. Em paralelo, a ponte Companion/Wear teve observação de “offline ao bloquear o telefone”; versões posteriores mantiveram serviço em foreground numa sessão com tela apagada, mas a autorização temporária expirava e reconexão durável continuava pendente.

Esses exemplos ilustram por que compilar um APK ou abrir uma tela não deve ser descrito como prova de funcionamento físico completo. Os resultados são históricos e devem ser conferidos novamente antes de qualquer alegação sobre a versão atual.

## Para transformar estes relatos em prova pública reproduzível

1. Criar casos de teste sintéticos e seguros no repositório público, sem importar banco, token, dump ou configuração privada do MARK.
2. Publicar comandos e fixtures autorais com licenças claras; documentar versão exata e hash do código testado.
3. Adicionar CI no Vladmir e publicar o resultado real da execução antes de usar badges ou afirmar que o pipeline está verde.
4. Repetir ensaios físicos apenas com escopo e aparelho declarados, sem publicar números de série, contas, IPs ou conteúdo privado.
5. Manter explícita a origem: resultados do MARK são experiência de desenvolvimento relacionada, não certificação independente do Vladmir.
