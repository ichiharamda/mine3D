import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import random
import sys
import numpy as np

glutInit(sys.argv)

# 初期設定
pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.DOUBLEBUF | pygame.OPENGL)
pygame.display.set_caption("3D Minesweeper")


# 3Dボード設定
cube_size = 4  # 各軸のセル数
cell_size = 1  # 各セルのサイズ
mine_num = 5  # 地雷の数

# グリッドと状態
grid = [[[0 for _ in range(cube_size)] for _ in range(cube_size)] for _ in range(cube_size)]
revealed = [[[False for _ in range(cube_size)] for _ in range(cube_size)] for _ in range(cube_size)]
flags = [[[False for _ in range(cube_size)] for _ in range(cube_size)] for _ in range(cube_size)]
mine_positions = []
game_over = False

# 地雷をランダムに配置
def place_mines():
    placed_mines = 0
    while placed_mines < mine_num:
        x, y, z = random.randint(0, cube_size - 1), random.randint(0, cube_size - 1), random.randint(0, cube_size - 1)
        if grid[x][y][z] != 9:
            grid[x][y][z] = 9
            mine_positions.append((x, y, z))
            placed_mines += 1

# 各セルの周囲地雷数設定
def set_mine_counts():
    for x, y, z in mine_positions:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if 0 <= nx < cube_size and 0 <= ny < cube_size and 0 <= nz < cube_size and grid[nx][ny][nz] != 9:
                        grid[nx][ny][nz] += 1

# レイキャストによるクリック検出
def ray_intersects_cube(ray_origin, ray_direction, cube_min, cube_max):
    t1 = (cube_min - ray_origin) / ray_direction
    t2 = (cube_max - ray_origin) / ray_direction
    
    tmin = np.minimum(t1, t2)
    tmax = np.maximum(t1, t2)
    
    largest_min = np.max(tmin)
    smallest_max = np.min(tmax)
    
    return smallest_max >= largest_min and smallest_max >= 0

def check_click(x, y):
    viewport = glGetIntegerv(GL_VIEWPORT)
    modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
    projection = glGetDoublev(GL_PROJECTION_MATRIX)
    
    # スクリーン座標からワールド座標への変換
    y = viewport[3] - y
    z_near = 0.1
    ray_start = np.array(gluUnProject(x, y, z_near, modelview, projection, viewport))
    ray_end = np.array(gluUnProject(x, y, 1.0, modelview, projection, viewport))
    ray_direction = ray_end - ray_start
    ray_direction = ray_direction / np.linalg.norm(ray_direction)

    closest_distance = float('inf')
    closest_cell = None

    # 各セルとの交差判定
    for i in range(cube_size):
        for j in range(cube_size):
            for k in range(cube_size):
                if revealed[i][j][k]:
                    continue
                
                # セルの中心座標
                center = np.array([
                    i - cube_size/2,
                    j - cube_size/2,
                    k - cube_size/2
                ])
                
                # セルのバウンディングボックス
                cube_min = center - cell_size/2
                cube_max = center + cell_size/2
                
                if ray_intersects_cube(ray_start, ray_direction, cube_min, cube_max):
                    distance = np.linalg.norm(center - ray_start)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_cell = (i, j, k)
    
    return closest_cell

# セルの開示
def reveal_cell(x, y, z):
    global game_over
    if not (0 <= x < cube_size and 0 <= y < cube_size and 0 <= z < cube_size) or revealed[x][y][z]:
        return
    
    revealed[x][y][z] = True
    
    if grid[x][y][z] == 9:
        game_over = True
        # ゲームオーバー時に全ての地雷を表示
        for mx, my, mz in mine_positions:
            revealed[mx][my][mz] = True
        print("Game Over!")
    elif grid[x][y][z] == 0:
        # 周囲のセルも開く
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    reveal_cell(x + dx, y + dy, z + dz)

# セルの描画
def draw_cell(x, y, z, color, outline=True, text=None):
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3fv(color)
    
    # キューブの描画
    glBegin(GL_QUADS)
    vertices = [
        ( 0.5,  0.5,  0.5), ( 0.5, -0.5,  0.5), (-0.5, -0.5,  0.5), (-0.5,  0.5,  0.5),  # 前面
        ( 0.5,  0.5, -0.5), ( 0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5,  0.5, -0.5),  # 背面
    ]
    faces = [
        (0, 1, 2, 3),  # 前面
        (4, 5, 6, 7),  # 背面
        (0, 4, 7, 3),  # 上面
        (1, 5, 6, 2),  # 下面
        (0, 4, 5, 1),  # 右面
        (3, 7, 6, 2),  # 左面
    ]
    for face in faces:
        for vertex in face:
            v = vertices[vertex]
            glVertex3f(v[0] * cell_size/2, v[1] * cell_size/2, v[2] * cell_size/2)
    glEnd()
    
    # 枠線の描画
    if outline:
        glColor3f(0, 0, 0)
        glBegin(GL_LINES)
        for i in range(4):
            glVertex3f(vertices[i][0] * cell_size/2, vertices[i][1] * cell_size/2, vertices[i][2] * cell_size/2)
            glVertex3f(vertices[(i+1)%4][0] * cell_size/2, vertices[(i+1)%4][1] * cell_size/2, vertices[(i+1)%4][2] * cell_size/2)
            glVertex3f(vertices[i+4][0] * cell_size/2, vertices[i+4][1] * cell_size/2, vertices[i+4][2] * cell_size/2)
            glVertex3f(vertices[(i+1)%4+4][0] * cell_size/2, vertices[(i+1)%4+4][1] * cell_size/2, vertices[(i+1)%4+4][2] * cell_size/2)
            glVertex3f(vertices[i][0] * cell_size/2, vertices[i][1] * cell_size/2, vertices[i][2] * cell_size/2)
            glVertex3f(vertices[i+4][0] * cell_size/2, vertices[i+4][1] * cell_size/2, vertices[i+4][2] * cell_size/2)
        glEnd()

    # テキストの描画（数字や爆弾）
    if text is not None:
        glColor3f(0, 0, 0)
        glRasterPos3f(-0.2, -0.2, cell_size/2 + 0.01)
        for c in str(text):
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(c))

    glPopMatrix()

# ボード全体の描画
def draw_board():
    for x in range(cube_size):
        for y in range(cube_size):
            for z in range(cube_size):
                if revealed[x][y][z]:
                    if grid[x][y][z] == 9:
                        color = (1, 0, 0)  # 爆弾は赤
                        text = "X"
                    else:
                        color = (0.8, 0.8, 0.8)  # 開いたセルは明るい灰色
                        text = grid[x][y][z] if grid[x][y][z] > 0 else None
                else:
                    color = (0.3, 0.3, 0.3) if not flags[x][y][z] else (1, 1, 0)
                    text = None
                draw_cell(x - cube_size/2, y - cube_size/2, z - cube_size/2, color, text=text)

# ゲーム初期化
place_mines()
set_mine_counts()

# カメラ設定
gluPerspective(45, (800/600), 0.1, 50.0)
glTranslatef(0.0, 0.0, -20)

# メインループ
running = True
rotation_x, rotation_y = 30, 0  # 初期回転角度
while running:
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    # 入力処理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                rotation_y += 5
            elif event.key == pygame.K_RIGHT:
                rotation_y -= 5
            elif event.key == pygame.K_UP:
                rotation_x += 5
            elif event.key == pygame.K_DOWN:
                rotation_x -= 5
        elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
            if event.button == 1:  # 左クリック
                mx, my = pygame.mouse.get_pos()
                cell = check_click(mx, my)
                if cell:
                    x, y, z = cell
                    reveal_cell(x, y, z)
            elif event.button == 3:  # 右クリック
                mx, my = pygame.mouse.get_pos()
                cell = check_click(mx, my)
                if cell:
                    x, y, z = cell
                    if not revealed[x][y][z]:
                        flags[x][y][z] = not flags[x][y][z]

    # 3D描画
    glPushMatrix()
    glRotatef(rotation_x, 1, 0, 0)
    glRotatef(rotation_y, 0, 1, 0)
    draw_board()
    glPopMatrix()

    pygame.display.flip()
    pygame.time.wait(10)

pygame.quit()
sys.exit()