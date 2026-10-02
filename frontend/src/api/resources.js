import api from './axios';

export const fetchMachines = async (params) => (await api.get('/resources/machines', { params })).data;
export const fetchProviders = async (params) => (await api.get('/resources/providers', { params })).data;
export const fetchInputSellers = async (params) => (await api.get('/resources/input-sellers', { params })).data;
export const fetchMachineDetail = async (id, params) => (await api.get(`/resources/machines/${id}`, { params })).data;
export const createMachineListing = async (payload) => (await api.post('/resources/machines', payload)).data;
