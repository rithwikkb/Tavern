import api from './axios';

// URL: api/authors/<uuid:author_serial>/commented/
export const createCommentLocal = async (authorSerial, commentData) => {
  try {
    const response = await api.post(
      `/authors/${authorSerial}/commented/`,
      commentData
    );
    return response.data;
  } catch (error) {
    console.error(error);
  }
};

// URL: ://service/api/authors/{AUTHOR_SERIAL}/posts/{POST_SERIAL}/comments
export const getComments = async (authorSerial, postSerial) => {
  try {
    const response = await api.get(
      `/authors/${authorSerial}/posts/${postSerial}/comments/`
    );
    return response.data;
  } catch (error) {
    console.error(error);
  }
};

