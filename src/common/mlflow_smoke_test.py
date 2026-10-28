"""Logs a dummy run to prove MLflow is set up."""
import mlflow
from naming import run_name

mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("road-intelligence-vision")

with mlflow.start_run(run_name=run_name("test", "dummy")):
    mlflow.log_params({"imgsz": 640, "epochs": 1, "seed": 42})
    mlflow.log_metric("mAP50", 0.0)
    print("Logged a test run.")
