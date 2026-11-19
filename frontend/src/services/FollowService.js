import api from './axios';

// URL: api/authors/{author_id}/inbox/follow_requests/
export const getFollowRequests = async (authorSerial) => {
  try {
    const response = await api.get(
      `authors/${authorSerial}/inbox/follow_requests/`
    );
    return response.data;
  } catch (error) {
    console.error(error);
  }
};

// URL: /api/authors/{author_id}/inbox/
export const createFollowRequest = async (authorSerial, followRequestData) => {
  try {
    console.log(`FOLLOW REQUEST ${followRequestData}`);
    const response = await api.post(
      `/authors/${authorSerial}/inbox/`,
      followRequestData
    );
    return response;
  } catch (error) {
    console.error(error);
  }
};

// URL: service/api/authors/<str:author_id>/followers/<str:follower_id>/
export const checkIfFollowing = async (authorId, followerId) => {
  // Check if followerId is a follower of authorId
  try {
    const response = await api.get(
      `authors/${authorId}/followers/${followerId}/`
    );
    return response;
  } catch (error) {
    if (error.response && error.response.status === 404) {
      return { data: { status: 'Follow request not found' } };
    }
  }
};

// URL: service/api/authors/<str:author_id>/followers/<str:follower_id>/
// based on the requird format of API , service/api/... service at the front.
export const acceptFollowRequest = async (authorId, followerId) => {
  try {
    const response = await api.put(
      `/authors/${authorId}/followers/${followerId}/`,
      null
    ); // use absolute URL
    return response.data;
  } catch (error) {
    console.error('Error accepting follow request:', error);
  }
};

export const rejectFollowRequest = async (authorId, followerId) => {
  try {
    await api.delete(`/authors/${authorId}/followers/${followerId}/`); // use absolute URL
  } catch (error) {
    console.error('Error rejecting follow request:', error);
  }
};
