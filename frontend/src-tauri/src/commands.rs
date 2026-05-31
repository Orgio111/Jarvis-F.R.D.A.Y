use tauri::{AppHandle, Manager, WebviewWindow, command};

#[command]
pub fn show_window(app: AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.show();
        let _ = win.set_focus();
    }
}

#[command]
pub fn hide_window(app: AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.hide();
    }
}

#[command]
pub fn open_quick_chat(app: AppHandle) {
    crate::tray::open_or_create_quick_chat_pub(&app);
}

#[command]
pub async fn get_jarvis_status() -> serde_json::Value {
    // Query the Go gateway health endpoint
    match reqwest::get("http://localhost:8000/health").await {
        Ok(resp) => {
            if let Ok(json) = resp.json::<serde_json::Value>().await {
                return json;
            }
        }
        Err(_) => {}
    }
    serde_json::json!({ "ok": false, "status": "unreachable" })
}
