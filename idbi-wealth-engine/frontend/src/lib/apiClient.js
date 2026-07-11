import axios from 'axios';

// In production, VITE_API_URL points to the Render backend
// (e.g. https://idbi-wealth-backend.onrender.com).
// In local dev, VITE_API_URL is unset -> baseURL is "" -> requests hit the same
// origin, which Vite's dev proxy forwards to http://localhost:8000.
const API_BASE = import.meta.env.VITE_API_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE,
});

export default apiClient;
