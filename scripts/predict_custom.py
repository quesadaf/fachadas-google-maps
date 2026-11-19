import argparse
from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser(description="Inferencia con detector entrenado")
    p.add_argument("source")
    p.add_argument("--weights", default="runs/fachadas_comerciales/weights/best.pt")
    p.add_argument("--conf", type=float, default=0.25)
    a = p.parse_args()

    model = YOLO(a.weights)
    model.predict(
        source=a.source,
        conf=a.conf,
        save=True,
        project="data/output",
        name="custom",
        exist_ok=True,
    )
    print("Resultados en data/output/custom")


if __name__ == "__main__":
    main()
