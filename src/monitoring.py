import os
import mlflow
import mlflow.system_metrics


def setup_mlflow():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("rennes_traffic_monitoring")

    mlflow.system_metrics.set_system_metrics_sampling_interval(1)
    mlflow.system_metrics.set_system_metrics_samples_before_logging(1)