# ============ IMPORTS ============

import pgzrun 
import random
import math
from pgzero.builtins import (
    Actor,       # images that need storage info like pos, angle and collideable images
    Rect,        # useful for hitboxs using int numbers
    ZRect,       # useful for hitboxs using float numbers
    animate,     # animate properties
    clock,       # schedule functions
    keyboard,    # get keyboards
    images,      # take images
    sounds,      # play sounds
    music,       # play music only one per time
    tone,        # create sounds on runtime
    mouse,       # get mouse
    exit,        # close game
)
from pgzero.builtins import (keys, keymods)  # type: ignore #useful for on_key_down
from pgzero.animation import Animation
from pgzero import game
from pgzero.screen import Screen
screen: Screen

# ============ CONFIGS ============

WIDTH, HEIGHT = 960, 540 # 16:9
TITLE = "Kodland Project"
ICON = "images/icon.png"

FONT = None
PANEL_W, PANEL_H = 560, 336
PANEL_X = int(WIDTH / 2 - PANEL_W / 2)
PANEL_Y = int(HEIGHT * 0.47 - PANEL_H / 2)
RUN_FRAMES = 4                          
RUN_FRAME_TIME = 0.1                    
PLAY_AREA = Rect(0, 0, WIDTH, HEIGHT) 
SPAWN_POS = (16, HEIGHT / 2)
DEBUG_AIM = False                      
ENEMY_SPOTS = [
    (WIDTH * 0.85, HEIGHT * 0.50),
    (WIDTH * 0.55, HEIGHT * 0.13),
    (WIDTH * 0.55, HEIGHT * 0.87),
    (WIDTH * 0.85, HEIGHT * 0.15),
    (WIDTH * 0.85, HEIGHT * 0.85),
    (WIDTH * 0.30, HEIGHT * 0.13),
    (WIDTH * 0.30, HEIGHT * 0.87),
    (WIDTH * 0.65, HEIGHT * 0.50),
]
THROW_ANIM = [("windup", 0.35), ("throw", 0.15), ("follow", 0.25)]   
ENEMY_COOLDOWN = {1: 2.5, 2: 2.2, 3: 1.9, 4: 1.6}     
FOLLOW_CHANCE = {1: 0.0, 2: 0.3, 3: 0.5, 4: 0.7}      
DIRECTION_SPREAD = 30
PROJECTILE_SPEED = 220                 # pixels per second
PROJECTILE_SPIN = 0                    # degrees per second (0 = no spin; careful: 6 and 9 get confused when spinning)
PROJECTILE_MARGIN = 40                 # how far off screen before it gets cleaned
SYMBOL_IMAGES = {"+": "op_plus", "-": "op_minus", "*": "op_times", "/": "op_div"}                                  
BOARD_POS = (240, 16)
BOARD_SIZE = (480, 248)
BOARD_TEXT_CENTER_Y = 16 + 113            # vertical center of the green area
GLYPH_STEP = 40                           # horizontal space per symbol on the board
GLYPHS_PER_LINE = 10
LINE_STEP = 54
ANSWER_MAX_LEN = 8
ANSWER_TOLERANCE = 0.01                   # accepts answers with 2 decimal places
POWER_PER_LEVEL = 5
RESULT_DELAY = 1.5                        # seconds showing CORRECT/WRONG before moving on
PENCIL_TIP = (4, 4)                      # pencil tip position inside cursor_pencil.png
ERASER_SPOTS = [
    (WIDTH * 0.18, HEIGHT * 0.15),
    (WIDTH * 0.18, HEIGHT * 0.85),
    (WIDTH * 0.42, HEIGHT * 0.50),
    (WIDTH * 0.42, HEIGHT * 0.10),
    (WIDTH * 0.70, HEIGHT * 0.30),
    (WIDTH * 0.70, HEIGHT * 0.72),
]
ERASERS_PER_DIFFICULTY = {1: 1, 2: 2, 3: 2, 4: 3}
GLYPH_IMAGES = {
    **{str(d): f"num_{d}" for d in range(10)},
    **SYMBOL_IMAGES,
    "=": "op_equals",
    "?": "op_question",
}
KEY_LABELS = {"del": "DELETE", "ok": "SEND"}
VICTORY_POWER = 45                        # beating the board at Math_Power 40 (difficulty 4) wins the game
SFX_VOLUME_SCALE = 0.5                    # generated tones are loud, this softens them
SFX_TONES = {                             # name: [(note, seconds), ...] played in sequence
    "hit_number":   [("E5", 0.08)],
    "hit_operator": [("A5", 0.08)],
    "eraser":       [("G4", 0.08), ("C4", 0.12)],
    "board":        [("G4", 0.10), ("C5", 0.15)],
    "key":          [("C6", 0.04)],
    "correct":      [("C5", 0.10), ("E5", 0.10), ("G5", 0.18)],
    "wrong":        [("E3", 0.15), ("C3", 0.35)],
    "victory":      [("C5", 0.12), ("E5", 0.12), ("G5", 0.12), ("C6", 0.40)],
    "crash":        [("C3", 0.60)],
}
ARROW_TIME = 3.0                          # seconds the direction arrow stays on screen
ARROW_POS = (190, HEIGHT / 2)
ARROW_COLOR = (255, 205, 117)
ARROW_OUTLINE = (93, 39, 93)
GAME_MUSIC = "game_music"                        

# ============ CLASSES ============

class Mode:
    MENU = "Menu"
    PLAYING = "Playing"
    GAMEOVER = "GameOver"
    BOARD = "Board"

class TextLabel:
    def __init__(self, text, x, y):
        self.text = text
        self.x = x
        self.y = y

class Signal:
    def __init__(self):
        self._connections = []

    def connect(self, func):
        self._connections.append(func)

    def disconnect(self, func):
        if func in self._connections:       
            self._connections.remove(func)

    def fire(self, *args):
        for func in self._connections[:]:
            func(*args)

class Observe:
    changed: Signal 

    def __init__(self):
        object.__setattr__(self, "changed", Signal())   

    def __setattr__(self, name, value):
        old = getattr(self, name, None)
        object.__setattr__(self, name, value)            
        if old != value:
            self.changed.fire(name, value)

class GameStates(Observe):
    def __init__(self):
        super().__init__()
        self.GameMode = ""
        self.EnemiesMode = ""
        self.SettingsOpen = False

class AudioSettings(Observe):
    def __init__(self):
        super().__init__()
        self.Music = 0.7
        self.Sfx = 0.8

class ManagedAnimation:
    def __init__(self, obj, tween, duration, on_finished, loops, yoyo, group, targets):
        self.obj = obj
        self.tween = tween
        self.duration = duration
        self.on_finished = on_finished
        self.loops = loops
        self.loops_left = loops
        self.yoyo = yoyo                # True = goes back and forth instead of restarting
        self.forward = True             # current direction (used by yoyo)
        self.group = group
        self.targets = dict(targets)
        self.initial = {k: getattr(obj, k) for k in targets}
        self.anim = None

class Player(Observe):
    def __init__(self, Character: Actor | None, Math_Power: int):
        super().__init__()
        self.Character = Character
        self.Math_Power = Math_Power
        self.Speed = 130         # pixels per second
        self.Facing = "right"
        self.Frame = 0
        self.AnimTime = 0.0
        self.CanMove = True
        self.AtEnd = False
        self.Table = []          # collected symbols in hit order
        self.LastOperator = "+"  # used between two numbers in a row
          
class Enemie(Observe):
    def __init__(self, Character: Actor | None, Operators: list | None , Numbers: list | None, Directions: list | None, CanFollowPlayer: bool | None):
        super().__init__()
        self.Character = Character
        self.Operators = Operators
        self.Numbers = Numbers
        self.Directions = Directions
        self.CanFollowPlayer = CanFollowPlayer
        self.Facing = "left"
        self.State = "idle"
        self.StateTime = 0.0
        self.Cooldown = 2.0
        self.CooldownLeft = 0.0
        self.Angle = 0.0

class Projectile:
    def __init__(self, Character: Actor, Symbol, Vx: float, Vy: float):
        self.Character = Character
        self.Symbol = Symbol
        self.Vx = Vx
        self.Vy = Vy

class KeypadKey:
    def __init__(self, Value: str, Image: str | None, Box: Rect):
        self.Value = Value
        self.Image = Image
        self.Box = Box

class Board:
    def __init__(self):
        self.Tokens = []         # expression shown on the board
        self.Answer = 0.0
        self.Typed = ""          # what the player typed
        self.Message = ""
        self.Locked = False      # blocks input while showing the result
        self.Keys = []

# ============ STATES ============

G= GameStates() 
A = AudioSettings()
P = Player(None,0)
B = Board()
MousePos = (0, 0)
ToneCache = {}
SfxQueue = []                             # [seconds_left, sound]
ArrowVisible = False
CurrentMusic = None                       # pgzero's music.is_playing() ignores the track name
DraggingSlider = None
HoverSlider = None
TitleFloat = None 
PlayerReachedEnd = Signal()
EnemyThrew = Signal()

# ============ UI DATA ============

MenuImages = [
    ("menu_bg", (0, 0)),
]

MenuButtons = [
    Actor("menu_btn_play",   center=(WIDTH / 2, HEIGHT * 0.55)),
    Actor("menu_btn_exit",   center=(WIDTH / 2, HEIGHT * 0.70)),
    Actor("menu_btn_config", topright=(WIDTH - 16, 16)),
]

ButtonLabels = {
    "menu_btn_play": ("PLAY", (36, 120, 66)),   
    "menu_btn_exit": ("EXIT", (115, 40, 54)),
    "menu_btn_back": ("BACK", (36, 56, 120)),
}

SettingsButtons = [
    Actor("menu_btn_back", midtop=(WIDTH / 2, PANEL_Y + PANEL_H + 16)),
]

Sliders = {  
    "Music": ("MUSIC", Rect(PANEL_X + 44, PANEL_Y + 152, 472, 16)),
    "Sfx":   ("SFX",   Rect(PANEL_X + 44, PANEL_Y + 256, 472, 16)),
}

TitleLabel = TextLabel(TITLE, WIDTH / 2, HEIGHT * 0.25)
ArrowHint = TextLabel("GO!", *ARROW_POS)

# ============ DATA ============

Difficulty = 1
AnimationStorage = []
EnemiesStorage = []
ProjectilesStorage = []
ErasersStorage = []
Difficulties = [1,2,3,4]
Operators = ["+","-","*","/"]
Numbers = [0,1,2,3,4,5,6,7,8,9]
EnemiesPerDifficulty = [1,2,4,8]

# ============ UTILS FUNCS ============

def BaseName(btn):
    return btn.image.replace("_hover", "")

def ActiveButtons():
    if G.SettingsOpen:
        return SettingsButtons
    if G.GameMode == Mode.MENU:
        return MenuButtons
    return []

def SliderAt(pos):
    for key, (label, track) in Sliders.items():
        if track.inflate(24, 32).collidepoint(pos):
            return key
    return None

def SetSlider(key, x):
    track = Sliders[key][1]
    value = (x - track.x) / track.width
    setattr(A, key, round(max(0, min(1, value)), 2))

def PlaySfx(name):
    sfx = getattr(sounds, name)
    sfx.set_volume(A.Sfx)
    sfx.play()

def PlayMusic(name):
    global CurrentMusic
    if name == CurrentMusic:
        return                            # already playing: don't restart between rounds
    music.play(name)
    music.set_volume(A.Music)
    CurrentMusic = name

# ============ SOUND ============

def GetTone(pitch, duration):
    key = (pitch, duration)
    if key not in ToneCache:
        ToneCache[key] = tone.create(pitch, duration)
    return ToneCache[key]

def UpdateSfx(dt):
    for entry in SfxQueue[:]:
        entry[0] -= dt
        if entry[0] <= 0:
            SfxQueue.remove(entry)
            entry[1].set_volume(A.Sfx * SFX_VOLUME_SCALE)
            entry[1].play()

def PlayTones(name):
    delay = 0.0
    for pitch, duration in SFX_TONES[name]:
        SfxQueue.append([delay, GetTone(pitch, duration)])
        delay += duration
    UpdateSfx(0)                          # first note plays right away

# ============ PLAYER ============

def GetMoveInput():
    dx = (keyboard.d or keyboard.right) - (keyboard.a or keyboard.left)
    dy = (keyboard.s or keyboard.down) - (keyboard.w or keyboard.up)
    return dx, dy

def ClampToArea(char):
    if char.left < PLAY_AREA.left:
        char.left = PLAY_AREA.left
    if char.right > PLAY_AREA.right:
        char.right = PLAY_AREA.right
    if char.top < PLAY_AREA.top:
        char.top = PLAY_AREA.top
    if char.bottom > PLAY_AREA.bottom:
        char.bottom = PLAY_AREA.bottom

def AnimatePlayer(dt, moving):
    char = P.Character
    if char is None:
        return

    if not moving:
        P.Frame = 0
        P.AnimTime = 0.0
        char.image = f"student_idle_{P.Facing}"
        return
    P.AnimTime += dt
    if P.AnimTime >= RUN_FRAME_TIME:
        P.AnimTime -= RUN_FRAME_TIME
        P.Frame = (P.Frame + 1) % RUN_FRAMES
    char.image = f"student_run{P.Frame + 1}_{P.Facing}"

def MovePlayer(dt):
    char = P.Character
    if char is None:
        return
    dx, dy = GetMoveInput() if P.CanMove else (0, 0)
    moving = dx != 0 or dy != 0
    if moving:
        length = math.hypot(dx, dy)          
        char.x += dx / length * P.Speed * dt
        char.y += dy / length * P.Speed * dt
        if dx != 0:
            P.Facing = "right" if dx > 0 else "left"
        ClampToArea(char)
        CheckReachedEnd(char)
    AnimatePlayer(dt, moving)

def CheckReachedEnd(char):
    if char.right >= PLAY_AREA.right and not P.AtEnd:
        PlayerReachedEnd.fire(char)
    P.AtEnd = char.right >= PLAY_AREA.right

def OnPlayerReachedEnd(char):
    Condition = True
    if Condition:
        P.CanMove = False
        G.EnemiesMode = "Stopped"
        for enemy in EnemiesStorage:
            SetEnemyState(enemy, "idle")  
        ProjectilesStorage.clear()
        G.GameMode = Mode.BOARD                       
    else:
       char.midleft = SPAWN_POS 
                 
def PlayerHitbox():
    char = P.Character
    if char is None:
        return
    return Rect(char.x - 18, char.y - 44, 36, 92)

# ============ Enemy ============

def MatchDifficulty(name,value):
    global Difficulty
    if name != "Math_Power":
        return

    if value <= 10 :
        Difficulty = Difficulties[0]
    elif value <=20:
        Difficulty = Difficulties[1]
    elif value <=30:
        Difficulty = Difficulties[2]
    elif value <=40:
        Difficulty = Difficulties[3]

def FacingFromAngle(angle):
    return "left" if math.cos(math.radians(angle)) < 0 else "right"

def CreateEnemy(pos):
    char = Actor("thrower_idle_left", center=pos)
    base = char.angle_to((WIDTH / 2, HEIGHT / 2))         
    directions = [base - DIRECTION_SPREAD, base, base + DIRECTION_SPREAD]
    enemy = Enemie(
        Character=char,
        Operators=Operators[:Difficulty],                    # dif 1: + | 2: + - | 3: + - * | 4: + - * /
        Numbers=list(Numbers),
        Directions=directions,
        CanFollowPlayer=random.random() < FOLLOW_CHANCE[Difficulty],
    )
    enemy.Cooldown = ENEMY_COOLDOWN[Difficulty]
    enemy.CooldownLeft = random.uniform(0.5, enemy.Cooldown)  
    enemy.Angle = base
    enemy.Facing = FacingFromAngle(base)
    char.image = f"thrower_idle_{enemy.Facing}"
    return enemy

def SpawnEnemies():
    EnemiesStorage.clear()
    count = EnemiesPerDifficulty[Difficulty - 1]
    for pos in ENEMY_SPOTS[:count]:
        EnemiesStorage.append(CreateEnemy(pos))

def ChooseAngle(enemy):
    if enemy.CanFollowPlayer and P.Character:
        return enemy.Character.angle_to(P.Character)
    if enemy.Directions:
        return random.choice(enemy.Directions)
    return enemy.Angle

def ChooseSymbol(enemy):
    options = (enemy.Numbers or []) + (enemy.Operators or [])
    return random.choice(options) if options else None

def SetEnemyState(enemy, state):
    enemy.State = state
    enemy.StateTime = 0.0
    enemy.Character.image = f"thrower_{state}_{enemy.Facing}"

def UpdateEnemy(enemy, dt):
    if enemy.State == "idle":
        enemy.CooldownLeft -= dt
        if enemy.CooldownLeft <= 0:
            enemy.Angle = ChooseAngle(enemy)                
            enemy.Facing = FacingFromAngle(enemy.Angle)
            SetEnemyState(enemy, THROW_ANIM[0][0])
        return
    enemy.StateTime += dt
    names = [name for name, _ in THROW_ANIM]
    index = names.index(enemy.State)
    if enemy.StateTime < THROW_ANIM[index][1]:
        return
    if index + 1 < len(THROW_ANIM):
        SetEnemyState(enemy, THROW_ANIM[index + 1][0])
        if enemy.State == "throw":
            symbol = ChooseSymbol(enemy)
            if symbol is not None:
                EnemyThrew.fire(enemy, enemy.Angle, symbol)
    else:
        SetEnemyState(enemy, "idle")
        enemy.CooldownLeft = enemy.Cooldown

def UpdateEnemies(dt):
    if G.EnemiesMode != "Throwing":
        return
    for enemy in EnemiesStorage:
        UpdateEnemy(enemy, dt)

def DrawAim(enemy):
    char = enemy.Character
    rad = math.radians(enemy.Angle)
    end = (char.x + math.cos(rad) * 80, char.y - math.sin(rad) * 80)
    screen.draw.line(char.center, end, (255, 205, 117) if enemy.CanFollowPlayer else (65, 166, 246))

# ============ PROJECTILES ============

def SymbolImage(symbol):
    if isinstance(symbol, int):
        return f"num_{symbol}"
    return SYMBOL_IMAGES[symbol]

def OnEnemyThrew(enemy, angle, symbol):
    rad = math.radians(angle)
    dir_x, dir_y = math.cos(rad), -math.sin(rad)          # same convention as DrawAim
    char = enemy.Character
    start = (char.x + dir_x * 30, char.y + dir_y * 30)    # leaves from the hand, not the center
    actor = Actor(SymbolImage(symbol), center=start)
    ProjectilesStorage.append(Projectile(actor, symbol, dir_x * PROJECTILE_SPEED, dir_y * PROJECTILE_SPEED))

def IsOffScreen(actor):
    area = PLAY_AREA.inflate(PROJECTILE_MARGIN * 2, PROJECTILE_MARGIN * 2)
    return (actor.right < area.left or actor.left > area.right
            or actor.bottom < area.top or actor.top > area.bottom)

def IsNumber(symbol):
    return isinstance(symbol, int)

def CollectSymbol(symbol):
    PlayTones("hit_number" if IsNumber(symbol) else "hit_operator")
    table = P.Table
    if IsNumber(symbol):
        if table and IsNumber(table[-1]):
            table.append(P.LastOperator)         # 1 then 4 -> 1 <last op> 4
        if table and table[-1] == "/" and symbol == 0:
            PlayTones("crash")
            G.GameMode = Mode.GAMEOVER
            return
        table.append(symbol)
    else:
        P.LastOperator = symbol
        if table and not IsNumber(table[-1]):
            table[-1] = symbol                   # two operators in a row -> the new one replaces
        elif table:
            table.append(symbol)                 # empty table: only remembers the operator

def UpdateProjectiles(dt):
    hitbox = PlayerHitbox()
    collecting = G.EnemiesMode == "Throwing"
    for proj in ProjectilesStorage[:]:
        actor = proj.Character
        actor.x += proj.Vx * dt
        actor.y += proj.Vy * dt
        if PROJECTILE_SPIN:
            actor.angle += PROJECTILE_SPIN * dt
        if collecting and hitbox and actor.colliderect(hitbox):
            CollectSymbol(proj.Symbol)
            ProjectilesStorage.remove(proj)
            continue
        if IsOffScreen(actor):                     # garbage
            ProjectilesStorage.remove(proj)

# ============ ERASERS ============

def SpawnErasers():
    ErasersStorage.clear()
    count = ERASERS_PER_DIFFICULTY[Difficulty]
    for pos in random.sample(ERASER_SPOTS, count):
        ErasersStorage.append(Actor("eraser", center=pos))

def UpdateErasers():
    hitbox = PlayerHitbox()
    if hitbox is None:
        return
    for eraser in ErasersStorage[:]:
        if eraser.colliderect(hitbox):
            ErasersStorage.remove(eraser)
            P.Table.clear()
            P.LastOperator = "+"
            PlayTones("eraser")

# ============ BOARD ============

def IsInteger(value):
    return abs(value - round(value)) < 1e-9

def FormatNumber(value):
    return str(int(round(value))) if IsInteger(value) else f"{value:.2f}"

def CleanTable(table):
    if table and not IsNumber(table[-1]):
        return table[:-1]                        # drops a dangling operator at the end
    return table[:]

def Evaluate(tokens):
    values = [tokens[0]]                         # 1st pass: * and /   2nd pass: + and -
    ops = []
    for i in range(1, len(tokens), 2):
        op, num = tokens[i], tokens[i + 1]
        if op == "*":
            values[-1] *= num
        elif op == "/":
            values[-1] /= num
        else:
            ops.append(op)
            values.append(num)
    result = values[0]
    for op, num in zip(ops, values[1:]):
        result = result + num if op == "+" else result - num
    return result

def RandomQuestion():
    op = random.choice(Operators[:Difficulty])
    a, b = random.randint(1, 9), random.randint(1, 9)
    if op == "-" and a < b:
        a, b = b, a                              # avoids negative results
    if op == "/":
        a = a * b                                # always exact division
    return [a, op, b]

def MakeKey(value, image, center):
    size = getattr(images, image).get_size() if image else (36, 48)
    box = Rect((0, 0), size)
    box.center = (int(center[0]), int(center[1]))
    return KeypadKey(value, image, box)

def BuildKeypad():
    keys = []
    for d in range(10):
        keys.append(MakeKey(str(d), f"num_{d}", (WIDTH / 2 + (d - 4.5) * 72, HEIGHT * 0.62)))
    extras = []
    if Difficulty >= 2:
        extras.append(("-", "op_minus"))
    if Difficulty >= 4:
        extras.append((".", None))
    extras += [("del", "eraser"), ("ok", "op_equals")]
    for i, (value, image) in enumerate(extras):
        x = WIDTH / 2 + (i - (len(extras) - 1) / 2) * 96
        keys.append(MakeKey(value, image, (x, HEIGHT * 0.80)))
    return keys

def StartBoard():
    tokens = CleanTable(P.Table)
    B.Tokens = tokens if tokens else RandomQuestion()
    B.Answer = Evaluate(B.Tokens)
    B.Typed = ""
    B.Message = ""
    B.Locked = False
    B.Keys = BuildKeypad()
    PlayTones("board")

def PressKey(value):
    if B.Locked:
        return
    PlayTones("key")
    match value:
        case "del":
            B.Typed = B.Typed[:-1]
        case "ok":
            CheckAnswer()
        case "-":
            if B.Typed == "":
                B.Typed = "-"
        case ".":
            if "." not in B.Typed and B.Typed not in ("", "-"):
                B.Typed += "."
        case _:
            if len(B.Typed) < ANSWER_MAX_LEN:
                B.Typed += value

def CheckAnswer():
    try:
        typed = float(B.Typed)
    except ValueError:
        return                                   # empty or just "-"
    B.Locked = True
    if abs(typed - B.Answer) > ANSWER_TOLERANCE:
        B.Message = f"WRONG! ANSWER: {FormatNumber(B.Answer)}"
        PlayTones("wrong")
        clock.schedule_unique(BoardGameOver, RESULT_DELAY)
    elif P.Math_Power + POWER_PER_LEVEL >= VICTORY_POWER:
        B.Message = "YOU ARE A MATH MASTER! YOU WIN!"
        PlayTones("victory")
        clock.schedule_unique(GameWon, RESULT_DELAY * 2)
    else:
        B.Message = f"CORRECT! +{POWER_PER_LEVEL} MATH POWER"
        PlayTones("correct")
        clock.schedule_unique(NextLevel, RESULT_DELAY)

def NextLevel():
    P.Math_Power += POWER_PER_LEVEL              # updates Difficulty before spawning
    G.GameMode = Mode.PLAYING

def BoardGameOver():
    G.GameMode = Mode.GAMEOVER

def GameWon():
    exit()

def KeyAt(pos):
    for key in B.Keys:
        if key.Box.collidepoint(pos):
            return key
    return None

# ============ DIRECTION ARROW ============

def ShowArrow():
    global ArrowVisible
    ArrowVisible = True
    StopAllAnimations(group="arrow")
    ArrowHint.x = ARROW_POS[0]
    AddAnimation(ArrowHint, tween="accel_decel", duration=0.5, loops=-1, yoyo=True,
                 group="arrow", x=ARROW_POS[0] + 20)
    clock.schedule_unique(HideArrow, ARROW_TIME)

def HideArrow():
    global ArrowVisible
    ArrowVisible = False
    StopAllAnimations(group="arrow")

# ============ ANIMATIONS ============

def _StartAnimation(entry):
    def finished():
        if entry.loops_left != 0:
            if entry.loops_left > 0:
                entry.loops_left -= 1
            if entry.yoyo:
                entry.forward = not entry.forward   # flips direction
                _StartAnimation(entry)
            else:
                _RestartFromInitial(entry)
            return
        if entry in AnimationStorage:
            AnimationStorage.remove(entry)
        if entry.on_finished:
            entry.on_finished()
    goal = entry.targets if entry.forward else entry.initial
    entry.anim = animate(entry.obj, entry.tween, entry.duration, on_finished=finished, **goal)

def _RestartFromInitial(entry):
    entry.forward = True
    for k, v in entry.initial.items():
        setattr(entry.obj, k, v)
    _StartAnimation(entry)

def _InGroup(entry, group):
    return group is None or entry.group == group

def AddAnimation(obj, tween="linear", duration=1, on_finished=None, loops=0, yoyo=False, group=None, **targets):
    entry = ManagedAnimation(obj, tween, duration, on_finished, loops, yoyo, group, targets)
    AnimationStorage.append(entry)
    _StartAnimation(entry)
    return entry

def StopAnimation(entry, complete=False):
    if entry.anim.running:
        entry.anim.stop(complete)
    if entry in AnimationStorage:
        AnimationStorage.remove(entry)

def StopAllAnimations(group=None, complete=False):
    for entry in AnimationStorage[:]:
        if _InGroup(entry, group):
            StopAnimation(entry, complete)

def StartMenuAnimations():
    global TitleFloat
    if TitleFloat is None:
        TitleFloat = AddAnimation(TitleLabel, tween="accel_decel", duration=1.2,
                                  loops=-1, yoyo=True, group="menu", y=TitleLabel.y - 8)

# ============ DRAW ============

def DrawText(text, size, color, shadow_color, **pos):
    screen.draw.text(
        text, fontname=FONT, fontsize=size, color=color,
        shadow=(0, size / 12), scolor=shadow_color, **pos
        )

def DrawButtonLabel(btn):
    label = ButtonLabels.get(BaseName(btn))
    if label:
        DrawText(label[0], 24, "white", label[1], center=(btn.x, btn.y - 4))

def DrawMenu():
    for image in MenuImages:
        screen.blit(image[0], image[1])

    DrawText(TitleLabel.text, 32, (255, 205, 117), (93, 39, 93), center=(TitleLabel.x, TitleLabel.y))

    for btn in MenuButtons:
        btn.draw()
        DrawButtonLabel(btn)

def DrawSlider(key, label, track):
    value = getattr(A, key)
    text_y = track.y - 48
    DrawText(label, 24, "white", (86, 108, 134), topleft=(PANEL_X + 76, text_y))
    DrawText(f"{round(value * 100)}%", 24, (255, 205, 117), (93, 39, 93), topright=(track.right, text_y))
    fill = Rect(track.x, track.y, int(track.width * value), track.height)
    screen.draw.filled_rect(fill, (56, 183, 100))
    knob = "menu_slider_knob_hover" if key in (DraggingSlider, HoverSlider) else "menu_slider_knob"
    screen.blit(knob, (track.x + track.width * value - 12, track.centery - 20))

def DrawSettings():
    screen.blit("menu_overlay", (0, 0))
    screen.blit("menu_sound_panel", (PANEL_X, PANEL_Y))
    DrawText("SOUND", 24, (255, 205, 117), (93, 39, 93), center=(PANEL_X + PANEL_W / 2, PANEL_Y + 44))
    for key, (label, track) in Sliders.items():
        DrawSlider(key, label, track)
    for btn in SettingsButtons:
        btn.draw()
        DrawButtonLabel(btn)

def DrawArrow():
    if not ArrowVisible:
        return
    x, y = ArrowHint.x, ArrowHint.y
    points = [(x - 40, y - 8), (x, y - 8), (x, y - 22), (x + 32, y),
              (x, y + 22), (x, y + 8), (x - 40, y + 8)]
    game.pygame.draw.polygon(screen.surface, ARROW_COLOR, points)
    game.pygame.draw.polygon(screen.surface, ARROW_OUTLINE, points, 3)
    DrawText(ArrowHint.text, 32, ARROW_COLOR, ARROW_OUTLINE, midbottom=(x, y - 28))

def DrawActors():
    for eraser in ErasersStorage:
        eraser.draw()
    actors = [e.Character for e in EnemiesStorage]
    if P.Character:
        actors.append(P.Character)
    for actor in sorted(actors, key=lambda a: a.bottom):    
        actor.draw()
    for proj in ProjectilesStorage:
        proj.Character.draw()
    if DEBUG_AIM:
        for enemy in EnemiesStorage:
            DrawAim(enemy)
    DrawArrow()

def DrawGlyph(char, x, y):
    image = GLYPH_IMAGES.get(char)
    if image:
        screen.blit(image, (x, y))
    else:
        DrawText(char, 48, "white", (40, 40, 40), center=(x + 18, y + 24))

def DrawBoard():
    bx, by = BOARD_POS
    bw, bh = BOARD_SIZE
    screen.blit("chalkboard", BOARD_POS)
    text = "".join(str(t) for t in B.Tokens) + "=" + (B.Typed or "?")
    lines = [text[i:i + GLYPHS_PER_LINE] for i in range(0, len(text), GLYPHS_PER_LINE)]
    top = BOARD_TEXT_CENTER_Y - len(lines) * LINE_STEP / 2
    for row, line in enumerate(lines):
        left = bx + bw / 2 - len(line) * GLYPH_STEP / 2
        for col, char in enumerate(line):
            DrawGlyph(char, left + col * GLYPH_STEP + 2, top + row * LINE_STEP)
    if "/" in B.Tokens:
        DrawText("2 DECIMAL PLACES", 18, "white", (40, 40, 40), center=(bx + bw / 2, by + 200))
    if B.Message:
        color = (230, 72, 72) if B.Message.startswith("WRONG") else (56, 183, 100)
        DrawText(B.Message, 32, color, (40, 40, 40), center=(WIDTH / 2, by + bh + 26))
    for key in B.Keys:
        lift = -4 if key.Box.collidepoint(MousePos) and not B.Locked else 0
        if key.Image:
            screen.blit(key.Image, (key.Box.x, key.Box.y + lift))
        else:
            DrawText(key.Value, 48, "white", (40, 40, 40), center=(key.Box.centerx, key.Box.centery + lift))
        label = KEY_LABELS.get(key.Value)
        if label:
            DrawText(label, 18, "white", (40, 40, 40), midtop=(key.Box.centerx, key.Box.bottom + 4))
    screen.blit("cursor_pencil", (MousePos[0] - PENCIL_TIP[0], MousePos[1] - PENCIL_TIP[1]))

def DrawGameMode():
    if G.GameMode == Mode.MENU:
        DrawMenu()
    if G.GameMode == Mode.PLAYING:
        screen.blit("game_bg", (0, 0))
        DrawActors()
    if G.GameMode == Mode.BOARD:
        screen.blit("game_bg", (0, 0))
        DrawBoard()

# ============ CHECK-UPS ============

def CheckGameMode(name,value):
    if name != "GameMode":
        return                     
    match value:
        case Mode.MENU:
            StartMenuAnimations()
            PlayMusic("menu_music")
        case Mode.PLAYING:
            P.CanMove = True
            P.AtEnd = False
            P.Table = []
            P.LastOperator = "+"
            ProjectilesStorage.clear()
            G.EnemiesMode = "Throwing"
            P.Character = Actor(f"student_idle_{P.Facing}", midleft=SPAWN_POS)
            SpawnEnemies()
            SpawnErasers()
            game.pygame.mouse.set_visible(True)
            StopAllAnimations(group="menu")
            if GAME_MUSIC:
                PlayMusic(GAME_MUSIC)
            else:
                music.fadeout(0.5)
            ShowArrow()
        case Mode.BOARD:
            P.Character = None
            EnemiesStorage.clear()
            ProjectilesStorage.clear()
            ErasersStorage.clear()
            StartBoard()
            HideArrow()
            game.pygame.mouse.set_visible(False)
        case Mode.GAMEOVER:
            exit()

def MenuClick(name):
    match name:
        case "menu_btn_play":
            G.GameMode = Mode.PLAYING
        case "menu_btn_exit":
            exit()
        case "menu_btn_config":
            G.SettingsOpen = True
        case "menu_btn_back":
            G.SettingsOpen = False

def ApplyVolume(name, value):
    if name == "Music":
        music.set_volume(value)

# ============ EVENTS HOOKS PYGAME ZERO ============

def on_mouse_down(pos, button):
    global DraggingSlider
    if button != mouse.LEFT:
        return
    if G.GameMode == Mode.BOARD:
        key = KeyAt(pos)
        if key:
            PressKey(key.Value)
        return
    for btn in ActiveButtons():
        if btn.collidepoint(pos):
            MenuClick(BaseName(btn))
            return
    if G.SettingsOpen:
        DraggingSlider = SliderAt(pos)
        if DraggingSlider:
            SetSlider(DraggingSlider, pos[0])

def on_mouse_up(pos, button):
    global DraggingSlider
    DraggingSlider = None

def on_mouse_move(pos, rel, buttons):
    global HoverSlider, MousePos
    MousePos = pos
    for btn in ActiveButtons():
        base = BaseName(btn)
        btn.image = base + "_hover" if btn.collidepoint(pos) else base
    if G.SettingsOpen:
        HoverSlider = SliderAt(pos)
        if DraggingSlider:
            SetSlider(DraggingSlider, pos[0])

def on_key_down(key,mod,unicode):
    if G.GameMode == Mode.BOARD:
        available = [k.Value for k in B.Keys]
        if unicode and unicode in available:
            PressKey(unicode)
        elif key == keys.BACKSPACE:
            PressKey("del")
        elif key in (keys.RETURN, keys.KP_ENTER):
            PressKey("ok")

def on_key_up(key,mod):
    pass

def draw():
    screen.clear()
    DrawGameMode()
    if G.SettingsOpen:
        DrawSettings()

def update(dt):
    UpdateSfx(dt)
    if G.GameMode == Mode.PLAYING and not G.SettingsOpen and P.Character:
        MovePlayer(dt)
        UpdateEnemies(dt)
        UpdateProjectiles(dt)
        UpdateErasers()

# =========== INITIALIZATION ============

G.changed.connect(CheckGameMode)
A.changed.connect(ApplyVolume)
P.changed.connect(MatchDifficulty)
PlayerReachedEnd.connect(OnPlayerReachedEnd)
EnemyThrew.connect(OnEnemyThrew)

G.GameMode = Mode.MENU
pgzrun.os.environ["SDL_VIDEO_CENTERED"]="1"
game.DISPLAY_FLAGS = game.pygame.SCALED | game.pygame.FULLSCREEN
pgzrun.go()


