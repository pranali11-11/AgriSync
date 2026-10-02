import api from './axios';

export const fetchMe = async () => {
  const response = await api.get('/me');
  return response.data;
};

export const updateMe = async (data) => {
  const response = await api.put('/me', data);
  return response.data;
};

export const fetchFarmerProfile = async () => {
  const response = await api.get('/farmer/profile');
  return response.data;
};

export const saveFarmerProfile = async (profileData) => {
  const response = await api.post('/farmer/profile', profileData);
  return response.data;
};

export const fetchFarms = async () => {
  const response = await api.get('/farms');
  return response.data;
};

export const createFarm = async (farmData) => {
  const response = await api.post('/farms', farmData);
  return response.data;
};

export const updateFarm = async (farmId, farmData) => {
  const response = await api.put(`/farms/${farmId}`, farmData);
  return response.data;
};

export const saveSoilTest = async (farmId, soilData) => {
  const response = await api.post(`/farms/${farmId}/soil-test`, soilData);
  return response.data;
};
