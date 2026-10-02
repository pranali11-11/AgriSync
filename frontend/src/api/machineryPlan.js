import api from './axios';

export const fetchMachineryPlan = (farmId, params = {}) => api.get(`/farms/${farmId}/machinery-plan`, { params }).then((response) => response.data);
