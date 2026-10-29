import Cookies from 'js-cookie';

// Login state lives in three cookies the app reads with JavaScript. Mark them
// Secure on HTTPS (so they're never sent over plain http) and SameSite=Strict.
const cookieOptions = () => ({
  sameSite: 'strict',
  secure: window.location.protocol === 'https:',
});

export const setAuthCookies = ({ authorId, accessToken, refreshToken }) => {
  if (authorId !== undefined) {
    Cookies.set('author_id', authorId, cookieOptions());
  }
  if (accessToken !== undefined) {
    Cookies.set('access_token', accessToken, cookieOptions());
  }
  if (refreshToken !== undefined) {
    Cookies.set('refresh_token', refreshToken, cookieOptions());
  }
};

export const clearAuthCookies = () => {
  Cookies.remove('author_id');
  Cookies.remove('access_token');
  Cookies.remove('refresh_token');
};
