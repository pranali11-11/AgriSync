import api from './axios';

export const requestOTP = async (phone) => {
  const response = await api.post('/auth/request-otp', { phone });
  return response.data;
};

export const verifyOTP = async (phone, otp) => {
  const response = await api.post('/auth/verify-otp', { phone, otp });
  return response.data;
};

export const refreshTokenApi = async (refreshToken) => {
  const response = await api.post('/auth/refresh-token', { refresh_token: refreshToken });
  return response.data;
};
