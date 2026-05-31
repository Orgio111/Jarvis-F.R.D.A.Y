// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod tray;
mod hotkeys;
mod commands;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            tray::setup_tray(app)?;
            hotkeys::register_hotkeys(app)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::show_window,
            commands::hide_window,
            commands::open_quick_chat,
            commands::get_jarvis_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running JARVIS application");
}
