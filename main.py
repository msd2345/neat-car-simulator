import pygame
import os
import math
import sys
import neat

# ── Screen ──────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1244
SCREEN_HEIGHT = 1016
FPS           = 60

pygame.init()
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("NEAT Car Simulator")
CLOCK  = pygame.time.Clock()

# ── Fonts ────────────────────────────────────────────────────────────────────
FONT_BIG   = pygame.font.SysFont("consolas", 28, bold=True)
FONT_MED   = pygame.font.SysFont("consolas", 20)
FONT_SMALL = pygame.font.SysFont("consolas", 15)

# ── Colours ──────────────────────────────────────────────────────────────────
GRASS_COLOR = pygame.Color(2, 105, 31, 255)
WHITE       = (255, 255, 255)
CYAN        = (0,   255, 255)
GREEN_HUD   = (0,   220, 80)
RED         = (220, 50,  50)
YELLOW      = (255, 220, 0)
FINISH_RED  = (255, 80,  80)
DARK_UI     = (15,  15,  25)
PANEL_BG    = (20,  20,  35, 200)
ROAD_GRAY   = (80,  80,  90)

# ── Paths ────────────────────────────────────────────────────────────────────
PATH_DEFAULT = os.path.join("Assets", "track_default.png")
PATH_CUSTOM  = os.path.join("Assets", "track_custom.png")

# ── Global state ─────────────────────────────────────────────────────────────
cars           = []
ge             = []
nets           = []
generation     = 0
best_fitness   = 0
speed_mult     = 1.0
show_radars    = True
current_track  = None
finish_line    = None
car_start_pos  = (490, 820)
return_to_menu = False


# ═══════════════════════════════════════════════════════════════════════════════
#  CAR
# ═══════════════════════════════════════════════════════════════════════════════
class Car(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = pygame.image.load(
            os.path.join("Assets", "car.png")).convert_alpha()
        self.image          = self.original_image
        self.rect           = self.image.get_rect(center=car_start_pos)
        self.vel_vector     = pygame.math.Vector2(0.8, 0)
        self.angle          = 0
        self.rotation_vel   = 5
        self.direction      = 0
        self.alive          = True
        self.radars         = []
        self.distance       = 0
        self.time_alive     = 0
        self.laps           = 0
        self.crossed_finish = False

    def update(self):
        self.radars.clear()
        self.drive()
        self.rotate()
        for a in (-60, -30, 0, 30, 60):
            self.radar(a)
        self.collision()
        self.check_finish()
        self.time_alive += 1

    def drive(self):
        move = self.vel_vector * 7 * speed_mult
        self.rect.center += move
        self.distance     += move.length()

    def collision(self):
        length = 40
        cr = [int(self.rect.center[0] + math.cos(math.radians(self.angle + 18)) * length),
              int(self.rect.center[1] - math.sin(math.radians(self.angle + 18)) * length)]
        cl = [int(self.rect.center[0] + math.cos(math.radians(self.angle - 18)) * length),
              int(self.rect.center[1] - math.sin(math.radians(self.angle - 18)) * length)]
        for pt in (cr, cl):
            pt[0] = max(0, min(SCREEN_WIDTH  - 1, pt[0]))
            pt[1] = max(0, min(SCREEN_HEIGHT - 1, pt[1]))
        if SCREEN.get_at(cr) == GRASS_COLOR or SCREEN.get_at(cl) == GRASS_COLOR:
            self.alive = False
        pygame.draw.circle(SCREEN, CYAN, cr, 4)
        pygame.draw.circle(SCREEN, CYAN, cl, 4)

    def rotate(self):
        if self.direction ==  1:
            self.angle -= self.rotation_vel
            self.vel_vector.rotate_ip( self.rotation_vel)
        if self.direction == -1:
            self.angle += self.rotation_vel
            self.vel_vector.rotate_ip(-self.rotation_vel)
        self.image = pygame.transform.rotozoom(self.original_image, self.angle, 0.1)
        self.rect  = self.image.get_rect(center=self.rect.center)

    def radar(self, radar_angle):
        length = 0
        x = int(self.rect.center[0])
        y = int(self.rect.center[1])
        while length < 200:
            nx = int(self.rect.center[0] + math.cos(math.radians(self.angle + radar_angle)) * length)
            ny = int(self.rect.center[1] - math.sin(math.radians(self.angle + radar_angle)) * length)
            if nx < 0 or nx >= SCREEN_WIDTH or ny < 0 or ny >= SCREEN_HEIGHT:
                break
            if SCREEN.get_at((nx, ny)) == GRASS_COLOR:
                break
            x, y = nx, ny
            length += 1
        if show_radars:
            pygame.draw.line(SCREEN, WHITE, self.rect.center, (x, y), 1)
            pygame.draw.circle(SCREEN, (0, 255, 0), (x, y), 3)
        dist = int(math.hypot(self.rect.center[0] - x, self.rect.center[1] - y))
        self.radars.append([radar_angle, dist])

    def check_finish(self):
        if finish_line is None:
            return
        fx1, fy1, fx2, fy2 = finish_line
        cx, cy = self.rect.center

        # Project car centre onto the finish line segment and check distance
        dx, dy = fx2 - fx1, fy2 - fy1
        length = math.hypot(dx, dy)
        if length == 0:
            return
        # How far along the line is the car's closest point (0..1)
        t = max(0.0, min(1.0, ((cx - fx1) * dx + (cy - fy1) * dy) / (length * length)))
        closest_x = fx1 + t * dx
        closest_y = fy1 + t * dy
        dist = math.hypot(cx - closest_x, cy - closest_y)

        if dist < 18 and not self.crossed_finish:
            self.laps += 1
            self.crossed_finish = True
        elif dist >= 18:
            self.crossed_finish = False

    def data(self):
        return [int(r[1]) for r in self.radars]


# ═══════════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════════
def draw_hud():
    panel = pygame.Surface((280, 210), pygame.SRCALPHA)
    panel.fill(PANEL_BG)
    SCREEN.blit(panel, (10, 10))

    top_laps = max((c.sprite.laps for c in cars), default=0)
    lines = [
        (f"GEN    {generation:>4}",                    GREEN_HUD),
        (f"ALIVE  {len(cars):>4}",                      WHITE),
        (f"BEST   {int(best_fitness):>6}",              YELLOW),
        (f"LAPS   {top_laps:>4}",                       FINISH_RED),
        (f"SPEED  {speed_mult:.0f}x",                   CYAN),
        (f"RADARS {'ON' if show_radars else 'OFF'}",    CYAN),
    ]
    for i, (txt, col) in enumerate(lines):
        SCREEN.blit(FONT_MED.render(txt, True, col), (20, 18 + i * 30))

    if finish_line:
        fx1, fy1, fx2, fy2 = finish_line
        pygame.draw.line(SCREEN, FINISH_RED, (fx1, fy1), (fx2, fy2), 5)
        pygame.draw.line(SCREEN, WHITE,      (fx1, fy1), (fx2, fy2), 1)

    hints = "[R] Radars  [S] Speed  [M] Map Editor  [ESC] Menu"
    SCREEN.blit(FONT_SMALL.render(hints, True, (140, 140, 160)), (10, SCREEN_HEIGHT - 22))


# ═══════════════════════════════════════════════════════════════════════════════
#  NEAT CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════
def remove(index):
    cars.pop(index)
    ge.pop(index)
    nets.pop(index)


def eval_genomes(genomes, config):
    global cars, ge, nets, generation, best_fitness, speed_mult, show_radars
    global current_track, finish_line, car_start_pos, return_to_menu

    if return_to_menu:
        return

    generation += 1
    cars, ge, nets = [], [], []

    for _, genome in genomes:
        cars.append(pygame.sprite.GroupSingle(Car()))
        ge.append(genome)
        nets.append(neat.nn.FeedForwardNetwork.create(genome, config))
        genome.fitness = 0

    while True:
        CLOCK.tick(FPS * int(speed_mult))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return_to_menu = True
                    return
                if event.key == pygame.K_r:
                    show_radars = not show_radars
                if event.key == pygame.K_s:
                    speed_mult = {1.0: 2.0, 2.0: 4.0, 4.0: 1.0}[speed_mult]
                if event.key == pygame.K_m:
                    result = run_map_editor(SCREEN, FONT_BIG, FONT_MED, FONT_SMALL)
                    if result:
                        current_track, car_start_pos, finish_line = result
                    return eval_genomes(genomes, config)

        SCREEN.blit(current_track, (0, 0))

        if not cars:
            break

        i = 0
        while i < len(cars):
            ge[i].fitness += 1
            ge[i].fitness += cars[i].sprite.laps * 1000
            if not cars[i].sprite.alive:
                remove(i)
            else:
                i += 1

        best_fitness = max((g.fitness for g in ge), default=best_fitness)

        for car in cars:
            car.draw(SCREEN)
            car.update()

        for i, car in enumerate(cars):
            input_data = car.sprite.data()
            if len(input_data) < 5:
                continue
            out = nets[i].activate(input_data)
            if out[0] > 0.7:
                car.sprite.direction =  1
            elif out[1] > 0.7:
                car.sprite.direction = -1
            else:
                car.sprite.direction =  0

        draw_hud()
        pygame.display.flip()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAP EDITOR
# ═══════════════════════════════════════════════════════════════════════════════
BRUSH_SIZES   = [8, 16, 32, 48, 64]
TOOL_ROAD     = "road"
TOOL_ERASER   = "eraser"
TOOL_STARTPOS = "start"
TOOL_FINISH   = "finish"


def run_map_editor(screen, font_big, font_med, font_small):
    canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    canvas.fill(GRASS_COLOR)

    if os.path.exists(PATH_CUSTOM):
        canvas.blit(pygame.image.load(PATH_CUSTOM).convert(), (0, 0))

    brush_idx        = 2
    tool             = TOOL_ROAD
    drawing          = False
    start_pos        = (490, 820)
    finish_line      = None
    finish_line_start = None   # first click of two-click finish line
    show_help        = True

    PANEL_W  = 220
    CANVAS_W = SCREEN_WIDTH - PANEL_W
    clock    = pygame.time.Clock()

    tools_list = [
        (TOOL_ROAD,     "Road (gray)",  (120, 120, 130)),
        (TOOL_ERASER,   "Eraser",       GREEN_HUD),
        (TOOL_STARTPOS, "Set Start",    YELLOW),
        (TOOL_FINISH,   "Finish Line",  FINISH_RED),
    ]

    def draw_ui():
        pygame.draw.rect(screen, (18, 18, 30), (CANVAS_W, 0, PANEL_W, SCREEN_HEIGHT))
        pygame.draw.line(screen, (60, 60, 80), (CANVAS_W, 0), (CANVAS_W, SCREEN_HEIGHT), 2)

        y = 20
        screen.blit(font_big.render("MAP EDITOR", True, (80, 200, 255)), (CANVAS_W + 10, y)); y += 45

        for tkey, tlabel, tcol in tools_list:
            border = WHITE if tool == tkey else (50, 50, 70)
            pygame.draw.rect(screen, border, (CANVAS_W + 8, y, PANEL_W - 16, 34), 2, border_radius=6)
            if tool == tkey:
                pygame.draw.rect(screen, (30, 30, 50), (CANVAS_W + 10, y + 2, PANEL_W - 20, 30), border_radius=5)
            screen.blit(font_small.render(tlabel, True, tcol), (CANVAS_W + 16, y + 9))
            y += 42

        y += 10
        screen.blit(font_med.render("Brush Size", True, WHITE), (CANVAS_W + 10, y)); y += 28
        for si, sz in enumerate(BRUSH_SIZES):
            col = YELLOW if si == brush_idx else (80, 80, 100)
            pygame.draw.circle(screen, col, (CANVAS_W + 30 + si * 36, y + 14), sz // 4 + 4)
        y += 50

        screen.blit(font_small.render(f"Start: {start_pos}", True, (180, 180, 200)), (CANVAS_W + 10, y)); y += 22

        if finish_line_start:
            fl_txt = "Finish: click 2nd pt"
            fl_col = YELLOW
        elif finish_line:
            fl_txt = "Finish: set"
            fl_col = FINISH_RED
        else:
            fl_txt = "Finish: none"
            fl_col = (100, 100, 120)
        screen.blit(font_small.render(fl_txt, True, fl_col), (CANVAS_W + 10, y)); y += 30

        for txt, col in [("[C] Clear", RED), ("[S] Save+Exit", GREEN_HUD), ("[ESC] Back to Menu", (160, 160, 160))]:
            screen.blit(font_med.render(txt, True, col), (CANVAS_W + 10, y)); y += 32

        if show_help:
            for hl in ["LMB - draw/place", "RMB - quick erase", "Scroll - brush", "H - help", "1-4 - tools"]:
                screen.blit(font_small.render(hl, True, (120, 120, 140)), (CANVAS_W + 10, y)); y += 20

        # ── canvas overlays ──
        pygame.draw.circle(screen, YELLOW, start_pos, 10, 3)
        pygame.draw.circle(screen, WHITE,  start_pos,  4)

        # Completed finish line
        if finish_line:
            fx1, fy1, fx2, fy2 = finish_line
            pygame.draw.line(screen, FINISH_RED, (fx1, fy1), (fx2, fy2), 6)
            pygame.draw.line(screen, WHITE,      (fx1, fy1), (fx2, fy2), 2)
            pygame.draw.circle(screen, FINISH_RED, (fx1, fy1), 5)
            pygame.draw.circle(screen, FINISH_RED, (fx2, fy2), 5)

        # Live preview while placing first point
        if finish_line_start:
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(screen, FINISH_RED, finish_line_start, 6)
            pygame.draw.line(screen, FINISH_RED, finish_line_start, (mx, my), 3)
            pygame.draw.circle(screen, YELLOW, (mx, my), 5, 2)

    while True:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_h:
                    show_help = not show_help
                if event.key == pygame.K_c:
                    canvas.fill(GRASS_COLOR)
                    finish_line       = None
                    finish_line_start = None
                if event.key == pygame.K_s:
                    pygame.image.save(canvas, PATH_CUSTOM)
                    return canvas.copy(), start_pos, finish_line
                if event.key == pygame.K_1: tool = TOOL_ROAD
                if event.key == pygame.K_2: tool = TOOL_ERASER
                if event.key == pygame.K_3: tool = TOOL_STARTPOS
                if event.key == pygame.K_4: tool = TOOL_FINISH

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if mx >= CANVAS_W:
                    # Panel clicks — tool selection
                    tools_y_start = 65
                    for ti in range(len(tools_list)):
                        ty = tools_y_start + ti * 42
                        if ty <= my <= ty + 34:
                            tool = tools_list[ti][0]
                            finish_line_start = None  # cancel pending finish
                    # Brush size row
                    brush_row_y = tools_y_start + len(tools_list) * 42 + 38
                    if brush_row_y <= my <= brush_row_y + 30:
                        for si in range(len(BRUSH_SIZES)):
                            if abs(mx - (CANVAS_W + 30 + si * 36)) < 16:
                                brush_idx = si
                else:
                    if event.button == 1:
                        if tool == TOOL_STARTPOS:
                            start_pos = (mx, my)
                        elif tool == TOOL_FINISH:
                            if finish_line_start is None:
                                # First click — store start point
                                finish_line_start = (mx, my)
                            else:
                                # Second click — complete the line
                                finish_line       = (*finish_line_start, mx, my)
                                finish_line_start = None
                        else:
                            drawing = True
                    elif event.button == 3:
                        # Right click cancels a pending finish line, otherwise erases
                        if finish_line_start is not None:
                            finish_line_start = None
                        else:
                            drawing = True
                            tool    = TOOL_ERASER

            elif event.type == pygame.MOUSEBUTTONUP:
                drawing = False
                if event.button == 3 and tool == TOOL_ERASER:
                    tool = TOOL_ROAD

            elif event.type == pygame.MOUSEWHEEL:
                brush_idx = max(0, min(len(BRUSH_SIZES) - 1, brush_idx - event.y))

        if drawing:
            mx, my = pygame.mouse.get_pos()
            if mx < CANVAS_W:
                sz = BRUSH_SIZES[brush_idx]
                if tool == TOOL_ROAD:
                    pygame.draw.circle(canvas, ROAD_GRAY, (mx, my), sz)
                elif tool == TOOL_ERASER:
                    pygame.draw.circle(canvas, GRASS_COLOR, (mx, my), sz)

        screen.blit(canvas, (0, 0))
        overlay = pygame.Surface((CANVAS_W, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 20))
        screen.blit(overlay, (0, 0))
        draw_ui()
        pygame.display.flip()


# ═══════════════════════════════════════════════════════════════════════════════
#  LAUNCHER
# ═══════════════════════════════════════════════════════════════════════════════
def show_launcher(screen):
    global finish_line, car_start_pos

    clock = pygame.time.Clock()

    if not os.path.exists(PATH_DEFAULT):
        src = pygame.image.load(os.path.join("Assets", "track.png")).convert()
        pygame.image.save(src, PATH_DEFAULT)

    default_track = pygame.image.load(PATH_DEFAULT).convert()

    options = [("  TRAIN ON DEFAULT TRACK", "default"),
           ("  BUILD A CUSTOM MAP",     "editor")]
    if os.path.exists(PATH_CUSTOM):
        options.insert(1, ("  LOAD SAVED CUSTOM MAP", "load_custom"))
        options.insert(2, ("  DELETE SAVED CUSTOM MAP", "delete_custom"))

    selected = 0

    while True:
        clock.tick(60)
        options = [("  TRAIN ON DEFAULT TRACK", "default"),
                   ("  BUILD A CUSTOM MAP",     "editor")]
        if os.path.exists(PATH_CUSTOM):
            options.insert(1, ("  LOAD SAVED CUSTOM MAP", "load_custom"))
            options.insert(2, ("  DELETE SAVED CUSTOM MAP", "delete_custom"))
        selected = max(0, min(selected, len(options) - 1))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    result = _handle_choice(options[selected][1], screen, default_track)
                    if result is not None:
                        return result
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, (_, key) in enumerate(options):
                    by = SCREEN_HEIGHT // 2 - 20 + i * 70
                    if by <= event.pos[1] <= by + 50:
                        selected = i
                        result = _handle_choice(key, screen, default_track)
                        if result is not None:
                            return result

        screen.fill(DARK_UI)
        preview = pygame.transform.scale(default_track, (SCREEN_WIDTH, SCREEN_HEIGHT))
        preview.set_alpha(40)
        screen.blit(preview, (0, 0))

        title = FONT_BIG.render("NEAT  CAR  SIMULATOR", True, GREEN_HUD)
        sub   = FONT_SMALL.render("Neuro-Evolution of Augmenting Topologies", True, (100, 180, 130))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 140)))
        screen.blit(sub,   sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100)))

        for i, (label, key) in enumerate(options):
            by     = SCREEN_HEIGHT // 2 - 20 + i * 70
            is_sel = i == selected
            is_delete = key == "delete_custom"
            bg  = (80, 20, 20) if (is_sel and is_delete) else (30, 80, 50) if is_sel else (20, 20, 35)
            brd = RED if is_delete else GREEN_HUD if is_sel else (50, 50, 70)
            txt_col = RED if is_delete else WHITE if is_sel else (140, 140, 160)
            pygame.draw.rect(screen, bg,  (SCREEN_WIDTH // 2 - 220, by, 440, 50), border_radius=8)
            pygame.draw.rect(screen, brd, (SCREEN_WIDTH // 2 - 220, by, 440, 50), 2, border_radius=8)
            screen.blit(FONT_MED.render(label, True, txt_col), (SCREEN_WIDTH // 2 - 200, by + 14))

        hint = FONT_SMALL.render("UP/DOWN navigate   ENTER select", True, (80, 80, 100))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)))
        pygame.display.flip()


def _handle_choice(key, screen, default_track):
    global finish_line, car_start_pos
    if key == "default":
        finish_line   = None
        car_start_pos = (490, 820)
        return default_track
    elif key == "editor":
        result = run_map_editor(screen, FONT_BIG, FONT_MED, FONT_SMALL)
        if result:
            track, car_start_pos, finish_line = result
            return track
        return None
    elif key == "load_custom":
        finish_line   = None
        car_start_pos = (490, 820)
        return pygame.image.load(PATH_CUSTOM).convert()
    elif key == "delete_custom":
        if os.path.exists(PATH_CUSTOM):
            os.remove(PATH_CUSTOM)
        return None   # stay on launcher, options will refresh
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def run(config_path):
    global current_track, return_to_menu, generation, best_fitness

    config = neat.config.Config(
        neat.DefaultGenome, neat.DefaultReproduction,
        neat.DefaultSpeciesSet, neat.DefaultStagnation,
        config_path)

    while True:
        return_to_menu = False
        generation     = 0
        best_fitness   = 0

        current_track = show_launcher(SCREEN)

        pop = neat.Population(config)
        pop.add_reporter(neat.StdOutReporter(True))
        pop.add_reporter(neat.StatisticsReporter())

        try:
            pop.run(eval_genomes, 50)
        except Exception:
            pass

    # Whether H or ESC was pressed, or training finished — loop back to launcher
        continue


if __name__ == '__main__':
    local_dir   = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config.txt')
    run(config_path)
