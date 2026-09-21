import axios from "axios";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: API_URL });

const TOKEN_KEY = "access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// A 401 on any authenticated call means the session JWT expired or was invalidated -
// there's no server-side session to refresh, so the only correct move is to drop the
// stale token and reload. Without this, the UI keeps showing the user as "logged in"
// while every API call silently fails.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && getToken()) {
      setToken(null);
      window.location.reload();
    }
    return Promise.reject(error);
  }
);
