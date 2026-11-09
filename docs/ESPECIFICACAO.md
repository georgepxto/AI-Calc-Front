# AI Calc: especificação final (pontos 1 a 7 aprovados)

Aplicativo desktop em Python (PySide6), em português do Brasil, com três modos:
Comum, Científica e Trigonometria. Este documento consolida o prompt original e
as decisões tomadas ponto a ponto antes de escrever o código.

## Como o projeto está organizado

O cálculo (`ai_calc/core`) não conhece a interface. Isso permite testá-lo sozinho.

| Etapa | Conteúdo | Status |
|---|---|---|
| 1 | Motor de cálculo e testes (`core/`) | feita |
| 2 | Lógica da trigonometria (círculo, seno com duas soluções) | feita |
| 3A | Janela, visor e teclado Comum (com teclado físico) | feita |
| 3B | Teclado Científico, DEG/RAD e botão de tema (troca simples) | feita |
| 3C | Transição suave do tema e visual de vidro | feita |
| 3D | Histórico, preferências e lista de conferência final | feita |
| 4 | Aba Trigonometria (círculo e gráficos) | pendente |
| 5 | Acabamento, animações e README | pendente |

Para rodar os testes: `pip install -r requirements.txt` e depois `pytest`.

## Ponto 1: Porcentagem

| Conta | Regra | Resultado |
|---|---|---|
| `200 + 10%` | `A + B%` vale A + A × B/100 | 220 |
| `200 − 10%` | A − A × B/100 | 180 |
| `200 × 10%` | `%` é só o fator B/100 | 20 |
| `200 ÷ 10%` | divide por B/100 | 2000 |
| `50%` | B/100 | 0,5 |
| `100 + 20 + 10%` | a base é tudo que já foi somado à esquerda (120) | 132 |
| `(2 + 3)%` | vale sobre o resultado do parêntese | 0,05 |
| `200 + 10% × 3` | o `%` só é "da base" quando é o termo inteiro à direita de `+` ou `−`; aqui vale 0,1 | 200,3 |

### Painel Porcentagem (Etapa 6)

O botão **Porcentagem** fica abaixo do visor na aba **Comum**. O painel aceita
ponto ou vírgula decimal.

| Operação | Cálculo | Exemplo |
|---|---|---|
| Parte do total | Parte ÷ total | 36 de 240 → 15% |
| Variação (%) | (Valor final − valor inicial) ÷ valor inicial | De 240 para 204 → −15% |
| Valor original | Valor final ÷ (1 − taxa de desconto) | 150 após 25% de desconto → 200 |

Na variação, a base mantém seu sinal. Total ou valor inicial igual a zero
gera erro. O desconto deve ser maior ou igual a 0% e menor que 100%.

O motor trabalha com taxas em fração decimal. O painel exibe `15%`, mas
**Usar resultado** insere `0,15` pelo editor da calculadora. Alterar um campo
ou trocar a operação invalida o resultado anterior. Esc fecha o painel
e devolve o foco ao botão **Porcentagem**.

## Ponto 2: Fatorial

- Inteiros de 0 a 170. `171!` ou mais: "Fatorial limitado a 170".
- `5,5!` e `(−3)!`: "Fatorial só vale para inteiros não negativos" (sem função gama).
- Valores a menos de 0,000000001 de um inteiro contam como inteiros: `(0,1 × 30)!` = `3!`.
- `5!!` não é suportado: "Use parênteses: (5!)!".

## Ponto 3: Ângulo no círculo (Etapa 2 e 4)

- Ângulo sempre normalizado entre 0° e 360° (`450°` vira 90°, `−30°` vira 330°).
- O botão de alternar solução do seno troca θ por 180° − θ.
- Em seno = 1 ou −1 só existe uma solução: o botão fica desativado.
- O app guarda o último lado (direita ou esquerda) e o respeita ao mexer no seno.
- Texto discreto "Também vale: θ + 360° × k". Gráficos de 0° a 360°.
- Aprovado na Etapa 2: 360° vira 0°; nos eixos (0°, 90°, 180°, 270°) o quadrante é
  "Sobre o eixo" e o zero aparece sem sinal; o estado do círculo fica sempre em graus;
  seno fora de [−1, 1] dá "Valor fora do domínio"; em seno ±1 o último lado é mantido.

## Ponto 4: Histórico (Etapa 3)

- Cada item guarda expressão, resultado arredondado e etiqueta DEG ou RAD (só se usou trigonometria).
- Clicar insere o número do resultado na conta atual, nunca a expressão antiga.
- Contas com erro não entram. Últimas 20. Salvo em JSON. Arquivo corrompido: renomeia e começa vazio.
- Limpar pede confirmação.

## Ponto 5: Notação científica

- Normal até 12 dígitos inteiros; a partir de 10¹² vira `1e+12`, `1,5e+20`.
- Menor que 10⁻⁶ (e diferente de zero) vira `1e-7`.
- No máximo 12 dígitos significativos, sem zeros sobrando: `1/3` = `0,333333333333`.
- Vírgula decimal. Sem separador de milhar nesta versão.
- O leitor de expressões aceita `1,5e+20` como número; `e` sozinho é a constante de Euler.
- Estouro: "Resultado grande demais".

## Ponto 6: Erros

| Conta | Mensagem |
|---|---|
| `5/0`, `1/x` com x = 0, `0^(−1)` | Divisão por zero inválida |
| `0/0`, `0^0` | Indeterminação |
| `√(−4)`, `ln(0)`, `ln(−1)`, `log(0)`, `asin(2)`, `acos(−1,5)` | Valor fora do domínio |
| `tan(90)` em DEG (e 270, −90, 450...), `tan(pi/2)` em RAD | Indefinida |
| `10^400` | Resultado grande demais |
| `2 +` | Expressão incompleta |
| `(2 + 3` ou `2 + 3)` | Parênteses incorretos |
| outras expressões malformadas | Expressão inválida |
| erro inesperado | Algo deu errado nesta conta |

Tangente em RAD: indefinida quando |cos(x)| < 10⁻¹². Em DEG, ângulos em múltiplos
de 90° são tratados de forma exata.

## Ponto 7: Multiplicação implícita e precedência

Precedência, da maior para a menor:

1. parênteses e funções
2. `!` e `%` (sufixos)
3. `^`, da direita para a esquerda (`2^3^2` = 512)
4. menos unário (`−2^2` = −4; `2^−2` = 0,25)
5. `×`, `÷` e multiplicação implícita, da esquerda para a direita
6. `+` e `−`

Multiplicação implícita vale quando o que vem depois é `(`, constante, função ou `√`
(`2pi`, `3(4+5)`, `2sin(30)`). Não vale entre dois números (`2 3` é inválido).
Funções exigem parênteses (`sin 30` mostra "Use parênteses: sin(30)").
`2e3` = 2000 e `2e` = 2 × e. Quando o app insere um `×`, mostra
"Interpretado como: 1 ÷ 2 × π" para `1/2pi`.

## Detalhes adicionados na implementação (para você conferir)

- Raiz de índice n: `raiz(n; x)`, com `;` separando os argumentos (a vírgula é o separador decimal). Radicando negativo só com índice inteiro ímpar (`raiz(3; −8)` = −2).
- Aceita `.` e `,` como separador decimal na digitação.
- `√` age sobre o próximo termo: `√9`, `√(2+7)`; `√4pi` é (√4) × π.
- Parênteses explícitos desligam a regra especial do `%`: `200 + (10%)` = 200,1.
- Expressões com mais de 500 caracteres: "Expressão longa demais".
- (Os cinco itens acima foram confirmados pelo Francisco antes da Etapa 2.)
- Etapa 2 (aprovado): ângulos a menos de 0,000000001° de um inteiro viram esse inteiro (30,000000000000004° vira 30°).
- Etapa 2 (aprovado): quadrante escrito como "1º quadrante" a "4º quadrante".
- Etapa 2 (aprovado): no modo RAD, os ângulos notáveis (0, 30, 45, 60, 90, 120, 135, 150, 180,
  210, 225, 240, 270, 300, 315 e 330 graus) aparecem como fração de π ("Também vale: π/6 + 2π × k");
  os demais com 4 casas decimais ("Também vale: 0,1745 + 2π × k").
- Etapa 3A: depois do "=", um operador (+ − × ÷ ^ % !) continua a conta a partir do resultado;
  qualquer outra tecla começa uma conta nova. "=" repetido não faz nada.
- Etapa 3A: "," digitada no começo ou depois de operador/parêntese vira "0,".
- Etapa 3A: teclado físico aceita dígitos, `,` `.` `+ - * / ( ) %`; Enter ou `=` calcula,
  Backspace apaga, Esc ou Delete limpa.
- Etapa 3A: enquanto se digita, a conta fica na linha grande do visor; depois do "=", ela sobe e
  o resultado ocupa a linha grande. Texto longo diminui de tamanho e depois mostra só o final.
- Etapa 3B: o teclado físico também aceita letras (para digitar sin, ln...) e `^ ! ;`.
- Etapa 3B: continuar a partir de um resultado negativo põe parênteses: `(-6)^2` = 36.
- Etapa 3B: trocar DEG/RAD não recalcula a conta já feita; vale para a próxima.
- Etapa 3B: o modo DEG/RAD aparece no canto do visor nas duas abas (vale também para funções
  digitadas na aba Comum).
- Etapa 3B: o botão de tema mostra o tema para onde leva (lua no claro, sol no escuro).
- Etapa 3C: no meio da transição de tema (cerca de 0,1 s), texto e fundo ficam parecidos por um
  instante; o contraste mínimo é garantido nos dois temas, antes e depois da troca.
- Etapa 3C: teclas recebem foco só pelo Tab (clicar com o mouse não move o foco), para o
  contorno de foco não aparecer depois de cada clique.
- Etapa 3C: clique encolhe a tecla 4% e escurece um pouco (70 ms para baixo, 180 ms para voltar);
  passar o mouse clareia a tecla. O "=" escurece em vez de clarear.
- Etapa 3C: o fundo tem duas manchas de cor (lavanda e coral no claro; roxo e turquesa no
  escuro) que aparecem através do vidro.
- Etapa 3C: para manter 4,5:1 sobre o vidro, o "=" do tema claro ficou num coral mais escuro
  (#962C14), e algumas cores do tema escuro ficaram mais claras (texto secundário, erro, aba
  desativada).
- Etapa 3C: o ícone de lua/sol troca com um esmaecimento cruzado, junto com o tema.
- Etapa 3C: aba "Trig. · Em breve"; o leitor de tela anuncia "Trigonometria, em breve".
- Etapa 3D: número do histórico negativo entra sempre entre parênteses, mesmo no começo da conta
  (`(-6)`); depois de número, `)`, π, e, `!` ou `%`, ele entra com "×" na frente.
- Etapa 3D: a janela abre com 700 × 640 (histórico visível ao lado); abaixo de 660 px de largura
  o histórico vira gaveta, que fecha ao escolher um número, com ✕ ou com Esc.
- Etapa 3D: na gaveta (por cima do teclado) o vidro do painel fica mais opaco.
- Etapa 3D: itens do histórico não mudam de cor ao apertar (só encolhem), para o texto discreto
  da conta manter 4,5:1.
- Etapa 3D: a confirmação mostra quantas contas serão apagadas e começa com o foco em "Cancelar".
- Etapa 3D: preferência com valor desconhecido é ignorada (vale o padrão); só JSON inválido ou
  formato errado conta como arquivo corrompido.
- Etapa 3D: o tema só é salvo quando o usuário usa o botão; sem isso, o app segue o Windows.
- Etapa 4A: no círculo, o seno aparece como "sen" (forma usada na escola), embora a tecla da
  calculadora continue "sin".
- Etapa 4A: o campo "Ângulo" aceita contas e vale no modo atual (em RAD, "π/6" é 30°); o campo "Seno"
  aceita contas como "1/2" ou "√3/2". Os campos são aplicados com Enter ou ao sair deles.
- Etapa 4A: o botão de outra solução mostra para onde leva ("Outra: 150°"); em seno ±1 vira
  "Solução única", desativado.
- Etapa 4A: setas → e ↑ aumentam o ângulo; ← e ↓ diminuem; Shift muda de 15 em 15; Home volta a 0°.
- Etapa 4A: a última aba aberta (inclusive Trigonometria) é lembrada.
- Etapa 4B: gráficos de y = −2 a 2; a tangente é cortada nas bordas e interrompida nas assíntotas.
- Etapa 4B: círculo e gráficos lado a lado quando a área da aba tem 600 px ou mais; abaixo disso,
  seletor "Círculo | Gráficos" (começa no Círculo).
- Etapa 4B: ao digitar um ângulo ou trocar a solução, o ponto desliza em 300 ms pelo caminho mais
  curto; os números do painel mudam na hora. Mouse e setas movem sem animação.
- Etapa 4B: ângulo escolhido com o mouse fica em grau inteiro (ou no notável, se estiver perto).
- Etapa 5A: botões sen/cos/tan na aba Trigonometria (60 px cada, à direita do seletor; na janela
  larga, alinhados à direita). Desligado: amostra cinza e nome riscado. A última ligada fica
  desativada. A escolha é salva.
- Etapa 5A: esmaecer de 150 ms na troca de aba, no seletor Círculo/Gráficos e no resultado do "=".
- Etapa 5A: ícone próprio: calculadora em degradê roxo → turquesa com a onda do seno em âmbar
  no visor e a tecla "=" em âmbar (2 × 2 teclas nos tamanhos pequenos).
- Etapa 5A: licença MIT, em nome de Francisco Aurélio.
- Etapa 5B: executável de um arquivo só (`AI Calc.exe`, sem console), publicado como anexo de uma
  Release no GitHub; o README explica o aviso do Windows para executáveis sem assinatura.
- Redesign liquid glass: paleta neutra (branco-gelo no claro, grafite no escuro) com um único
  acento laranja em operadores e "="; substitui as cores da Etapa 3C (lavanda, coral, roxo e
  turquesa). O ícone do app não mudou.
- Redesign liquid glass: teclas em cápsula, abas como controle segmentado com lente deslizante
  (260 ms), histórico e tema numa cápsula no topo, histórico como lista com divisórias.
- Redesign liquid glass: teclados reorganizados por grupo (controles, números, operadores na última
  coluna). Na Comum, `⌫` foi para o lado do `C` e `%` para o lado da vírgula; na Científica, as
  inversas ficam abaixo de sin/cos/tan e o "=" no canto inferior direito.
