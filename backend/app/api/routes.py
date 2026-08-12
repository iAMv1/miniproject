"""MindPulse Backend — API Routes."""

from __future__ import annotations
import time
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from app.core.auth import get_current_user
from app.schemas.stress import (
    InferenceRequest,
    InferenceResponse,
    HistoryPoint,
    FeedbackRequest,
    CalibrationStatus,
    HealthResponse,
    InterventionActionRequest,
    InterventionEvent,
)
from app.services.inference import engine
from app.services.websocket_manager import manager
from app.services import history
from app.services.interventions import intervention_engine
from app.core.config import (
    CALIBRATION_TARGET_SAMPLES_PER_HOUR,
    CALIBRATION_MIN_HOURS_COVERED,
    WS_HEARTBEAT_TIMEOUT_SEC,
)
from app.core.ratelimit import SlidingWindowLimiter, rate_limit

router = APIRouter()

_inference_limiter = SlidingWindowLimiter(max_requests=120, window_seconds=60)
_mutation_limiter = SlidingWindowLimiter(max_requests=30, window_seconds=60)


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model_loaded=engine.is_ready,
        version="1.0.0",
        active_connections=manager.count,
    )


@router.post("/inference", response_model=InferenceResponse)
async def run_inference(
    req: InferenceRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(rate_limit(_inference_limiter)),
):
    user_id = current_user["id"]
    features_raw = req.features.model_dump()
    result = engine.predict(features_raw, user_id)
    intervention_state = intervention_engine.evaluate(user_id, result)
    result.update(
        {
            "alert_state": intervention_state["alert_state"],
            "intervention": intervention_state["intervention"],
            "trend": intervention_state["trend"],
            "recovery_score": intervention_state["recovery_score"],
        }
    )
    history.append(user_id, result)
    if intervention_state["new_alert_triggered"] and intervention_state["intervention"]:
        history.append_intervention_event(
            user_id=user_id,
            action="recommended",
            intervention_type=intervention_state["intervention"]["intervention_type"],
            alert_state=intervention_state["alert_state"],
            score_before=float(result.get("score", 0.0)),
            notes="auto-generated recommendation",
        )
    await manager.broadcast({"type": "stress_update", **result, "user_id": user_id})
    return InferenceResponse(**result)


@router.get("/history", response_model=list[HistoryPoint])
async def get_history(
    current_user: dict = Depends(get_current_user), hours: int = 24
):
    user_id = current_user["id"]
    return history.get_history(user_id, hours)


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    return history.get_stats(user_id)


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(rate_limit(_mutation_limiter)),
):
    user_id = current_user["id"]
    # Persist feedback to SQLite via PersonalBaseline
    baseline = engine._get_baseline(user_id)
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


@router.get("/interventions/recommendation")
async def get_recommendation(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    latest = history.latest_point(user_id)
    eval_result = intervention_engine.evaluate(
        user_id,
        {
            "score": latest["score"],
            "level": latest["level"],
            "confidence": latest["confidence"],
            "insights": [],
            "feature_contributions": {},
        },
    )
    snapshot = intervention_engine.active_snapshot(user_id)
    return {
        "alert_state": eval_result["alert_state"],
        "trend": eval_result["trend"],
        "recovery_score": eval_result["recovery_score"],
        "intervention": eval_result["intervention"]
        or snapshot.get("last_recommendation"),
        "active_intervention": snapshot.get("active_intervention"),
        "active_start_score": snapshot.get("active_start_score"),
    }


@router.post("/interventions/action")
async def intervention_action(
    req: InterventionActionRequest, current_user: dict = Depends(get_current_user)
):
    return intervention_engine.apply_action(
        user_id=current_user["id"],
        action=req.action,
        intervention_type=req.intervention_type or "",
        notes=req.notes or "",
    )


@router.get("/interventions/history", response_model=list[InterventionEvent])
async def intervention_history(
    current_user: dict = Depends(get_current_user), hours: int = 168
):
    user_id = current_user["id"]
    events = history.get_intervention_events(user_id, hours)
    return [InterventionEvent(**event) for event in events]


@router.get("/interventions/wind-down")
async def check_wind_down(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    latest = history.latest_point(user_id)
    wind_down = intervention_engine.detect_wind_down(user_id, latest)
    return {"wind_down": wind_down}


@router.post("/interventions/schedule-break")
async def schedule_break(
    current_user: dict = Depends(get_current_user),
    break_time: str = Query(...),
    intervention_type: str = Query("breathing_reset"),
):
    user_id = current_user["id"]
    return intervention_engine.schedule_break(user_id, break_time, intervention_type)


@router.get("/interventions/scheduled-breaks")
async def get_scheduled_breaks(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    return {"breaks": intervention_engine.get_scheduled_breaks(user_id)}


@router.post("/interventions/cancel-break")
async def cancel_break(
    current_user: dict = Depends(get_current_user),
    break_id: str = Query(...),
):
    user_id = current_user["id"]
    return intervention_engine.cancel_break(user_id, break_id)


@router.get("/interventions/check-due-breaks")
async def check_due_breaks(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    due = intervention_engine.check_due_breaks(user_id)
    return {"due_break": due}


@router.get("/calibration", response_model=CalibrationStatus)
async def get_calibration(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    baseline = engine._get_baseline(user_id)
    if baseline:
        status = baseline.get_calibration_status(
            target_samples_per_hour=CALIBRATION_TARGET_SAMPLES_PER_HOUR,
            min_hours_covered=CALIBRATION_MIN_HOURS_COVERED,
        )
    else:
        status = {
            "is_calibrated": False,
            "days_collected": 0,
            "samples_per_hour": {},
            "completion_pct": 0.0,
            "calibration_quality": 0.0,
        }
    return CalibrationStatus(
        user_id=user_id,
        is_calibrated=status["is_calibrated"],
        days_collected=status["days_collected"],
        samples_per_hour=status["samples_per_hour"],
        completion_pct=status["completion_pct"],
        calibration_quality=status["calibration_quality"],
    )


@router.post("/reset")
async def reset_session(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(rate_limit(_mutation_limiter)),
):
    """Clear all in-memory session data for a fresh start."""
    user_id = current_user["id"]
    history.reset(user_id)
    baseline = engine._get_baseline(user_id)
    if baseline:
        baseline.reset()
    await manager.broadcast({"type": "session_reset", "user_id": user_id})
    return {"status": "ok", "message": f"Session data cleared for {user_id}"}


@router.get("/model-metrics")
async def model_metrics(current_user: dict = Depends(get_current_user)):
    """Return model accuracy, F1, precision, recall and confusion matrix."""
    import json
    import os
    import numpy as np

    manifest_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "ml",
        "artifacts",
        "artifacts_manifest.json",
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
        from app.ml.synthetic_data import (
            generate_synthetic_dataset,
            compute_global_stats,
        )
        from app.ml.model import DualNormalizer, load_model
        from app.ml.feature_extractor import FEATURE_NAMES
        from sklearn.metrics import confusion_matrix as cm_func

        model, stats = load_model(allow_download=False, allow_train_fallback=False)
        n_in = int(getattr(model, "n_features_in_", 23))

        X_raw, y_true, _ = generate_synthetic_dataset(n_samples=600)
        # shape-aware: raw-23 model takes raw features; 46-dim model takes
        # DualNormalizer output (global + user z-scores)
        if n_in == 23:
            X_pred = np.asarray(X_raw, dtype=np.float32)
        else:
            from app.ml.model import DualNormalizer
            normalizer = DualNormalizer(stats)
            hour_idx = FEATURE_NAMES.index("hour_of_day")
            X_pred = np.array(
                [
                    normalizer.transform(
                        X_raw[i], hour=int(X_raw[i, hour_idx]), baseline=None
                    )
                    for i in range(len(X_raw))
                ],
                dtype=np.float32,
            )

        y_pred = model.predict(X_pred)
        if np.ndim(y_pred) == 2:
            y_pred = y_pred.argmax(axis=1)
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
        "benchmark_type": "synthetic_smoke_test",
        "training_source": metrics.get("training_source", "unknown"),
        "split_method": metrics.get("split_method", "unknown"),
        "note": (
            "Confusion matrix is generated on 600 fresh SYNTHETIC samples. "
            "It is a smoke test of pipeline integrity, not a real-world benchmark. "
            "See manifest for the stored training metrics."
        ),
    }


@router.websocket("/ws/stress")
async def websocket_stress(ws: WebSocket, token: str = Query(default="")):
    from app.core.auth import decode_access_token

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await ws.close(code=4401, reason="Unauthorized")
        return
    uid = str(payload["sub"])
    await manager.connect(ws)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    ws.receive_text(), timeout=WS_HEARTBEAT_TIMEOUT_SEC
                )
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping", "timestamp": time.time()})
                continue
            # Client can send feature vectors for real-time prediction
            import json

            try:
                payload = json.loads(data)
                if payload.get("type") == "pong":
                    continue
                if payload.get("type") == "features":
                    from app.schemas.stress import FeatureVector

                    fv = FeatureVector(**payload["features"])
                    result = engine.predict(fv.model_dump(), uid)
                    intervention_state = intervention_engine.evaluate(uid, result)
                    result.update(
                        {
                            "alert_state": intervention_state["alert_state"],
                            "intervention": intervention_state["intervention"],
                            "trend": intervention_state["trend"],
                            "recovery_score": intervention_state["recovery_score"],
                        }
                    )
                    history.append(uid, result)
                    if (
                        intervention_state["new_alert_triggered"]
                        and intervention_state["intervention"]
                    ):
                        history.append_intervention_event(
                            user_id=uid,
                            action="recommended",
                            intervention_type=intervention_state["intervention"][
                                "intervention_type"
                            ],
                            alert_state=intervention_state["alert_state"],
                            score_before=float(result.get("score", 0.0)),
                            notes="auto-generated recommendation",
                        )
                    await ws.send_json(
                        {"type": "stress_update", **result, "user_id": uid}
                    )
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ─── SSE Inference Endpoint (Alternative to WebSocket) ───

from fastapi.responses import StreamingResponse
from datetime import datetime
import json as json_mod

@router.get("/inference/stream")
async def inference_sse_stream(
    token: str = Query(default=""),
    duration_minutes: int = Query(default=30, ge=1, le=120)
):
    """SSE stream of stress inference updates.

    Alternative to WebSocket for clients that prefer SSE.
    Streams stress scores every 5 seconds for specified duration.
    Authenticated via ?token=<JWT>.
    """
    from app.core.auth import decode_access_token
    from app.services.history import get_recent_history

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_id = str(payload["sub"])

    async def event_generator():
        max_iterations = duration_minutes * 12  # 5-second intervals
        
        for i in range(max_iterations):
            # Get recent data
            recent = get_recent_history(user_id, minutes=5)
            
            if recent and engine.is_ready:
                latest = recent[-1]
                features = {
                    "hold_time_mean": latest.get("hold_time_mean", 0.2),
                    "flight_time_mean": latest.get("flight_time_mean", 0.15),
                    "typing_speed_wpm": latest.get("typing_speed_wpm", 60),
                    "error_rate": latest.get("error_rate", 0.05),
                    "mouse_speed_mean": latest.get("mouse_speed_mean", 200),
                }
                
                result = engine.predict(features, user_id=user_id)
                
                event_data = {
                    "type": "stress_update",
                    "timestamp": datetime.now().isoformat(),
                    "score": result.get("score", 50),
                    "level": result.get("level", "NEUTRAL"),
                    "confidence": result.get("confidence", 0.0),
                    "features": {
                        "typing_speed_wpm": features["typing_speed_wpm"],
                        "error_rate": features["error_rate"],
                    }
                }
            else:
                event_data = {
                    "type": "stress_update",
                    "timestamp": datetime.now().isoformat(),
                    "score": 50,
                    "level": "NEUTRAL",
                    "confidence": 0.0 if not recent else 0.5,
                    "status": "collecting_data" if not recent else "engine_initializing"
                }
            
            yield f"data: {json_mod.dumps(event_data)}\n\n"
            
            # Heartbeat
            if i % 6 == 0 and i > 0:
                yield f"data: {json_mod.dumps({'type': 'heartbeat'})}\n\n"
            
            await asyncio.sleep(5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
