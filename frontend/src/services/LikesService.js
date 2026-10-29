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

// URL: /api/authors/{author_id}/liked/  (DELETE removes this author's like on `object`)
// Returns 'removed', 'missing' (there was no like to remove) or null on failure.
export const deleteLike = async (authorSerial, objectUrl) => {
    try {
      await api.delete(`/authors/${authorSerial}/liked/`, { data: { object: objectUrl } });
      return 'removed';
    } catch (error) {
      if (error.response?.status === 404) {
        return 'missing';
      }
      console.error(error);
      return null;
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