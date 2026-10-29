import api from './axios';

// Many components (every post card, the feed, the profile page) ask for the same
// author at once; share one request per author while it is in flight.
const inFlightProfiles = new Map();

export const getAuthorProfile = async (authorId) => {
    if (!inFlightProfiles.has(authorId)) {
        const request = api
            .get(`authors/${authorId}/profile/`)
            .then((response) => response.data)
            .finally(() => inFlightProfiles.delete(authorId));
        inFlightProfiles.set(authorId, request);
    }
    try {
        return await inFlightProfiles.get(authorId);
    } catch (error) {
        console.error('Error fetching profile:', error);
        throw error;
    }
};
