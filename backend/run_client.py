import time
import json
import threading
import urllib.request
from app.ml.data_collector import BehavioralCollector
from app.ml.feature_extractor import extract_all_features, FEATURE_NAMES

# ─── Windows Native Toast Notification (PowerShell, no pip packages needed) ───
_last_notif_time = 0
NOTIF_COOLDOWN = 60  # Don't spam — wait 60s between notifications

def _send_stress_notification(score, level):
    """Fire a native Windows toast notification via PowerShell (non-blocking)."""
    global _last_notif_time
    now = time.time()
    if now - _last_notif_time < NOTIF_COOLDOWN:
        return  # Cooldown active
    _last_notif_time = now

    title = "MindPulse - Stress Alert"
    body = f"Stress score: {score}/100 ({level}). Take a deep breath and try a 5-min break."

    def _fire():
        try:
            import subprocess
            import tempfile
            import os

            # Write PS script to a temp file to avoid escaping issues
            lines = [
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null",
                "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null",
                f"$xmlStr = \"<toast><visual><binding template='ToastGeneric'><text>{title}</text><text>{body}</text></binding></visual></toast>\"",
                "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument",
                "$xml.LoadXml($xmlStr)",
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)",
                '[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("MindPulse").Show($toast)',
            ]
            ps_script = "\n".join(lines)

            tmp = os.path.join(tempfile.gettempdir(), "mindpulse_toast.ps1")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(ps_script)

            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", tmp],
                capture_output=True, timeout=10
            )
            print(f"[MindPulse] Windows notification sent! (Score: {score})")
        except Exception as e:
            print(f"[MindPulse] Notification failed: {e}")

    threading.Thread(target=_fire, daemon=True).start()


def run_client():

    collector = BehavioralCollector()
    collector.start()
    print("MindPulse Client: Started collecting behavioral data...")
    session_start = time.time() * 1000.0
    
    all_keys = []
    all_mice = []
    all_ctx = []
    
    try:
        while True:
            time.sleep(5)  # Update dashboard every 5 seconds
            k, m, c = collector.get_events()
            all_keys.extend(k)
            all_mice.extend(m)
            all_ctx.extend(c)
            
            # Keep only the last 60 seconds (rolling window) for fast UI updates
            now_ms = time.time() * 1000.0
            cutoff = now_ms - 60000
            
            all_keys = [e for e in all_keys if e.timestamp_press >= cutoff]
            all_mice = [e for e in all_mice if e.timestamp >= cutoff]
            all_ctx = [e for e in all_ctx if e.timestamp >= cutoff]
            
            # Send data to backend if there is any activity
            if len(all_keys) > 0 or len(all_mice) > 0:
                features_arr, _ = extract_all_features(
                    all_keys, all_mice, all_ctx,
                    window_start_time_ms=cutoff,
                    session_start_time_ms=session_start
                )
                
                # Convert np.float32 to python floats for JSON
                features_dict = {name: float(val) for name, val in zip(FEATURE_NAMES, features_arr)}
                
                payload = json.dumps({
                    "features": features_dict,
                    "user_id": "demo_user"
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    "http://localhost:5000/api/v1/inference",
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                try:
                    with urllib.request.urlopen(req) as response:
                        res_data = json.loads(response.read().decode('utf-8'))
                        level = res_data['level']
                        score = res_data['score']
                        print(f"Update: {level} | Score: {score} | WPM: {features_dict['typing_speed_wpm']:.1f}")

                        # Fire Windows notification when STRESSED or high MILD
                        if level == "STRESSED" or score >= 65:
                            _send_stress_notification(score, level)

                except Exception as e:
                    print(f"Failed to send to API: {e}")
            else:
                print("Idle... move mouse or type to see dashboard updates.")
                
    except KeyboardInterrupt:
        print("Stopping client...")
        collector.stop()

if __name__ == "__main__":
    run_client()
