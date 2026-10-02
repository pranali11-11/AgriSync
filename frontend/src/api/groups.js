import api from './axios';

export const fetchNearbyGroups = (params) => api.get('/groups/nearby', { params }).then((response) => response.data);
export const fetchMyGroups = () => api.get('/groups/mine').then((response) => response.data);
export const fetchGroup = (id) => api.get(`/groups/${id}`).then((response) => response.data);
export const previewGroup = (id, acres) => api.get(`/groups/${id}/preview`, { params: { acres } }).then((response) => response.data);
export const createGroup = (payload) => api.post('/groups', payload).then((response) => response.data);
export const joinGroup = (id, payload) => api.post(`/groups/${id}/join`, payload).then((response) => response.data);
export const leaveGroup = (id) => api.post(`/groups/${id}/leave`).then((response) => response.data);
