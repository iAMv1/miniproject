"""MindPulse Backend — API Routes."""

from __future__ import annotations
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.schemas.stress import (
    InferenceRequest,
    InferenceResponse,
    HistoryPoint,
    FeedbackRequest,
    CalibrationStatus,
    HealthResponse,
)
from app.services.inference import engine
from app.services.websocket_manager import manager
from app.services import history

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model_loaded=engine.is_ready,
        version="1.0.0",
        active_connections=manager.count,
    )


@router.post("/inference", response_model=InferenceResponse)
async def run_inference(req: InferenceRequest):
    features_raw = req.features.model_dump()
    result = engine.predict(features_raw, req.user_id)
    history.append(req.user_id, result)
    await manager.broadcast({"type": "stress_update", **result, "user_id": req.user_id})
    return InferenceResponse(**result)


@router.get("/history", response_model=list[HistoryPoint])
async def get_history(user_id: str = "default", hours: int = 24):
    return history.get_history(user_id, hours)


@router.get("/stats")
async def get_stats(user_id: str = "default"):
    return history.get_stats(user_id)


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    # Persist feedback to SQLite via PersonalBaseline
    baseline = engine._get_baseline(req.user_id)
    if baseline:
        baseline.save_feedback(
            timestamp_ms=req.timestamp,
            model_label=req.predicted_level,
            user_feedback=req.actual_level,
            score=0.0,
        )
    return {
        "status": "ok",
        "message": f"Feedback saved: predicted {req.predicted_level}, actual {req.actual_level}",
    }


@router.get("/calibration/{user_id}", response_model=CalibrationStatus)
async def get_calibration(user_id: str):
    return CalibrationStatus(
        user_id=user_id,
        is_calibrated=False,
        days_collected=0,
        samples_per_hour={},
        completion_pct=0.0,
    )


@router.post("/reset")
async def reset_session(user_id: str = "demo_user"):
    """Clear all in-memory session data for a fresh start."""
    history.reset(user_id)
    await manager.broadcast({"type": "session_reset", "user_id": user_id})
    return {"status": "ok", "message": f"Session data cleared for {user_id}"}


@router.get("/model-metrics")
async def model_metrics():
    """Return model accuracy, F1, precision, recall and confusion matrix."""
    import json
    import os
    import numpy as np

    manifest_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "ml", "artifacts", "artifacts_manifest.json"
    )
    manifest_path = os.path.normpath(manifest_path)

    # Load stored validation metrics
    metrics = {"accuracy": 0, "precision_macro": 0, "recall_macro": 0, "f1_macro": 0}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        metrics = manifest.get("metrics_validation", metrics)

    # Generate a fresh confusion matrix from the loaded model
    confusion_matrix = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    try:
        from app.ml.synthetic_data import generate_synthetic_dataset, compute_global_stats
        from app.ml.model import DualNormalizer, load_model
        from app.ml.feature_extractor import FEATURE_NAMES
        from sklearn.metrics import confusion_matrix as cm_func

        model, stats = load_model(allow_download=False, allow_train_fallback=False)
        normalizer = DualNormalizer(stats)
        hour_idx = FEATURE_NAMES.index("hour_of_day")

        X_raw, y_true, _ = generate_synthetic_dataset(n_samples=600)
        X_norm = np.array([
            normalizer.transform(X_raw[i], hour=int(X_raw[i, hour_idx]), baseline=None)
            for i in range(len(X_raw))
        ], dtype=np.float32)

        y_pred = model.predict(X_norm)
        matrix = cm_func(y_true, y_pred, labels=[0, 1, 2])
        confusion_matrix = matrix.tolist()
    except Exception as e:
        print(f"[WARN] Could not compute confusion matrix: {e}")

    return {
        "accuracy": round(metrics.get("accuracy", 0) * 100, 1),
        "precision": round(metrics.get("precision_macro", 0) * 100, 1),
        "recall": round(metrics.get("recall_macro", 0) * 100, 1),
        "f1": round(metrics.get("f1_macro", 0) * 100, 1),
        "confusion_matrix": confusion_matrix,
        "labels": ["NEUTRAL", "MILD", "STRESSED"],
    }


@router.websocket("/ws/stress")
async def websocket_stress(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Client can send feature vectors for real-time prediction
            import json

            try:
                payload = json.loads(data)
                if payload.get("type") == "features":
                    from app.schemas.stress import FeatureVector

                    fv = FeatureVector(**payload["features"])
                    result = engine.predict(
                        fv.model_dump(), payload.get("user_id", "default")
                    )
                    uid = payload.get("user_id", "default")
                    history.append(uid, result)
                    await ws.send_json({"type": "stress_update", **result})
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws)
