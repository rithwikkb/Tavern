import api from "./axios";

// URL: /api/authors/{author_id}/liked/
export const createLike = async (authorSerial, likeData) => {
    try {
      const response = await api.post(
        `/authors/${authorSerial}/liked/`,
        likeData
      );
      return response;
    } catch (error) {
      console.error(error);
    }
};

// URL: /api/authors/{author_id}/posts/{post_id}/likes/
export const getLikes = async (authorSerial, postSerial, size) => {
    try {
      const response = await api.get(
        `/authors/${authorSerial}/posts/${postSerial}/likes/`,
        size ? { params: { size } } : undefined
      );
      return response.data;
    } catch (error) {
      console.error(error);
    }
};