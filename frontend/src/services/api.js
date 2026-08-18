const LOCAL_API_URL = 'http://127.0.0.1:8000/';

const VSCODE_TUNNEL_API_URL =
  'https://gv4knhz1-8000.inc1.devtunnels.ms/';

// ============================================================
// DETECT ENVIRONMENT
// ============================================================

const isProduction =
  import.meta.env.PROD === true;

// ============================================================
// API MODE
// ============================================================
//
// Local development:
//   VITE_API_MODE=local
//
// VS Code tunnel:
//   VITE_API_MODE=tunnel
//
// Auto:
//   Production  -> VS Code tunnel
//   Development -> localhost
//
// ============================================================

const API_MODE =
  import.meta.env.VITE_API_MODE || 'auto';

let rawBaseUrl;

if (API_MODE === 'local') {

  // Local frontend + local backend
  rawBaseUrl = LOCAL_API_URL;

} else if (API_MODE === 'tunnel') {

  // Frontend can be local or deployed
  // Backend is exposed through VS Code tunnel
  rawBaseUrl = VSCODE_TUNNEL_API_URL;

} else {

  // ==========================================================
  // AUTO MODE
  // ==========================================================

  if (import.meta.env.VITE_API_BASE_URL) {

    // Explicit Vercel/environment URL
    rawBaseUrl =
      import.meta.env.VITE_API_BASE_URL;

  } else if (isProduction) {

    // Vercel production
    // NEVER use 127.0.0.1 here
    rawBaseUrl =
      VSCODE_TUNNEL_API_URL;

  } else {

    // Local Vite development
    rawBaseUrl =
      LOCAL_API_URL;
  }
}

// ============================================================
// REMOVE TRAILING SLASH
// ============================================================

const API_BASE_URL =
  rawBaseUrl.replace(/\/+$/, '');

export default API_BASE_URL;