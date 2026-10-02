import api from './axios';

export const fetchCrops = async () => {
  const response = await api.get('/crops');
  return response.data;
};
