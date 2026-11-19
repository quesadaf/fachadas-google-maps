from pathlib import Path
import argparse
from ultralytics import YOLOE

PROMPTS_DEFAULT = [
    "storefront",
    "shop facade",
    "commercial sign",
    "shop window",
    "retail store entrance",
]


def main():
    parser = argparse.ArgumentParser(
        description="Detección zero-shot sobre imágenes propias/autorizadas"
    )
    parser.add_argument("source", help="Imagen, carpeta o video de entrada")
    parser.add_argument("--model", default="yoloe-26s-seg.pt")
    parser.add_argument("--conf", type=float, default=0.20)
    parser.add_argument("--prompts", nargs="+", default=PROMPTS_DEFAULT)
    parser.add_argument("--out", default="data/output/zero_shot")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    model = YOLOE(args.model)
    model.set_classes(args.prompts)
    results = model.predict(
        source=args.source,
        conf=args.conf,
        save=True,
        project=str(out.parent),
        name=out.name,
        exist_ok=True,
        verbose=True,
    )

    total = sum(len(r.boxes) if r.boxes is not None else 0 for r in results)
    print(f"Detecciones totales: {total}")
    print(f"Resultados guardados en: {out}")


if __name__ == "__main__":
    main()
