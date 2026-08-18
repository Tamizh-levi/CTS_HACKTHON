const LOCAL_API_URL = 'http://127.0.0.1:8000';

const VSCODE_TUNNEL_API_URL =
  'https://gv4knhz1-8000.inc1.devtunnels.ms/';

// ============================================================
// API MODE
// ============================================================
// Set this to:
//   'local'  -> use localhost
//   'tunnel' -> use VS Code Dev Tunnel
//   'auto'   -> use VITE_API_BASE_URL if available
//
// Default: auto
// ============================================================

const API_MODE = import.meta.env.VITE_API_MODE || 'auto';

let rawBaseUrl;

if (API_MODE === 'local') {
  rawBaseUrl = LOCAL_API_URL;

} else if (API_MODE === 'tunnel') {
  rawBaseUrl = VSCODE_TUNNEL_API_URL;

} else {
  // AUTO MODE
  // VITE_API_BASE_URL has highest priority.
  rawBaseUrl =
    import.meta.env.VITE_API_BASE_URL ||
    LOCAL_API_URL;
}

// Remove trailing slash
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

export default API_BASE_URL;