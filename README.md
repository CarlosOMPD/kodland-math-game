# Kodland Project — jogo de matemática em Pygame Zero

Um jogo 2D em que o jogador atravessa a sala de aula enquanto inimigos arremessam **números e operações matemáticas**. Tudo o que acerta o jogador vira uma expressão. No final do percurso, essa expressão aparece num **quadro-negro**, e o jogador precisa resolvê-la: se acertar, ganha *Math Power* e a dificuldade sobe; se errar, é game over.

---

## Como jogar

### Fluxo do jogo
1. **Menu:** jogar, sair ou ajustar o volume da música e dos efeitos.
2. **Fase:** atravesse a tela da esquerda para a direita. Uma seta **GO!** indica a direção no começo de cada fase.
3. **Arremessos:** os inimigos lançam números (`0`–`9`) e operadores (`+ − × ÷`). Cada símbolo que acerta você entra, em ordem, na sua expressão, que fica escondida até o final.
4. **Quadro-negro:** ao chegar do outro lado, a expressão aparece no quadro e você digita a resposta.
5. **Acertou:** +5 de *Math Power* e uma nova fase, mais difícil. **Errou:** game over.
6. **Vitória:** chegue a 45 de *Math Power* (acertar o quadro na dificuldade máxima).

### Controles
| Ação | Tecla |
|---|---|
| Mover | `W A S D` ou setas |
| Responder no quadro | clique nos números com o lápis ou digite no teclado |
| Apagar | botão **DELETE** ou `Backspace` |
| Enviar resposta | botão **SEND** ou `Enter` |
| Fechar o jogo | botão **EXIT** no menu ou `Ctrl + Q` |

### Regras da expressão
- **Número seguido de número:** o último operador coletado entra entre eles (ou `+`, se nenhum foi coletado ainda). Ex.: `1`, `×`, `4`, `5` → `1 × 4 × 5`.
- **Operador seguido de operador:** o novo substitui o anterior.
- **Operador sobrando no final:** é descartado.
- **Divisão por zero:** pegar um `0` logo depois de um `÷` é **game over imediato**.
- **Borrachas:** espalhadas pelo mapa, **limpam a expressão** quando o jogador passa por elas. São a mecânica de **balanceamento** do jogo: o jogador decide se vale desviar do caminho para se livrar de uma conta difícil, e a quantidade de borrachas aumenta junto com a dificuldade.
- **Expressão vazia no final:** o quadro mostra uma conta aleatória e simples.
- A conta respeita a **precedência** (`×` e `÷` antes de `+` e `−`). Em contas com divisão, a resposta é aceita com **2 casas decimais**.

### Dificuldade progressiva
| Dificuldade | Math Power | Inimigos | Operadores | Borrachas |
|---|---|---|---|---|
| 1 | 0 – 10 | 1 | `+` | 1 |
| 2 | 15 – 20 | 2 | `+ −` | 2 |
| 3 | 25 – 30 | 4 | `+ − ×` | 2 |
| 4 | 35 – 40 | 8 | `+ − × ÷` | 3 |

Conforme a dificuldade sobe, os inimigos também arremessam mais rápido e ficam mais propensos a **mirar no jogador** em vez de jogar em direções aleatórias.

---

## Arquitetura

Venho do **desenvolvimento em Roblox (Luau)** e quis trazer para o Python a forma de pensar que uso lá: um código **orientado a eventos**, em que os sistemas não ficam perguntando a cada frame "isso mudou?", mas **reagem quando algo acontece**.

### Signals: eventos como no Roblox
A classe `Signal` é a minha versão dos eventos do Roblox (`RBXScriptSignal` / `BindableEvent`): qualquer função pode se **conectar** (`connect`) a um evento, e quando ele é **disparado** (`fire`), todas as funções conectadas são chamadas.

```python
PlayerReachedEnd = Signal()
PlayerReachedEnd.connect(OnPlayerReachedEnd)   # quem se importa com o evento se conecta
PlayerReachedEnd.fire(char)                    # quem detecta o evento só avisa
```

Assim, quem **detecta** um evento não precisa saber quem **reage** a ele. Por exemplo, o inimigo só dispara `EnemyThrew` quando arremessa; quem cria o projétil é uma função conectada a esse sinal.

### Observe: detectar mudança de propriedades
A classe `Observe` funciona como o `Changed` / `GetPropertyChangedSignal` do Roblox. Ela sobrescreve o `__setattr__` e, **sempre que uma propriedade muda de valor**, dispara o sinal `changed` com o nome e o novo valor.

Classes que herdam de `Observe`: `GameStates`, `AudioSettings`, `Player` e `Enemie`. Na prática:
- mudar `G.GameMode` dispara `CheckGameMode`, que monta ou limpa cada tela;
- mudar o volume em `A.Music` dispara `ApplyVolume`;
- mudar `P.Math_Power` dispara `MatchDifficulty`, que recalcula a dificuldade sozinha.

### Máquina de estados
O jogo tem uma pequena máquina de estados (`Mode`: `MENU → PLAYING → BOARD → PLAYING ... → GAMEOVER`). Como `GameStates` é observável, **trocar de estado é só atribuir um valor**, e o `CheckGameMode` cuida de preparar o estado novo e **limpar o anterior**: remove inimigos, projéteis e borrachas, esconde ou mostra o mouse, troca a música etc. Isso concentra toda a lógica de transição num único lugar.

Os inimigos também têm uma máquina de estados própria para o arremesso (`idle → windup → throw → follow → idle`), definida pela lista `THROW_ANIM`, com a duração de cada etapa.

### Classes como "modelos" de objetos
Usei classes para padronizar a criação dos objetos do jogo, parecido com montar um *template* de `Instance` no Roblox:
- **`Player`, `Enemie` e `Projectile`:** guardam o `Actor` (a imagem na tela) junto com os dados de jogo (velocidade, estado, símbolo, direção...);
- **`Board` e `KeypadKey`:** o estado do quadro-negro e de cada botão clicável;
- **`ManagedAnimation`:** um gerenciador de animações sobre o `animate` do Pygame Zero, com **loops**, **yoyo** (vai e volta) e **grupos**, que permitem parar todas as animações de uma tela de uma vez. É a minha versão simplificada do `TweenService`.

### Gerenciamento de memória ("garbage")
Objetos temporários ficam em listas (`EnemiesStorage`, `ProjectilesStorage`, `ErasersStorage`, `AnimationStorage`). Projéteis que saem da tela são removidos automaticamente, e cada troca de estado limpa o que não é mais usado.

### Organização do arquivo
O `KodlandProject.py` é dividido em seções, na ordem:

| Seção | Responsabilidade |
|---|---|
| `CONFIGS` | constantes de balanceamento, posições e sons (ajustar o jogo sem mexer na lógica) |
| `CLASSES` | `Signal`, `Observe` e os modelos de objetos |
| `STATES` / `DATA` | instâncias globais e listas de objetos ativos |
| `SOUND` | efeitos sonoros gerados por código |
| `PLAYER` / `ENEMY` / `PROJECTILES` / `ERASERS` | regras de cada parte da gameplay |
| `BOARD` | montagem, cálculo e verificação da expressão |
| `ANIMATIONS` | gerenciador de animações |
| `DRAW` | tudo o que é desenhado na tela |
| `CHECK-UPS` | transições da máquina de estados |
| `EVENTS HOOKS` | entradas do Pygame Zero (`update`, `draw`, mouse e teclado) |
| `INITIALIZATION` | conexão dos sinais e início do jogo |

### Decisões técnicas
- **Cálculo da expressão sem `eval`:** a função `Evaluate` resolve a conta em duas passadas (primeiro `×` e `÷`, depois `+` e `−`). Isso respeita a precedência sem executar texto como código.
- **Sons gerados por código:** os efeitos usam o `tone` do Pygame Zero para gerar notas musicais na hora, sem arquivos de áudio. Uma fila própria (`SfxQueue`) toca as notas em sequência.
- **Tela escalável:** o jogo é desenhado em 960×540 e usa a flag `SCALED` do pygame para se adaptar a qualquer resolução em tela cheia, mantendo o pixel art nítido.

---

## Como rodar

### Requisitos
- **Python 3.12 ou mais novo** (testado com Python 3.14)
- Git (opcional, só para clonar o repositório)

### 1. Baixe o projeto
```bash
git clone <url-do-repositorio>
cd aulas-pgzero
```
Ou baixe pelo GitHub e abra um terminal dentro da pasta do projeto.

### 2. Crie e ative um ambiente virtual

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
pip install --no-deps pgzero==1.2.1
```

> **Por que `--no-deps`?** O Pygame Zero depende do pacote `pygame` clássico, mas este projeto usa o
> **`pygame-ce`** (Community Edition), que fornece o mesmo módulo `pygame`. Instalar os dois causa
> conflito, então o `pgzero` é instalado sem puxar o `pygame`.

### 4. Rode o jogo
```bash
python KodlandProject.py
```

O jogo abre em **tela cheia**. Para sair, use o botão **EXIT** no menu ou `Ctrl + Q` a qualquer momento.

### Problemas comuns
- **`Activate.ps1 cannot be loaded because running scripts is disabled`** (Windows):
  rode uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e ative de novo.
- **`ModuleNotFoundError: No module named 'pgzero'`:** o ambiente virtual não está ativo, ou o passo 3
  não foi feito. Ative o `.venv` e rode os comandos de instalação de novo.
- **Erros envolvendo `pygame` depois de instalar outros pacotes:** o `pygame` clássico pode ter sido
  instalado junto com o `pygame-ce`. Para corrigir:
  ```bash
  pip uninstall -y pygame pygame-ce
  pip install pygame-ce==2.5.8
  ```

---

## Estrutura de pastas
```
aulas-pgzero/
├── KodlandProject.py   # código do jogo
├── requirements.txt    # dependências
├── images/             # sprites, interface, números e operadores
└── music/              # músicas do menu e da gameplay
```

---

## Limitações conhecidas e próximos passos
- **Pause:** estava nos planos implementar uma mecânica de pausa usando `yield` (geradores) junto com as funções auxiliares do gerenciador de animações, que já organiza as animações em grupos. Ela foi cortada por causa do prazo do projeto e para reduzir a complexidade: como o jogo ainda tem poucos sistemas, o pause exigiria muito código para pouca diferença na gameplay. É algo a ser adicionado numa versão futura.
- **Expressões muito longas** (mais de ~40 símbolos) podem passar do espaço do quadro. As borrachas ajudam a evitar isso.
- **Projéteis rebatendo nas paredes:** fazer os números e operadores quicarem nas bordas da tela em vez de sumirem, deixando a fase mais dinâmica. Um símbolo que errou o jogador poderia voltar e acertá-lo depois.

---

## Uso de IA
A ideia do jogo, as regras, o fluxo e a arquitetura baseada em sinais e estados são meus, vindos da minha experiência com Roblox. Usei IA como **apoio durante o desenvolvimento**: para tirar dúvidas sobre o Pygame Zero, sugerir implementações de partes específicas (como o quadro-negro e os sons) e encontrar bugs. Todo o código sugerido foi revisado, testado e integrado por mim ao longo de várias iterações, ajustando cada parte até ficar como eu tinha idealizado.

---

## Créditos
- **Bibliotecas:** [Pygame Zero](https://pygame-zero.readthedocs.io/), [pygame-ce](https://pyga.me/), [NumPy](https://numpy.org/)
- **Imagens:** geradas com IA.
- **Músicas:** recortes de áudios open source.
