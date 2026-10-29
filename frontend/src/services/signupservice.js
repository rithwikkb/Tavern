import api from './axios';  // Adjust the path based on your project structure

export const signup = async (signupData) => {
  try {
    const response = await api.post('signup/', signupData, {
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });
    return response.data;
  } catch (error) {
    // surface the server's reason (e.g. "Username already exists.") to the signup form
    throw new Error(error.response?.data?.message || error.response?.data?.detail || 'Signup failed. Please try again.');
  }
};
