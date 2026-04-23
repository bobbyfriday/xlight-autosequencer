import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { Splash } from './components/Splash/Splash';
import { bootstrapApi } from './lib/apiClient';

const root = ReactDOM.createRoot(document.getElementById('root')!);

// Show the splash immediately so there is no blank window between Tauri
// creating the WKWebView and the backend sidecar signalling ready.
root.render(
  <React.StrictMode>
    <Splash />
  </React.StrictMode>,
);

// In dev this resolves to "" synchronously-ish; in Tauri prod it waits
// for the `backend-ready` event from the Rust shell.
bootstrapApi()
  .then(() => {
    root.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>,
    );
  })
  .catch((err) => {
    root.render(
      <React.StrictMode>
        <Splash error={err instanceof Error ? err.message : String(err)} />
      </React.StrictMode>,
    );
  });
