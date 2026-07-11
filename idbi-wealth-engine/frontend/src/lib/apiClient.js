import axios from 'axios';

// In production, VITE_API_URL points to the Render backend
// (e.g. https://idbi-wealth-backend.onrender.com).
// In local dev, VITE_API_URL is unset -> baseURL is "" -> requests hit the same
// origin, which Vite's dev proxy forwards to http://localhost:8000.
const API_BASE = import.meta.env.VITE_API_URL || '';

// Every backend request must carry the API key in the X-API-Key header.
// VITE_API_KEY is injected at build time from the environment; when unset
// (e.g. local dev with the gate open) it stays empty and no header is attached.
const API_KEY = import.meta.env.VITE_API_KEY || '';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'X-API-Key': API_KEY,
  },
});

export default apiClient;
