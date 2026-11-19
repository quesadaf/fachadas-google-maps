import argparse
from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser(description="Entrena detector personalizado de fachadas")
    p.add_argument("--data", default="configs/fachadas.yaml")
    p.add_argument("--model", default="yolo26n.pt")
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default=None)
    a = p.parse_args()

    model = YOLO(a.model)
    kwargs = {
        "data": a.data,
        "epochs": a.epochs,
        "imgsz": a.imgsz,
        "project": "runs",
        "name": "fachadas_comerciales",
    }
    if a.device is not None:
        kwargs["device"] = a.device
    model.train(**kwargs)


if __name__ == "__main__":
    main()
