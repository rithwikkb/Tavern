import axios from 'axios';
import Cookies from 'js-cookie';
import { clearAuthCookies, removeLegacyTokenCookies } from '../utils/authCookies';

// Login tokens are HttpOnly cookies set by the server: the browser sends them with every
// request, and this code never sees them. Requests that change something also need
// Django's CSRF token (from the readable `csrftoken` cookie) in the X-CSRFToken header.
const csrfConfig = {
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
};

// sessions from before the switch to HttpOnly cookies left readable token cookies behind
removeLegacyTokenCookies();

const api = axios.create({
  baseURL: `${window.location.origin}/api/`,
  ...csrfConfig,
});

api.interceptors.request.use(
  (config) => {
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// One refresh at a time: the feed fires many requests at once, and the server
// blacklists a refresh token after its first use, so parallel refreshes would fail.
let refreshPromise = null;

const refreshTokens = () => {
  if (!refreshPromise) {
    // the refresh token cookie is sent automatically; the new tokens come back as cookies
    refreshPromise = axios
      .post(`${window.location.origin}/api/users/token/refresh/`, null, csrfConfig)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

// When the access token has expired, refresh it once and retry the request
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    // network errors have no response; only try when the user is (or was) logged in
    if (error.response?.status === 401 && !originalRequest._retry && Cookies.get('author_id')) {
      originalRequest._retry = true;
      try {
        await refreshTokens();
        return api(originalRequest);
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
    return Promise.reject(error);
  }
);

export default api;
