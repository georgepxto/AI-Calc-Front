# AI Calc: contexto do projeto

Calculadora desktop em Python (PySide6), em português do Brasil, com três modos:
Comum, Científica e Trigonometria (círculo trigonométrico interativo).
Leia também `docs/ESPECIFICACAO.md`: ela tem todas as decisões já aprovadas
(pontos 1 a 7) e deve ser seguida à risca.

## Sobre quem está pedindo

- Francisco, iniciante em programação, fazendo uma imersão da Alura em engenharia de software com IA.
- Fala português. Explique em linguagem simples, sem pressa de despejar código.
- Método combinado: **um passo de cada vez**. Apresente o que vai fazer, espere o "ok" e só então siga para a próxima etapa.
- Avise sempre que mudar algo que não foi aprovado e liste essas decisões ao final.

## Estado atual

| Etapa | Conteúdo | Status |
|---|---|---|
| 1 | Motor de cálculo e testes (`ai_calc/core`) | feita |
| 2 | Lógica da trigonometria (`core/trig.py`) | feita (271 testes passando no total) |
| 3A | Janela, visor e teclado Comum (com teclado físico), visual simples | feita |
| 3B | Teclado Científico, DEG/RAD e botão de tema (troca simples) | feita |
| 3C | Transição suave do tema e visual de vidro | feita |
| 3D | Histórico, preferências e lista de conferência final | feita |
| 4A | Aba Trigonometria: círculo interativo, painel e campos | feita |
| 4B | Gráficos, layout largo/estreito, animação do ponto, conferência | feita |
| 5A | Liga/desliga das funções, ajustes visuais, transições, ícone, licença | feita |
| 5B | Executável (PyInstaller) em Release no GitHub, revisão final, docs | feita (576 testes no total) |

Comandos (da raiz do projeto): `pip install -r requirements.txt`, `pytest` e `python -m ai_calc` (abre o app).
Os testes de janela usam pytest-qt em modo offscreen (`tests/conftest.py`).
Ambiente virtual: `.venv` na raiz do projeto (ignorado pelo git). Atenção: o PySide6 não
carrega se o caminho do ambiente for longo demais (limite do Windows); por isso o projeto
fica numa pasta de caminho curto (`C:\Projetos\AI-Calc`).
Rodar com `.venv\Scripts\python -m ai_calc` e `.venv\Scripts\python -m pytest`.

## Regras de arquitetura

- `ai_calc/core` NÃO pode importar nada de interface. Toda lógica nova fica lá e é testada com pytest.
- Nunca usar `eval()` nem `exec()`. O cálculo passa pelo tokenizador, parser e avaliador próprios.
- Erros do usuário são `CalcError` (mensagens em português já definidas em `core/errors.py`). O app nunca pode fechar por causa de uma conta.
- Limites e tolerâncias ficam em `core/limits.py`.
- Números exibidos com vírgula decimal, 12 dígitos significativos, sem separador de milhar.

## Etapa 2 (feita): lógica do círculo em `core/trig.py`

- O círculo guarda o ângulo sempre em graus, em [0°, 360°) (360° vira 0°); radianos só na exibição.
- Funções: `normalize_degrees`, `quadrant`/`quadrant_label` ("1º quadrante"… ou "Sobre o eixo"),
  `circle_values` (tangente `None` quando indefinida), `signs` ("+", "-", "0" ou "indefinida"),
  `side_of`, `angles_from_sin` (devolve (direita, esquerda) ou uma solução só em ±1) e `periodicity_text`.
- Em RAD, `radians_text` escreve os notáveis como fração de π (`π/6`, `3π/4`) e os demais com 4 casas (`0,1745`).
- `TrigCircleState` é o que a interface da Etapa 4 vai usar: `set_angle`, `set_sin`, `toggle`,
  `can_toggle`, `side` (começa na direita; mantido em 90° e 270°).
- Seno fora de [−1, 1]: "Valor fora do domínio". Testes em `tests/test_trig_circle.py`.

## Etapa 3A (feita)

- `core/editor.py` (`ExpressionEditor`): o que cada tecla faz (inserir, apagar, limpar, calcular).
  Depois do "=", operador continua do resultado; número começa conta nova; "," no começo vira "0,".
- `ui/`: `app.py` (estilo Fusion, fonte Segoe UI Variable com reserva em Segoe UI),
  `main_window.py` (abas, teclado físico), `display.py` (visor), `keypad.py` (teclas a partir de listas).
- Toda tecla tem `accessibleName`, recebe foco com Tab e mostra contorno de foco visível.

## Etapa 3B (feita)

- Teclado Científico (`SCIENTIFIC_KEYS`, 5 colunas, teclas de 34 px de altura mínima) com tecla
  DEG/RAD; o modo também aparece no canto do visor e vale para as duas abas.
- Botão de tema no topo, ícone de lua/sol. Abre no tema do Windows
  (`styleHints().colorScheme()`); a escolha ainda não é salva (3D).

## Etapa 3C (feita)

- Sem folha de estilo (QSS): tudo é desenhado à mão como vidro (`ui/glass.py`: `paint_glass`,
  `Backdrop`; `ui/glass_button.py`: `GlassButton`, `ThemeToggleButton`; `ui/tabs.py`: `GlassTabBar`;
  visor em `ui/display.py`). Cada elemento pede a cor ao `ThemeManager` (`theme.hex/color`).
- `ui/theme.py`: `PALETTES` (mesmas chaves nos dois temas), `ROLE_COLORS` (cores de cada tipo de
  superfície), constantes do vidro (opacidades e brilhos) e `THEME_TRANSITION_MS = 450` (InOutCubic).
  O progresso vai de 0 (claro) a 1 (escuro); clicar de novo inverte a animação do ponto atual.
  O sinal `changed` faz a janela inteira se redesenhar a cada quadro.
- Contraste testado sobre o vidro (`surface_colors`/`backdrop_colors`): 4,5:1 texto, 3:1 foco e ícone.
  Ao criar um elemento novo, dê cor a ele pela paleta e acrescente-o aos testes de contraste.
- "Reduzir movimento" do Windows (`ui/system.py`) desliga a transição e as animações de clique.

## Etapa 3D (feita)

- `core/storage.py`: `write_json_atomic` (temporário na mesma pasta + `os.replace`) e
  `load_or_quarantine` (arquivo estragado vira `<nome>.corrompido-AAAAMMDD-HHMMSS.json`).
- `core/history.py` (`History`, 20 itens, mais novo primeiro, `modo` só com trigonometria via
  `CalcResult.uses_trig`) e `core/preferences.py` (`Preferences`: tema, modo_angulo, ultima_aba).
  Sem caminho, os dois ficam só na memória (é o que os testes de janela usam).
- `ExpressionEditor.insert_value`: número do histórico; negativo entre parênteses; depois de
  número, `)`, constante, `!` ou `%` entra com "×".
- `ui/history_panel.py` (painel, itens, `GlassScrollBar`), `ui/confirm_dialog.py` (confirmação de
  vidro sobre a janela escurecida). Painel fixo a partir de 660 px; abaixo, gaveta com botão.
- `ui/app.py`: `build_window(pasta)` liga tudo; dados em `QStandardPaths.AppDataLocation`
  (`%APPDATA%/AI Calc`). O tema salvo pelo botão vale sobre o do Windows.
- Lista de conferência manual: `docs/LISTA_DE_CONFERENCIA.md`.

## Etapa 4A (feita)

- Motor: `trig.nearest_notable` (encaixe a menos de 2°, `NOTABLE_SNAP_DEGREES`), `trig.angle_from_point`,
  `trig.angle_text`; `core/trig_input.py` (`angle_from_text`, `sine_from_text` usando o motor, e
  `describe` para leitor de tela). Fica fora de `trig.py` para não criar importação circular.
- `ui/trig_circle.py` (`TrigCircleWidget`): mouse (clicar/arrastar, com encaixe), setas (1°, Shift 15°),
  Home (0°). Seno contínuo, cosseno tracejado, tangente pontilhada; cores `trig_sin/cos/tan` na paleta.
- `ui/trig_page.py`: `InfoCard` (ângulo em graus e radianos, quadrante, valores com sinal,
  "Também vale" e aviso de erro dos campos) e campos `GlassField` (`ui/glass_field.py`) "Ângulo" e
  "Seno", botão DEG/RAD (sincronizado com o Científico) e "Outra: 150°" (desativado em seno ±1).
- Na aba Trigonometria: visor escondido, painel fixo do histórico escondido (gaveta continua),
  teclas físicas não vão para a conta. Abre em 30°; o ângulo não é salvo; a última aba é.
- Testes de janela: não usar `QTest.keyClicks` com "π" (fecha o processo no Windows); usar "pi".
- Botões desativados agora são desenhados com as cores de `tab_disabled`.

## Etapa 4B (feita)

- `trig.graph_points(função)`: trechos (graus, valor) de 0° a 360°; tangente quebrada em 90°/270° e
  cortada em ±`GRAPH_LIMIT` (2), começando/terminando na borda.
- `ui/trig_graphs.py` (`TrigGraphsWidget`): grade, rótulos do eixo em DEG ou RAD, assíntotas,
  marca do ângulo e legenda (amostra da linha + nome).
- `TrigPage`: largura ≥ `WIDE_MIN_WIDTH` (600) põe círculo e gráficos lado a lado; abaixo, seletor
  `view_tabs` "Círculo | Gráficos". O ponto desliza `POINT_MS` (300 ms) pelo caminho mais curto ao
  digitar ou trocar a solução (`shown_angle` do círculo e `marker` dos gráficos); mouse e setas
  movem na hora e interrompem a animação. Ângulos escolhidos com o mouse ficam em graus inteiros.
- README com imagens da aba; lista de conferência ganhou a seção 8 (Trigonometria).

## Etapa 5A (feita)

- Projeto em `C:\Projetos\AI-Calc` (clone do GitHub), trabalho em branches (`etapa-5a-acabamento`).
- `trig.toggle_visible` (a última função visível não desliga) e `Preferences.visible_functions`
  (`funcoes_visiveis` no JSON). `TrigPage`: botões `FunctionToggle` sen/cos/tan no topo da aba,
  aplicados ao círculo, aos gráficos e ao painel (`set_visible`).
- Número do quadrante se afasta do raio (`_quadrant_spot`, `QUADRANT_LABEL_GAP`), indo para o
  lado do eixo vertical. `GlassField` diminui a fonte (até 8 pt) quando o texto não cabe.
- `ui/motion.py` (`fade_in`, 150 ms): troca de aba, seletor Círculo/Gráficos e resultado do "=".
  Desligado com "reduzir movimento". Testes que fotografam a janela esperam o efeito acabar.
- Ícone (calculadora com a onda do seno no visor) desenhado em `icons.paint_app_icon`/`app_icon`;
  `AppUserModelID` para a barra de tarefas.
- Licença MIT (`LICENSE`). Cores do escuro: seno `#FFB3D9` e cosseno `#A8D6FF` (contraste nos botões).

## Etapa 5B (feita)

- Executável: `requirements-build.txt` (PyInstaller + Pillow), `tools/gerar_icone.py` (gera
  `assets/ai_calc.ico` com os 7 tamanhos a partir de `paint_app_icon`), `tools/iniciar.py`
  (ponto de entrada) e `tools/gerar_executavel.py` (`--onefile --windowed`, sem módulos do Qt
  que o app não usa). Saída em `dist/` (ignorada pelo git), cerca de 45 MB.
- Publicação: Release no GitHub com o `AI Calc.exe` anexado (não vai para o repositório).
- Testes: `tests/ajudantes.py` (`distancia` entre cores, usada pelos testes de janela).
- Fluxo de trabalho: uma branch por etapa, PR no GitHub e merge depois do ok do Francisco.

## Redesign estilo calculadora do macOS (feito)

- Branch `redesign-liquid-glass`. Referência aprovada pelo George: "Opção B · macOS Tahoe
  refinado" no canvas de design "AI Calc · Liquid Glass".
- Paleta (`theme.py`): fundo liso grafite `#1C1C1E` (escuro) e `#EFEFF4` (claro); números em
  cinza (`key_bg`), funções em cinza mais escuro (`function_bg`), controles (`⌫ AC %`) em cinza
  mais claro (`action_bg`) e operadores/"=" no laranja original da Apple (`#FF9500` no claro,
  `#FF9F0A` no escuro) com símbolo branco. Esse laranja dá ~2:1 com o branco: escolha de design
  do George; o teste de contraste aceita 1,8:1 só para operadores e "=" (comentado no teste).
  O resto continua com 4,5:1 (texto) e 3:1 (foco e ícones).
- Superfícies opacas (`KEY_ALPHA = 1`) e reflexos discretos: fio de luz em cima (`RIM_ALPHA`),
  contorno leve (`EDGE_ALPHA`), sombra curta, sem reflexo embaixo (`GLINT_ALPHA = 0`).
- Topo (como no macOS): botão de barra lateral à esquerda (`HistoryToggleButton`), seletor de
  modo no centro (`ModeButton`, "Científica ⌄", também em `mode_title`) e tema à direita. O
  seletor abre o menu de modos (`ui/nav_menu.py`), um cartão logo abaixo dele com o `GlassTabBar`
  na vertical; Esc, clique fora ou escolher um modo fecha. O topo não muda ao trocar de modo
  (as duas abas com teclado usam a mesma largura máxima).
- Histórico: barra lateral plana encostada à esquerda (`PANEL_WIDTH` 260), com um fio separando
  da calculadora e lixeira (`TrashButton`) para limpar. Janela larga: o botão de barra lateral
  esconde/mostra (`_sidebar_hidden`); estreita: gaveta sólida que entra pela esquerda.
- Tela grande: a barra lateral vai de cima a baixo; o teclado fica centralizado na área da
  calculadora e sobe para perto do meio quando a janela passa de `BODY_MAX_HEIGHT`.
  Trigonometria: conteúdo com tamanho máximo (`TRIG_MAX_SIZE`), centralizado.
- Teclados (`keypad.py`): Comum igual ao iOS 26 (`⌫ AC % ÷` / 789× / 456− / 123+ / `( ) 0 , =`),
  círculos de até 64 px com 12 px entre eles; Científica com três linhas de funções e uma coluna
  `( ) ; e π` à esquerda, cápsulas de 80 × 44 px (`aspect` 1,82) com 9 px entre elas.
  `KeypadMetrics`, `KEY_PAD` (4 px de folga para sombra e "estufar"), bloco centralizado e
  encostado embaixo; `MainWindow._fit_keypad` dá ao teclado a altura exata e o resto ao visor;
  `_align_display` alinha o número à borda das teclas.
- Tecla `( )` (ação `PARENTHESES`) chama `ExpressionEditor.parenthesis()` no core: fecha se há
  parêntese aberto e a conta termina em número, `)`, `!`, `%`, `π` ou `e`; senão abre.
- Visor sem caixa nem chips: "DEG" em texto discreto, "Porcentagem" como botão de texto
  (`Display.add_tool`), número grande e leve (50 pt) com altura fixa.
- Animações: tecla estufa 7% ao apertar e volta com mola; operador escolhido fica com fundo
  claro e símbolo laranja até a próxima tecla (`operator_selected_bg`, `Keypad.set_selected`);
  menu e gaveta com mola. Tudo some com "reduzir movimento".
- Porcentagem: painel sólido sobre visor e teclado (`MainWindow.percentage_area`), opções
  "Parte | Variação | Desconto" (nome completo na dica), resultado grande e "Usar resultado".
- Barra de título do Windows escura no tema escuro (`system.set_dark_title_bar`, DWM).
- Contorno de foco só quando o foco veio do teclado (Tab).

## Interface (Etapas 3 e 4)

- Aprovado: pytest-qt (offscreen); histórico em painel lateral recolhível; `preferencias.json`
  (tema, DEG/RAD, última aba) com gravação segura e tratamento de arquivo corrompido igual ao
  histórico; na primeira vez segue o tema do Windows; janela mínima 360 × 560; teclado
  Científico testado na largura mínima; contraste adequado nos dois temas.

- PySide6 com `QPainter` e `QPropertyAnimation`; janela redimensionável com tamanho mínimo.
- "Vidro líquido" simulado com translucidez, gradientes, bordas e brilho (blur real pesa e é instável).
- Tema claro (cinza-claro) e escuro (grafite), no estilo da calculadora do macOS, com laranja só em operadores e "="; ver "Redesign estilo calculadora do macOS". A troca muda TODOS os elementos, com transição suave.
- Cores de seno, cosseno e tangente diferentes, mais rótulo escrito e estilo de linha (não depender só da cor).
- Respeitar a preferência de "reduzir movimento" do sistema.
- Histórico: 20 itens, JSON em pasta de configuração do sistema (usar `QStandardPaths`), etiqueta DEG/RAD nos itens com trigonometria, clique insere só o número do resultado.

## Confirmados pelo Francisco (decididos na Etapa 1)

1. Raiz de índice n: `raiz(n; x)`, com `;` separando os argumentos; radicando negativo só com índice inteiro ímpar.
2. A digitação aceita `.` e `,` como decimal.
3. Parênteses desligam a regra especial do `%`: `200 + (10%)` = 200,1.
4. `√` age sobre o próximo termo: `√4pi` = (√4) × π.
5. Expressões com mais de 500 caracteres: "Expressão longa demais".

## Ambiente

- Windows 11 (confirmado). Histórico e preferências em `%APPDATA%`, obtido via `QStandardPaths`.
