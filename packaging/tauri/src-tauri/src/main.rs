// Prevents additional console window on Windows (no-op on macOS; kept so the
// shell is portable if Windows is ever added back).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod handshake;

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Mutex;

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, State};

/// Cached backend port; written once the handshake line is parsed on the
/// sidecar's stdout, read by the frontend via `get_backend_port` and also
/// used for graceful shutdown.
struct BackendState {
    port: Mutex<Option<u16>>,
    // We intentionally do NOT retain a reference to the child process here;
    // the Command handle is consumed by the waiter thread, and shutdown is
    // performed by sending SIGTERM to the pid recorded at spawn.
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

/// Resolve the backend binary path. Tauri copies the PyInstaller onedir
/// into the resource dir (under `backend/`) per `tauri.conf.json >
/// bundle.resources` — in dev that's `target/debug/backend/`, in release
/// it's `.app/Contents/Resources/backend/`.
fn backend_binary_path(app: &AppHandle) -> Result<PathBuf, String> {
    let arch = std::env::consts::ARCH;
    let binary_name = format!("backend-{arch}-apple-darwin");
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource_dir: {e}"))?;
    Ok(resource_dir.join("backend").join(&binary_name))
}

/// Spawn the PyInstaller backend and wire up stdout parsing.
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

    let backend_path = backend_binary_path(app)?;

    let mut child = Command::new(&backend_path)
        .env("XLIGHT_PACKAGED", "1")
        .env("PYTHONUNBUFFERED", "1")
        .env("VAMP_PATH", vamp_path.to_string_lossy().to_string())
        .env("TORCH_HOME", torch_home.to_string_lossy().to_string())
        // Cap torch/openmp thread count so we don't spike CPU at startup.
        .env("OMP_NUM_THREADS", "4")
        .env("MKL_NUM_THREADS", "4")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("failed to spawn backend ({}): {e}", backend_path.display()))?;

    let pid = child.id();
    if let Ok(mut slot) = app.state::<BackendState>().pid.lock() {
        *slot = Some(pid);
    }

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "backend: no stdout".to_string())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "backend: no stderr".to_string())?;

    // Stdout reader: parses the port handshake and passes remaining lines
    // through to our log.
    let stdout_handle = app.clone();
    std::thread::spawn(move || {
        let reader = BufReader::new(stdout);
        let mut port_announced = false;
        for line in reader.lines() {
            let Ok(line) = line else { break };
            if !port_announced {
                if let Some(port) = handshake::parse_port_line(&line) {
                    port_announced = true;
                    if let Ok(mut slot) = stdout_handle.state::<BackendState>().port.lock() {
                        *slot = Some(port);
                    }
                    let _ = stdout_handle
                        .emit("backend-ready", BackendReadyPayload { port });
                }
            }
            eprintln!("[backend stdout] {}", line.trim_end());
        }
    });

    // Stderr reader: pass-through to our log.
    std::thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            if let Ok(line) = line {
                eprintln!("[backend stderr] {}", line.trim_end());
            }
        }
    });

    // Waiter: detects backend termination and emits the appropriate event
    // (startup-failed if the port was never announced, backend-lost if the
    // process exited after handshake).
    let wait_handle = app.clone();
    std::thread::spawn(move || {
        let status = child.wait();
        let port = wait_handle
            .state::<BackendState>()
            .port
            .lock()
            .ok()
            .and_then(|g| *g);
        let code = status.as_ref().ok().and_then(|s| s.code());
        let event = if port.is_some() {
            "backend-lost"
        } else {
            "backend-startup-failed"
        };
        let _ = wait_handle.emit(
            event,
            BackendStartupFailedPayload {
                message: format!("Backend process exited (code={code:?})"),
            },
        );
    });

    // Handshake deadline: if the port hasn't been announced within 30s,
    // surface a failure event so the frontend can stop waiting.
    let deadline_handle = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_secs(30));
        let port = deadline_handle
            .state::<BackendState>()
            .port
            .lock()
            .ok()
            .and_then(|g| *g);
        if port.is_none() {
            let _ = deadline_handle.emit(
                "backend-startup-failed",
                BackendStartupFailedPayload {
                    message: "Handshake timed out (30s)".to_string(),
                },
            );
        }
    });

    Ok(())
}

/// Return `$HOME` as a `PathBuf`. Kept as a small helper so tests can
/// mock it without pulling in an external crate.
fn dirs_home() -> Option<std::path::PathBuf> {
    std::env::var_os("HOME").map(std::path::PathBuf::from)
}

/// Best-effort: send SIGTERM to the backend pid we recorded at spawn.
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
