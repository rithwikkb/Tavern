import api from './axios';

export const login = async (loginData) => {
  try {
    const response = await api.post('login/', loginData);
    return response.data;
  } catch (error) {
    throw error;
  }
};
