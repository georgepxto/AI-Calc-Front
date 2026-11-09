# AI Calc: lista de conferência (Etapas 3 a 5)

Marque cada item depois de testar. Abra o app com:

```
C:\Users\fcoau\.venvs\ai_calc\Scripts\python -m ai_calc
```

(rodando na pasta do projeto). Para os testes automáticos: `C:\Users\fcoau\.venvs\ai_calc\Scripts\python -m pytest`.

Os arquivos do app ficam em `%APPDATA%\AI Calc` (cole isso na barra de endereço do Explorador
de Arquivos): `historico.json` e `preferencias.json`. Eles só aparecem depois da primeira
conta ou da primeira mudança de tema, modo ou aba.

## 1. Contas (aba Comum)

- [ ] `2 + 3 =` dá 5; `200 + 10 % =` dá 220; `, 5 × 3 =` dá 1,5.
- [ ] Depois do `=`, um operador continua do resultado (`× 2 =`); um número começa conta nova.
- [ ] `5 ÷ 0 =` mostra "Divisão por zero inválida" e o app continua aberto.
- [ ] `2 ( 3 + 4 ) =` mostra "Interpretado como: 2 × (3 + 4)".
- [ ] Teclado físico: `12*3-6/2` e Enter dá 33; `.` vira vírgula; Backspace apaga; Esc limpa.

## 2. Aba Científica

- [ ] `sin 30 ) =` dá 0,5 em DEG; tecla DEG vira RAD e o canto do visor acompanha.
- [ ] Em RAD, `sin π ÷ 2 ) =` dá 1. `tan 90 ) =` em DEG mostra "Indefinida".
- [ ] `ⁿ√ 3 ; − 8 ) =` dá -2; `2 − 8 =` e depois `x² =` dá 36.
- [ ] Na largura mínima (360 × 560) todas as teclas aparecem inteiras.

## 3. Tema, vidro e movimento

- [ ] Sem escolha salva, o app abre no tema do Windows (Configurações › Personalização › Cores).
- [ ] O botão de lua/sol troca o tema em cerca de meio segundo; tudo muda junto
      (fundo, visor, teclas, abas, ícones, histórico e janela de confirmação).
- [ ] Dois cliques rápidos: a animação volta do ponto onde estava, sem travar.
- [ ] Clique nas teclas: afundam um pouco; passar o mouse clareia.
- [ ] **Reduzir movimento**: Configurações › Acessibilidade › Efeitos visuais › desligue
      "Efeitos de animação". A troca de tema fica instantânea, as teclas não animam e a gaveta
      do histórico aparece sem deslizar. Religue depois.

## 4. Histórico

- [ ] Janela larga (a partir de 660 px): o painel do histórico fica à direita.
- [ ] Janela estreita: aparece o botão de relógio; ele abre a gaveta, que fecha com ✕, com Esc,
      com o mesmo botão ou ao escolher um número.
- [ ] Contas certas entram (mais nova em cima); contas com erro não entram; máximo de 20.
- [ ] Contas com seno, cosseno ou tangente mostram DEG ou RAD; as outras não.
- [ ] Clicar num item insere só o número. Um número negativo entra entre parênteses: `(-6)`.
- [ ] Com mais itens do que cabem, a barra de rolagem aparece fina e nas cores do tema.
- [ ] "Limpar" abre a confirmação de vidro (não a janela padrão do Windows); "Cancelar" mantém,
      Esc cancela, "Limpar" apaga.
- [ ] Feche e abra o app: o histórico continua lá.

## 5. Preferências

- [ ] Escolha o tema escuro, o modo RAD e a aba Científica; feche e abra: tudo volta igual.
- [ ] A escolha salva de tema vale mesmo se o Windows estiver no outro tema.

## 6. Arquivo corrompido (simulação)

1. Feche o app.
2. Abra `%APPDATA%\AI Calc\historico.json` no Bloco de Notas, apague um pedaço
   (por exemplo, a última chave `}`) e salve.
3. Abra o app: ele abre normalmente com o histórico vazio.
4. Na pasta aparece `historico.corrompido-AAAAMMDD-HHMMSS.json` (o arquivo estragado guardado).
5. Faça uma conta: um `historico.json` novo é criado.
6. Repita com `preferencias.json`: o app abre no padrão (tema do Windows, DEG, aba Comum) e
   guarda `preferencias.corrompido-...json`.

## 7. Acessibilidade

- [ ] Tab percorre abas, botões do topo, teclas, Limpar e itens do histórico, com contorno de
      foco visível nos dois temas; Espaço aperta o item em foco.
- [ ] Na confirmação, o foco começa em "Cancelar" e o Tab só circula entre os dois botões.
- [ ] Com o Narrador do Windows (Ctrl + Win + Enter), as teclas e itens são lidos pelo nome
      (ex.: "Multiplicar", "sin(30) igual a 0,5, graus", "Limpar histórico").

## 8. Trigonometria (Etapa 4)

- [ ] A aba abre em 30°, sem o visor da calculadora e sem o painel fixo do histórico (o botão de
      relógio continua abrindo a gaveta).
- [ ] Arraste o ponto pelos quatro quadrantes: valores, sinais, quadrante e a marca nos gráficos
      acompanham. Perto de 30°, 45°, 60°… ele encaixa; fora deles, fica em graus inteiros.
- [ ] Clique no círculo e use as setas (Shift: 15°; Home: 0°).
- [ ] Seno `0,5` + Enter → 30°; "Outra: 150°" → 150°. Seno `1` → 90°, botão "Solução única"
      desativado e tangente "indefinida".
- [ ] Ângulo `450` → 90°; `-30` → 330°. Seno `2` mostra o aviso vermelho dentro do painel.
- [ ] DEG → RAD: campo mostra `π/6`, eixo dos gráficos mostra `π/2`, `π`, `3π/2`, `2π`.
- [ ] Ao digitar um ângulo ou usar "Outra", o ponto desliza pelo caminho mais curto
      (de 30° para 330° passa por 0°). Com "reduzir movimento", vai direto.
- [ ] Gráficos: a tangente "quebra" em 90° e 270° (linhas tracejadas) e cada curva tem rótulo
      e estilo de linha próprios.
- [ ] Janela larga: círculo e gráficos lado a lado. Janela estreita (360 × 560): seletor
      "Círculo | Gráficos" e tudo cabe.
- [ ] Tab passa por seletor, círculo, campos e botões; o Narrador lê o círculo como
      "Ângulo 30 graus, 1º quadrante, seno 0,5, …".

## 9. Acabamento (Etapa 5A)

- [ ] Botões **sen / cos / tan** no topo da aba Trigonometria: desligar a tangente tira a linha do
      círculo, a curva dos gráficos e a linha do painel. O botão desligado fica riscado.
- [ ] Desligue duas funções: a que sobrou fica bloqueada. Feche e abra o app: a escolha continua.
- [ ] Gire o ponto pelos quatro quadrantes: o número do quadrante não fica embaixo do raio nem
      em cima do rótulo "sen".
- [ ] Janela estreita, seno `-0,707106781187`: o texto do campo diminui e cabe.
- [ ] Trocar de aba, trocar Círculo/Gráficos e apertar "=" esmaecem rapidamente; com
      "reduzir movimento", trocam na hora.
- [ ] O ícone do AI Calc (calculadora com a onda do seno) aparece na janela e na barra de
      tarefas (não o do Python).

## 10. Executável (Etapa 5B)

- [ ] Baixe o executável do Windows em **Assets** na página de Releases (ou gere com `tools/gerar_executavel.py`).
- [ ] Abra com dois cliques. Se aparecer "O Windows protegeu o computador": Mais informações →
      Executar assim mesmo.
- [ ] O ícone da calculadora aparece no arquivo, na janela e na barra de tarefas.
- [ ] Não abre janela preta de console junto.
- [ ] O histórico e as preferências são os mesmos de quando o app roda pelo Python
      (mesma pasta `%APPDATA%\AI Calc`).
- [ ] Repita rapidamente as seções 1, 4 e 8 no executável.

## 11. Painel Porcentagem (Etapa 6)

- [ ] No executável, na aba **Comum**, digite `200 ×`. Abra **Porcentagem**,
      calcule **36 de 240** e confira `15%`. Clique em **Usar resultado** e
      depois em `=`. O visor deve mostrar `30`.
- [ ] Em **Variação**, calcule de 240 para 204 e confira `−15%`.
- [ ] Em **Desconto** (valor original), informe 150 e desconto de 25% e confira `200`.
      Repita com `25,0` e `25.0`.
- [ ] Informe total ou valor inicial zero, desconto de 100% ou um campo
      inválido. Confira a mensagem de erro e o bloqueio da inserção.
- [ ] Após um cálculo válido, altere um campo ou troque a operação.
      **Usar resultado** deve ficar desabilitado até um novo cálculo válido.
- [ ] Na largura mínima, confira o alinhamento ao abrir e fechar a gaveta
      do histórico. Teste nos temas claro e escuro.
- [ ] Com o painel aberto, Tab e Shift+Tab pulam teclas encobertas.
      Pressione Esc com um campo em foco e confira o retorno ao botão.
