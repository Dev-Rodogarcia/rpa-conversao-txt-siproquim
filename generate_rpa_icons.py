"""Gera a serie de icones numerados do RPA em paths relativos ao repositorio."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "rpa-icons"


def _resolver_base(caminho: str | None) -> Path:
    if caminho:
        candidato = Path(caminho).expanduser().resolve()
        if candidato.exists():
            return candidato
        raise FileNotFoundError(f"Imagem base nao encontrada: {candidato}")

    for relativo in ("public/icon.png", "public/app-icon.png", "public/logo.png"):
        candidato = ROOT / relativo
        if candidato.exists():
            return candidato

    raise FileNotFoundError(
        "Nenhuma imagem base encontrada. Informe --base com um PNG de origem."
    )


def _carregar_fonte(tamanho: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidatos = [
        "arialbd.ttf",
        str((ROOT / "public" / "fonts" / "Manrope-Variable.ttf").resolve()),
    ]
    for candidato in candidatos:
        try:
            return ImageFont.truetype(candidato, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def gerar_icones(base_image_path: Path, output_dir: Path, quantidade: int = 30) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Carregando imagem base: {base_image_path}")

    img_orig = Image.open(base_image_path).convert("RGB")
    width, height = img_orig.size
    pixels = img_orig.load()

    min_red = min(pixels[x, y][0] for y in range(height) for x in range(width))
    base_colors = [
        pixels[x, y]
        for y in range(height)
        for x in range(width)
        if pixels[x, y][0] <= min_red + 5
    ]
    if base_colors:
        base_color = (
            int(sum(c[0] for c in base_colors) / len(base_colors)),
            int(sum(c[1] for c in base_colors) / len(base_colors)),
            int(sum(c[2] for c in base_colors) / len(base_colors)),
        )
    else:
        base_color = (33, 71, 138)

    img_base = Image.new("RGBA", (width, height))
    base_pixels = img_base.load()
    denominator = float(max(1, 255 - base_color[0]))

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            alpha_val = (255.0 - float(r)) / denominator
            alpha_val = max(0.0, min(1.0, alpha_val))
            base_pixels[x, y] = (
                base_color[0],
                base_color[1],
                base_color[2],
                int(alpha_val * 255),
            )

    alpha_mask = img_base.split()[-1]
    mask_dilated = alpha_mask.filter(ImageFilter.MaxFilter(3))
    mask_blurred = mask_dilated.filter(ImageFilter.GaussianBlur(1.5))
    shadow = Image.new("RGBA", img_base.size, (20, 20, 20, 255))
    shadow.putalpha(mask_blurred)
    final_base = Image.alpha_composite(shadow, img_base)

    for indice in range(1, quantidade + 1):
        imagem = final_base.copy()
        badge_radius = int(min(width, height) * 0.12)
        center_x = width - badge_radius - int(width * 0.08)
        center_y = height - badge_radius - int(height * 0.08)

        draw = ImageDraw.Draw(imagem)
        outline_radius = int(badge_radius * 1.08)
        draw.ellipse(
            [
                (center_x - outline_radius, center_y - outline_radius),
                (center_x + outline_radius, center_y + outline_radius),
            ],
            fill=(20, 20, 20, 255),
        )
        draw.ellipse(
            [
                (center_x - badge_radius, center_y - badge_radius),
                (center_x + badge_radius, center_y + badge_radius),
            ],
            fill=(255, 59, 48, 255),
        )

        texto = str(indice)
        fonte = _carregar_fonte(int(badge_radius * 1.3))
        try:
            draw.text((center_x, center_y), texto, fill="white", font=fonte, anchor="mm")
        except Exception:
            bbox = draw.textbbox((0, 0), texto, font=fonte)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text(
                (center_x - text_w / 2, center_y - text_h / 2 - text_h * 0.1),
                texto,
                fill="white",
                font=fonte,
            )

        destino = output_dir / f"rpa_icon_{indice}.png"
        imagem.save(destino, "PNG")

    print(f"{quantidade} icones gerados em {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="Caminho do PNG base usado na geracao.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()

    base = _resolver_base(args.base)
    output_dir = Path(args.output_dir).expanduser().resolve()
    gerar_icones(base, output_dir, max(1, args.count))


if __name__ == "__main__":
    main()
