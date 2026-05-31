use tauri::{
    App,
    Manager,
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
};

pub fn setup_tray(app: &mut App) -> tauri::Result<()> {
    let show_i   = MenuItem::with_id(app, "show",       "Open JARVIS",       true, None::<&str>)?;
    let chat_i   = MenuItem::with_id(app, "quick_chat", "Quick Chat",        true, Some("CmdOrCtrl+Shift+J"))?;
    let sep      = PredefinedMenuItem::separator(app)?;
    let status_i = MenuItem::with_id(app, "status",     "Status: Ready",     false, None::<&str>)?;
    let sep2     = PredefinedMenuItem::separator(app)?;
    let quit_i   = MenuItem::with_id(app, "quit",       "Quit JARVIS",       true, None::<&str>)?;

    let menu = Menu::with_items(app, &[
        &show_i,
        &chat_i,
        &sep,
        &status_i,
        &sep2,
        &quit_i,
    ])?;

    let _tray = TrayIconBuilder::new()
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }
            "quick_chat" => {
                open_or_create_quick_chat(app);
            }
            "quit" => {
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(win) = app.get_webview_window("main") {
                    if win.is_visible().unwrap_or(false) {
                        let _ = win.hide();
                    } else {
                        let _ = win.show();
                        let _ = win.set_focus();
                    }
                }
            }
        })
        .build(app)?;

    Ok(())
}

pub fn open_or_create_quick_chat_pub(app: &tauri::AppHandle) {
    open_or_create_quick_chat(app);
}

fn open_or_create_quick_chat(app: &tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("quick_chat") {
        let _ = win.show();
        let _ = win.set_focus();
        return;
    }

    let _ = tauri::WebviewWindowBuilder::new(
        app,
        "quick_chat",
        tauri::WebviewUrl::App("/chat".into()),
    )
    .title("JARVIS — Quick Chat")
    .inner_size(600.0, 480.0)
    .min_inner_size(480.0, 360.0)
    .resizable(true)
    .center()
    .always_on_top(true)
    .build();
}
