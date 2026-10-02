import api from './axios';

export const fetchSystemHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};
