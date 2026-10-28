"""Run-naming helper so every MLflow run is named the same way."""


def run_name(model: str, dataset: str, seed: int = 42, imgsz: int = 640, tag: str = "") -> str:
    name = f"{model}_{dataset}_seed{seed}_img{imgsz}"
    return f"{name}_{tag}" if tag else name


if __name__ == "__main__":
    print(run_name("yolov8s", "rdd-india"))
