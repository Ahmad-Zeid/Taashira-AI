"""Generate synthetic document images for testing and the demo.

SYNTHETIC ONLY. These are fabricated images with invented numbers, produced so the
multimodal extractor has something to read without any real identity document ever
existing in this repository or appearing on camera.

Deliberately imperfect: dates are printed DD/MM/YYYY, the layout is cramped, and the
travel document does not say "passport" anywhere — which is exactly what the extractor
has to cope with.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "data" / "synthetic"


def _font(size: int):
    for path in (
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def travel_document() -> Image.Image:
    """A refugee travel document. Note: one-year validity, and never the word 'passport'."""
    img = Image.new("RGB", (1000, 640), "#e8e4d9")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 999, 92], fill="#1d3a5f")
    d.text((28, 22), "RÉPUBLIQUE LIBANAISE  ·  SÛRETÉ GÉNÉRALE", font=_font(26), fill="#f2f0e8")
    d.text(
        (28, 56),
        "DOCUMENT DE VOYAGE POUR RÉFUGIÉS PALESTINIENS",
        font=_font(19),
        fill="#c9d6e8",
    )

    rows = [
        ("N° / No.", "RD 4 8 2 1 9 2"),
        ("NOM / Surname", "SPECIMEN"),
        ("PRÉNOM / Given name", "SYNTHETIC"),
        ("DATE DE NAISSANCE", "14/02/2001"),
        ("LIEU / Place", "BEYROUTH"),
        ("DÉLIVRÉ LE / Issued", "01/03/2026"),
        ("EXPIRE LE / Expiry", "01/03/2027"),
        ("AUTORITÉ / Authority", "SÛRETÉ GÉNÉRALE - BEYROUTH"),
    ]
    y = 130
    for label, value in rows:
        d.text((40, y), label, font=_font(17), fill="#5a5a52")
        d.text((330, y - 3), value, font=_font(25), fill="#111111")
        y += 56

    d.rectangle([700, 130, 950, 430], outline="#8a8a80", width=2)
    d.text((762, 265), "PHOTO", font=_font(24), fill="#9a9a90")
    d.text((40, 592), "SPECIMEN — NOT A REAL DOCUMENT", font=_font(18), fill="#a03028")
    return img


def civil_extract() -> Image.Image:
    """An Individual Civil Extract, issued long enough ago to be stale."""
    img = Image.new("RGB", (1000, 560), "#f4f2ec")
    d = ImageDraw.Draw(img)
    d.text((40, 34), "REPUBLIC OF LEBANON", font=_font(28), fill="#1d3a5f")
    d.text((40, 74), "INDIVIDUAL CIVIL EXTRACT", font=_font(22), fill="#333333")
    d.line([40, 112, 960, 112], fill="#9a9a90", width=2)

    rows = [
        ("Register no.", "1974 / 221"),
        ("Full name", "SYNTHETIC SPECIMEN"),
        ("Date of birth", "14/02/2001"),
        ("Place of registration", "BEIRUT"),
        ("Date of issue", "15/06/2023"),
        ("Issuing office", "GENERAL SECURITY - BEIRUT"),
    ]
    y = 146
    for label, value in rows:
        d.text((44, y), label, font=_font(18), fill="#5a5a52")
        d.text((360, y - 3), value, font=_font(24), fill="#111111")
        y += 58

    d.text((40, 510), "SPECIMEN — NOT A REAL DOCUMENT", font=_font(18), fill="#a03028")
    return img


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, builder in (("travel_document", travel_document), ("civil_extract", civil_extract)):
        path = OUT / f"{name}.png"
        builder().save(path)
        print(f"wrote {path.relative_to(OUT.parent.parent)}")
