use tauri::App;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

pub fn register_hotkeys(app: &mut App) -> tauri::Result<()> {
    // CmdOrCtrl+Shift+J → toggle main window
    app.global_shortcut().on_shortcut("CmdOrCtrl+Shift+J", |app, _shortcut, event| {
        if event.state() == ShortcutState::Pressed {
            if let Some(win) = app.get_webview_window("main") {
                if win.is_visible().unwrap_or(false) {
                    let _ = win.hide();
                } else {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }
        }
    })?;

    // CmdOrCtrl+Shift+Space → quick chat floating window
    app.global_shortcut().on_shortcut("CmdOrCtrl+Shift+Space", |app, _shortcut, event| {
        if event.state() == ShortcutState::Pressed {
            crate::tray::open_or_create_quick_chat_pub(app);
        }
    })?;

    Ok(())
}
