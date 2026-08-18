const rawBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  'https://gv4knhz1-8000.inc1.devtunnels.ms/';

const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

export default API_BASE_URL;