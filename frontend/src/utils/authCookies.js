import Cookies from 'js-cookie';

// The login tokens are HttpOnly cookies that only the server sets and reads.
// These two cookies are just for the page: who's logged in, and whether it's the
// shared demo account. Neither is a secret.
const cookieOptions = () => ({
  sameSite: 'strict',
  secure: window.location.protocol === 'https:',
});

export const setAuthCookies = ({ authorId, isDemo }) => {
  if (authorId !== undefined) {
    Cookies.set('author_id', authorId, cookieOptions());
  }
  // only set on login/signup; the shared demo account can't edit its profile
  if (isDemo) {
    Cookies.set('is_demo', '1', cookieOptions());
  } else if (isDemo === false) {
    Cookies.remove('is_demo');
  }
};

export const isDemoAccount = () => Cookies.get('is_demo') === '1';

// Older versions stored the tokens in readable cookies. Removing them here can't touch
// the HttpOnly ones (scripts can't change those), only the leftovers.
export const removeLegacyTokenCookies = () => {
  Cookies.remove('access_token');
  Cookies.remove('refresh_token');
};

// The server clears the HttpOnly token cookies when logging out.
export const clearAuthCookies = () => {
  Cookies.remove('author_id');
  Cookies.remove('is_demo');
  removeLegacyTokenCookies();
};
