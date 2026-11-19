from pathlib import Path
import argparse
import random
import shutil


def main():
    p = argparse.ArgumentParser(description="Divide imágenes/labels YOLO en train/val")
    p.add_argument("--images", required=True)
    p.add_argument("--labels", required=True)
    p.add_argument("--val", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()

    images = [
        x for x in Path(a.images).iterdir()
        if x.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    random.Random(a.seed).shuffle(images)
    nval = max(1, round(len(images) * a.val)) if images else 0
    val_names = {p.stem for p in images[:nval]}

    for split in ["train", "val"]:
        Path(f"data/dataset/images/{split}").mkdir(parents=True, exist_ok=True)
        Path(f"data/dataset/labels/{split}").mkdir(parents=True, exist_ok=True)

    for img in images:
        split = "val" if img.stem in val_names else "train"
        label = Path(a.labels) / f"{img.stem}.txt"
        if not label.exists():
            print(f"AVISO: sin etiqueta {img.name}; se omite")
            continue
        shutil.copy2(img, f"data/dataset/images/{split}/{img.name}")
        shutil.copy2(label, f"data/dataset/labels/{split}/{label.name}")

    print(f"Total: {len(images)} | val: {nval} | train: {max(0, len(images)-nval)}")


if __name__ == "__main__":
    main()
