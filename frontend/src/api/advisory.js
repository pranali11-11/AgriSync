import api from './axios';

export const fetchAdvisory = async (farmId, lang) => {
  const response = await api.get(`/farms/${farmId}/advisory`, { params: { lang } });
  return response.data;
};

export const askAdvisoryAssistant = async (farmId, question) => {
  const response = await api.post(`/farms/${farmId}/advisory/assistant`, {
    question: question || null,
  });
  return response.data;
};
