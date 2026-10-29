import api from "./axios";

// URL: ://service/api/authors/
export const getAuthors = async () => {
    try {
      const response = await api.get(
        `authors/`
      );
      return response.data;
    } catch (error) {
      console.error(error);
    }
  };

//URL: ://service/api/authors/{AUTHOR_SERIAL}/
export const getAuthor = async (authorSerial) => {
  try {
    const response = await api.get(
      `authors/${authorSerial}/`
    );
    return response.data;
  } catch (error) {
    console.error(error);
  }
};

// URL: ://service/api/authors/get_remote_authors
export const getRemoteAuthors = async () => {
  try {
    const response = await api.get(
      `authors/all/`
    );
    return response.data;
  } catch (error) {
    console.error(error);
  }
};

// The logged-in author's record is needed by every post card (to like/comment as them);
// fetch it once and share it instead of once per card.
let currentAuthorCache = { id: null, promise: null };

export const getCurrentAuthor = (authorId) => {
  if (currentAuthorCache.id !== authorId || !currentAuthorCache.promise) {
    const promise = getAuthor(authorId).then((data) => {
      if (!data) {
        // don't cache a failed lookup
        currentAuthorCache = { id: null, promise: null };
      }
      return data;
    });
    currentAuthorCache = { id: authorId, promise };
  }
  return currentAuthorCache.promise;
};

// Call after the user edits their profile so the next lookup sees the new name/picture
export const clearCurrentAuthorCache = () => {
  currentAuthorCache = { id: null, promise: null };
};

