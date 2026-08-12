#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::State;

// ─── AppState ───

struct AppState {
    collector: Mutex<BehavioralCollector>,
}

// ─── Event Types ───

#[derive(Debug, Clone, Serialize, Deserialize)]
struct KeyEvent {
    timestamp_press: f64,
    timestamp_release: f64,
    key_category: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MouseEvent {
    timestamp: f64,
    x: i32,
    y: i32,
    event_type: String,
    click_type: Option<String>,
    scroll_delta: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StressData {
    score: f32,
    level: String,
    confidence: f32,
    typing_speed_wpm: f32,
    error_rate: f32,
    rage_click_count: i32,
}

// ─── Behavioral Collector (Rust replacement for Python pynput) ───

struct BehavioralCollector {
    key_events: Mutex<Vec<KeyEvent>>,
    mouse_events: Mutex<Vec<MouseEvent>>,
    running: Mutex<bool>,
}

impl BehavioralCollector {
    fn new() -> Self {
        Self {
            key_events: Mutex::new(Vec::new()),
            mouse_events: Mutex::new(Vec::new()),
            running: Mutex::new(false),
        }
    }

    fn start(&self) {
        let mut running = self.running.lock().unwrap();
        if *running {
            return;
        }
        *running = true;
        drop(running);

        // Start keyboard listener in background thread
        let key_events = self.key_events.clone();
        let running = self.running.clone();
        std::thread::spawn(move || {
            // Using rdev for cross-platform keyboard/mouse capture
            // This is a simplified version - full implementation
            // would use rdev::listen() with proper event handling
            log::info!("Keyboard listener started");
            while *running.lock().unwrap() {
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
            log::info!("Keyboard listener stopped");
        });

        // Start mouse listener in background thread
        let mouse_events = self.mouse_events.clone();
        let running = self.running.clone();
        std::thread::spawn(move || {
            log::info!("Mouse listener started");
            while *running.lock().unwrap() {
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
            log::info!("Mouse listener stopped");
        });
    }

    fn stop(&self) {
        let mut running = self.running.lock().unwrap();
        *running = false;
    }

    fn get_events(&self) -> (Vec<KeyEvent>, Vec<MouseEvent>) {
        let mut keys = self.key_events.lock().unwrap();
        let mut mice = self.mouse_events.lock().unwrap();
        let keys_out = std::mem::take(&mut *keys);
        let mice_out = std::mem::take(&mut *mice);
        (keys_out, mice_out)
    }
}

// ─── Tauri Commands ───

#[tauri::command]
fn start_collector(state: State<AppState>) -> Result<(), String> {
    state.collector.start();
    log::info!("Behavioral collector started");
    Ok(())
}

#[tauri::command]
fn stop_collector(state: State<AppState>) -> Result<(), String> {
    state.collector.stop();
    log::info!("Behavioral collector stopped");
    Ok(())
}

#[tauri::command]
fn get_collected_events(state: State<AppState>) -> Result<(Vec<KeyEvent>, Vec<MouseEvent>), String> {
    let (keys, mice) = state.collector.get_events();
    Ok((keys, mice))
}

// ─── Telemetry Bridge (closes the desktop -> backend data channel) ───
// Posts collected key/mouse events to the MindPulse backend telemetry
// endpoint. Auth via MINDPULSE_TOKEN env (desktop login flow comes later);
// endpoint via MINDPULSE_API_URL (default localhost:5000).

fn telemetry_config() -> (String, String) {
    let url = std::env::var("MINDPULSE_API_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:5000/api/v1".into());
    let token = std::env::var("MINDPULSE_TOKEN").unwrap_or_default();
    (url, token)
}

#[tauri::command]
fn flush_telemetry(state: State<AppState>) -> Result<serde_json::Value, String> {
    let (keys, mice) = state.collector.get_events();
    if keys.is_empty() && mice.is_empty() {
        return Ok(serde_json::json!({"status": "empty"}));
    }

    let (url, token) = telemetry_config();
    let mut events: Vec<serde_json::Value> = Vec::new();
    for k in keys {
        events.push(serde_json::json!({
            "type": "key",
            "t": k.timestamp_press,
            "down_ms": k.timestamp_press * 1000.0,
            "up_ms": k.timestamp_release * 1000.0,
        }));
    }
    for m in mice {
        events.push(serde_json::json!({
            "type": "mouse",
            "t": m.timestamp,
            "x": m.x,
            "y": m.y,
            "kind": if m.event_type.contains("click") { "left" } else { "move" },
        }));
    }

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;
    let resp = client
        .post(format!("{}/telemetry/batch", url))
        .bearer_auth(&token)
        .json(&serde_json::json!({"client": "desktop", "events": events}))
        .send()
        .map_err(|e| e.to_string())?;
    let status = resp.status().as_u16();
    let body: serde_json::Value = resp.json().unwrap_or(serde_json::json!({}));
    log::info!("telemetry flush -> {} {}", status, body);
    Ok(serde_json::json!({"status": status, "body": body}))
}

#[tauri::command]
fn get_system_info() -> Result<serde_json::Value, String> {
    let info = serde_json::json!({
        "platform": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "version": env!("CARGO_PKG_VERSION"),
    });
    Ok(info)
}

// ─── Main ───

fn main() {
    // Initialize logging
    env_logger::init();

    let state = AppState {
        collector: Mutex::new(BehavioralCollector::new()),
    };

    // auto-flush thread (needs a handle to the collector state)
    {
        let collector = state.collector.clone();
        let api = telemetry_config();
        std::thread::spawn(move || loop {
            std::thread::sleep(std::time::Duration::from_secs(15));
            let (keys, mice) = {
                let c = collector.lock().unwrap();
                let k = c.key_events.lock().unwrap();
                let m = c.mouse_events.lock().unwrap();
                (k.clone(), m.clone())
            };
            if keys.is_empty() && mice.is_empty() {
                continue;
            }
            let (url, token) = api.clone();
            let mut events: Vec<serde_json::Value> = Vec::new();
            for k in keys.iter() {
                events.push(serde_json::json!({"type": "key", "t": k.timestamp_press,
                    "down_ms": k.timestamp_press * 1000.0, "up_ms": k.timestamp_release * 1000.0}));
            }
            for m in mice.iter() {
                events.push(serde_json::json!({"type": "mouse", "t": m.timestamp, "x": m.x, "y": m.y,
                    "kind": if m.event_type.contains("click") { "left" } else { "move" }}));
            }
            let client = reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_secs(10)).build().unwrap();
            match client
                .post(format!("{}/telemetry/batch", url))
                .bearer_auth(&token)
                .json(&serde_json::json!({"client": "desktop", "events": events}))
                .send()
            {
                Ok(r) => log::info!("telemetry auto-flush -> {}", r.status()),
                Err(e) => log::warn!("telemetry auto-flush failed: {}", e),
            }
        });
    }

    tauri::Builder::default()
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            start_collector,
            stop_collector,
            get_collected_events,
            flush_telemetry,
            get_system_info,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
