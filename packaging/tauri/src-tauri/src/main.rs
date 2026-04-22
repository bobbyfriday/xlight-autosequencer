// Prevents additional console window on Windows (no-op on macOS; kept so the
// shell is portable if Windows is ever added back).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod handshake;

use std::sync::Mutex;

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_shell::process::{Command, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Cached backend port; written once the handshake line is parsed on the
/// sidecar's stdout, read by the frontend via `get_backend_port` and also
/// used for graceful shutdown.
struct BackendState {
    port: Mutex<Option<u16>>,
    // We intentionally do NOT retain a reference to `CommandChild` here;
    // Tauri's process handle is consumed by the stdout-reader task, and
    // shutdown is performed by sending SIGTERM to the pid we record when
    // the sidecar spawns.
    pid: Mutex<Option<u32>>,
}

impl BackendState {
    fn new() -> Self {
        Self {
            port: Mutex::new(None),
            pid: Mutex::new(None),
        }
    }
}

#[derive(Clone, Serialize)]
struct BackendReadyPayload {
    port: u16,
}

#[derive(Clone, Serialize)]
struct BackendStartupFailedPayload {
    message: String,
}

/// Frontend-callable command: return the cached port, or null if the
/// handshake hasn't completed yet. Exists so a frontend listener that
/// attaches after the event has already fired can still learn the port.
#[tauri::command]
fn get_backend_port(state: State<'_, BackendState>) -> Option<u16> {
    state.port.lock().ok().and_then(|g| *g)
}

/// Spawn the PyInstaller sidecar and wire up stdout parsing.
fn spawn_backend(app: &AppHandle) -> Result<(), String> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource_dir: {e}"))?;

    let vamp_path = resource_dir.join("vamp");
    let torch_home = dirs_home()
        .ok_or_else(|| "no home dir".to_string())?
        .join("Library")
        .join("Application Support")
        .join("XLight")
        .join("models")
        .join("torch-hub");
    std::fs::create_dir_all(torch_home.join("hub").join("checkpoints")).ok();

    let sidecar: Command = app
        .shell()
        .sidecar("backend")
        .map_err(|e| format!("sidecar lookup failed: {e}"))?
        .envs([
            ("XLIGHT_PACKAGED", "1".to_string()),
            ("PYTHONUNBUFFERED", "1".to_string()),
            ("VAMP_PATH", vamp_path.to_string_lossy().to_string()),
            ("TORCH_HOME", torch_home.to_string_lossy().to_string()),
            // Cap torch/openmp thread count so we don't spike CPU at startup.
            ("OMP_NUM_THREADS", "4".to_string()),
            ("MKL_NUM_THREADS", "4".to_string()),
        ]);

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|e| format!("failed to spawn backend: {e}"))?;

    let pid = child.pid();
    if let Ok(mut slot) = app.state::<BackendState>().pid.lock() {
        *slot = Some(pid);
    }

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        let mut port_announced = false;
        let deadline =
            std::time::Instant::now() + std::time::Duration::from_secs(30);

        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes).to_string();
                    if !port_announced {
                        if let Some(port) = handshake::parse_port_line(&line) {
                            port_announced = true;
                            if let Ok(mut slot) =
                                handle.state::<BackendState>().port.lock()
                            {
                                *slot = Some(port);
                            }
                            let _ = handle.emit(
                                "backend-ready",
                                BackendReadyPayload { port },
                            );
                        }
                    }
                    eprintln!("[backend stdout] {}", line.trim_end());
                }
                CommandEvent::Stderr(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes);
                    eprintln!("[backend stderr] {}", line.trim_end());
                }
                CommandEvent::Terminated(status) => {
                    if !port_announced {
                        let _ = handle.emit(
                            "backend-startup-failed",
                            BackendStartupFailedPayload {
                                message: format!(
                                    "Sidecar exited before announcing port (code={:?})",
                                    status.code
                                ),
                            },
                        );
                    } else {
                        let _ = handle.emit(
                            "backend-lost",
                            BackendStartupFailedPayload {
                                message: format!(
                                    "Backend process exited (code={:?})",
                                    status.code
                                ),
                            },
                        );
                    }
                    break;
                }
                _ => {}
            }

            if !port_announced && std::time::Instant::now() > deadline {
                let _ = handle.emit(
                    "backend-startup-failed",
                    BackendStartupFailedPayload {
                        message: "Handshake timed out (30s)".to_string(),
                    },
                );
                break;
            }
        }
    });

    Ok(())
}

/// Return `$HOME` as a `PathBuf`. Kept as a small helper so tests can
/// mock it without pulling in an external crate.
fn dirs_home() -> Option<std::path::PathBuf> {
    std::env::var_os("HOME").map(std::path::PathBuf::from)
}

/// Best-effort: send SIGTERM to the sidecar pid we recorded at spawn.
/// Uses libc on Unix; on Windows would need TerminateProcess — out of
/// scope for the macOS v1 ship.
#[cfg(unix)]
fn terminate_sidecar(pid: u32) {
    unsafe {
        libc::kill(pid as libc::pid_t, libc::SIGTERM);
    }
}

#[cfg(not(unix))]
fn terminate_sidecar(_pid: u32) {}

fn main() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_single_instance::init(|app, _argv, _cwd| {
                // Focus the existing window instead of starting a second
                // instance (covers spec Edge Case: multiple instances).
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.set_focus();
                    let _ = window.show();
                }
            }),
        )
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendState::new())
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .setup(|app| {
            if let Err(err) = spawn_backend(&app.handle()) {
                eprintln!("spawn_backend failed: {err}");
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.app_handle().try_state::<BackendState>() {
                    if let Ok(guard) = state.pid.lock() {
                        if let Some(pid) = *guard {
                            terminate_sidecar(pid);
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
