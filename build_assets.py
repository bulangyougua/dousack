# -*- coding: utf-8 -*-
"""生成项目视觉资源：AI 主视觉展示图 + 代码绘制的多尺寸 exe 图标。

用法： python build_assets.py
依赖： Pillow（仅构建时需要，运行时不需要）
"""
import glob
import os
import shutil
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
os.makedirs(ASSETS, exist_ok=True)

WHITE = (255, 255, 255)
NAVY = (14, 18, 42)
PINK = (254, 44, 85)
BLUE = (28, 64, 190)
CYAN = (37, 244, 238)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_tile(size):
    """双线性四角渐变：左上深蓝 / 右上粉红 / 左下宝蓝 / 右下青。"""
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        ty = y / (size - 1)
        for x in range(size):
            tx = x / (size - 1)
            top = lerp(NAVY, PINK, tx)
            bottom = lerp(BLUE, CYAN, tx)
            px[x, y] = lerp(top, bottom, ty)
    return img


def draw_icon(size=512):
    s = float(size)
    img = gradient_tile(size).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 圆角外框（四角透明）
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=int(s * 0.22), fill=255
    )
    img.putalpha(mask)
    d = ImageDraw.Draw(img)

    # 下载箭头：柄 + 三角
    d.rounded_rectangle(
        (0.425 * s, 0.22 * s, 0.575 * s, 0.53 * s),
        radius=0.028 * s, fill=WHITE,
    )
    d.polygon(
        [(0.28 * s, 0.475 * s), (0.72 * s, 0.475 * s), (0.50 * s, 0.79 * s)],
        fill=WHITE,
    )

    # 镜头圆环，呼应主视觉
    d.ellipse((0.355 * s, 0.355 * s, 0.645 * s, 0.645 * s), fill=WHITE)
    d.ellipse((0.405 * s, 0.405 * s, 0.595 * s, 0.595 * s), fill=(20, 26, 60))
    d.ellipse((0.455 * s, 0.455 * s, 0.545 * s, 0.545 * s), fill=WHITE)
    d.ellipse((0.482 * s, 0.482 * s, 0.518 * s, 0.518 * s), fill=(20, 26, 60))

    # 左下播放三角
    d.polygon(
        [(0.255 * s, 0.625 * s), (0.255 * s, 0.735 * s), (0.355 * s, 0.68 * s)],
        fill=WHITE,
    )

    # 右下四角星芒
    cx, cy, r = 0.705 * s, 0.68 * s, 0.055 * s
    d.polygon(
        [(cx, cy - r), (cx + r * 0.28, cy - r * 0.28), (cx + r, cy),
         (cx + r * 0.28, cy + r * 0.28), (cx, cy + r),
         (cx - r * 0.28, cy + r * 0.28), (cx - r, cy),
         (cx - r * 0.28, cy - r * 0.28)],
        fill=WHITE,
    )
    return img


def main():
    # 1) AI 主视觉 -> 规范文件名 + 界面用缩略图
    ai = sorted(glob.glob(os.path.join(ASSETS, "Modern_flat_vector_app_icon_*.png")))
    artwork = os.path.join(ASSETS, "app_artwork.png")
    if ai:
        if not os.path.exists(artwork):
            shutil.copyfile(ai[0], artwork)
        print("主视觉:", artwork)
    if os.path.exists(artwork):
        Image.open(artwork).convert("RGB").resize((256, 256), Image.LANCZOS).save(
            os.path.join(ASSETS, "app_logo.png")
        )
        print("界面图:", os.path.join(ASSETS, "app_logo.png"))

    # 2) 矢量 exe 图标
    icon = draw_icon(512)
    icon.save(os.path.join(ASSETS, "app_icon.png"))
    icon.save(
        os.path.join(ASSETS, "app_icon.ico"),
        format="ICO",
        sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40),
               (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("exe 图标:", os.path.join(ASSETS, "app_icon.ico"))


if __name__ == "__main__":
    main()
