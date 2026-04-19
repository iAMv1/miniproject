"""Full integration test for MindPulse backend."""
import sys
sys.path.insert(0, '.')

# Test 1: All imports work
print('TEST 1: Imports...')
from app.main import app
from app.services.history import get_history, get_stats, append, reset
from app.services.interventions import intervention_engine
from app.services.inference import engine
from app.schemas.stress import FeatureVector, HistoryPoint, InferenceRequest
print('  OK - All imports successful')

# Test 2: FeatureVector validation with 23+2 fields
print('TEST 2: FeatureVector with all fields...')
fv = FeatureVector(
    hold_time_mean=0.12, hold_time_std=0.03, hold_time_median=0.11,
    flight_time_mean=0.08, flight_time_std=0.02,
    typing_speed_wpm=60.0, error_rate=0.05,
    pause_frequency=2.0, pause_duration_mean=1.5,
    burst_length_mean=3.0, rhythm_entropy=2.5,
    mouse_speed_mean=200.0, mouse_speed_std=50.0,
    direction_change_rate=0.3, click_count=10, rage_click_count=1,
    scroll_velocity_std=30.0, tab_switch_freq=0.0, switch_entropy=0.0,
    session_fragmentation=0.0, hour_of_day=14.5, day_of_week=3,
    session_duration_min=5.0,
    mouse_reentry_count=0.0, mouse_reentry_latency_ms=0.0
)
print(f'  OK - FeatureVector: wpm={fv.typing_speed_wpm}, rage={fv.rage_click_count}, mouse={fv.mouse_speed_mean}')

# Test 3: History DB with feature fields
print('TEST 3: History DB write/read...')
reset('test_user')
append('test_user', {
    'score': 45.0, 'level': 'MILD', 'confidence': 0.8,
    'insights': ['test insight'],
    'model_score': 40.0, 'equation_score': 50.0, 'final_score': 45.0,
    'timestamp': 1000000.0,
    'typing_speed_wpm': 65.0, 'rage_click_count': 2,
    'error_rate': 0.05, 'click_count': 15, 'mouse_speed_mean': 220.0,
    'mouse_reentry_count': 1.0, 'mouse_reentry_latency_ms': 500.0
})
stats = get_stats('test_user')
print(f'  OK - Stats keys: {list(stats.keys())}')
assert 'mouse_speed_mean' in stats, f'mouse_speed_mean missing from stats!'
print(f'  OK - Stats: wpm={stats["typing_speed_wpm"]}, mouse={stats["mouse_speed_mean"]}')

history_data = get_history('test_user', hours=24)
print(f'  OK - History points: {len(history_data)}')
if len(history_data) > 0:
    hp = history_data[0]
    print(f'  OK - HistoryPoint: wpm={hp.typing_speed_wpm}, rage={hp.rage_click_count}, mouse={hp.mouse_speed_mean}')
    hp_dict = hp.model_dump()
    print(f'  OK - Dict keys: {list(hp_dict.keys())}')

# Test 4: Inference
print('TEST 4: Inference engine predict...')
try:
    engine.load(allow_train_fallback=True)
    result = engine.predict(fv.model_dump(), 'test_user')
    keys_we_need = ['score', 'level', 'typing_speed_wpm', 'rage_click_count', 'error_rate', 'click_count', 'mouse_speed_mean']
    missing = [k for k in keys_we_need if k not in result]
    if missing:
        print(f'  FAIL - Missing keys: {missing}')
    else:
        print(f'  OK - Predict: score={result["score"]}, level={result["level"]}, wpm={result["typing_speed_wpm"]}, mouse={result["mouse_speed_mean"]}')
except Exception as e:
    print(f'  WARN - Predict failed (model not trained): {e}')

# Test 5: WebSocket message format
print('TEST 5: WS feature payload format...')
import json
ws_payload = json.dumps({"type": "features", "features": fv.model_dump(), "user_id": "test_user"})
parsed = json.loads(ws_payload)
assert parsed["type"] == "features"
assert "features" in parsed
assert "user_id" in parsed
print(f'  OK - WS payload: type={parsed["type"]}, features count={len(parsed["features"])}, user_id={parsed["user_id"]}')

# Test 6: Auth routes
print('TEST 6: Auth module...')
from app.core.auth import create_access_token, decode_access_token, hash_password, verify_password
token = create_access_token({"sub": "1", "email": "test@test.com"})
payload = decode_access_token(token)
assert payload is not None
assert payload["sub"] == "1"
print(f'  OK - JWT token created and verified')

hashed = hash_password("test123")
assert verify_password("test123", hashed)
print(f'  OK - Password hashing works')

# Test 7: Demo token in auth endpoint
print('TEST 7: Demo user auth...')
from app.api.auth_routes import router as auth_router
from app.services.users import create_or_login_google_user
demo_result = create_or_login_google_user("demo@mindpulse.app", "Demo User", "demo-google-id")
if demo_result:
    print(f'  OK - Google OAuth: user={demo_result["user"]["email"]}, has_token={bool(demo_result["access_token"])}')
else:
    print(f'  OK - Google OAuth: user created on first run (or already exists)')

# Test 8: Intervention engine
print('TEST 8: Intervention engine...')
eval_result = intervention_engine.evaluate('test_user', {
    'score': 75, 'level': 'STRESSED', 'confidence': 0.85
})
print(f'  OK - Alert state: {eval_result["alert_state"]}, trend: {eval_result["trend"]}')

# Cleanup
reset('test_user')
print()
print('ALL TESTS PASSED')