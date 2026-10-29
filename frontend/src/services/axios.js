import axios from 'axios';
import Cookies from 'js-cookie';
import { clearAuthCookies, setAuthCookies } from '../utils/authCookies';

const api = axios.create({
  baseURL: `${window.location.origin}/api/`,
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    const accessToken = Cookies.get('access_token');

    if (config.data instanceof FormData) {
      // config.headers['Content-Type'] = 'multipart/form-data';
    } else {
      config.headers['Content-Type'] = 'application/json';
    }

    if (accessToken) {
      config.headers['Authorization'] = `Bearer ${accessToken}`;
    } else {
      delete config.headers['Authorization'];
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// One refresh at a time: the feed fires many requests at once, and the server
// blacklists a refresh token after its first use, so parallel refreshes would fail.
let refreshPromise = null;

const refreshAccessToken = (refreshToken) => {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${window.location.origin}/api/users/token/refresh/`, {
        refresh: refreshToken,
      })
      .then((response) => {
        const accessToken = response.data['access'];
        // refresh tokens are rotated, so keep the new one for next time
        setAuthCookies({ accessToken, refreshToken: response.data['refresh'] });
        return accessToken;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

// Refresh access token if expired
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    // network errors have no response
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = Cookies.get('refresh_token');
      if (refreshToken) {
        try {
          const accessToken = await refreshAccessToken(refreshToken);
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          return axios(originalRequest);
        } catch (refreshError) {
          clearAuthCookies();
          // session has fully expired; send the user back to log in
          // (unless they're already there, so the login page can show its own errors)
          const onAuthPage = ['/login', '/signup'].some((path) =>
            window.location.pathname.startsWith(path)
          );
          if (!onAuthPage) {
            window.location.href = '/login';
          }
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
