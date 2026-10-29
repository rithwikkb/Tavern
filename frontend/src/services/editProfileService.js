import api from './axios';
import { clearCurrentAuthorCache } from './AuthorsService';

const currentHost = window.location.origin; // Get host for the image upload URL

// Function to fetch the author profile
export const getAuthorProfile = async (authorId) => {
    const response = await api.get(`authors/${authorId}/profile/`);
    return response.data;
};

// Function to update the author profile
export const updateAuthorProfile = async (authorId, profileData) => {
    try {
        const response = await api.put(`authors/${authorId}/profile/edit/`, profileData);
        clearCurrentAuthorCache();
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.error || 'Failed to update profile');
    }
};

export const uploadProfileImage = async (authorId, formData) => {
    const response = await fetch(`${currentHost}/authors/${authorId}/upload_image/`, {
        method: 'POST',
        body: formData
    });
    return response;
};
