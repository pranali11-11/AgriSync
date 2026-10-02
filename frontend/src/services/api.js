import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// Attach JWT on every request
api.interceptors.request.use((config) => {
  try {
    const persisted = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
    const token = persisted?.state?.token;
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } catch {}
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const persisted = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
        const refreshToken = persisted?.state?.refreshToken;
        if (refreshToken) {
          const { data } = await axios.post(
            `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/refresh-token`,
            { refresh_token: refreshToken }
          );
          // Update persisted token
          const stored = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
          if (stored.state) {
            stored.state.token = data.access_token;
            localStorage.setItem('agrisync-onboarding', JSON.stringify(stored));
          }
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        }
      } catch {}
    }
    return Promise.reject(error);
  }
);

export default api;

// Convenience wrappers
export const authApi = {
  requestOtp: (phone) => api.post('/auth/request-otp', { phone }),
  verifyOtp: (phone, otp, name) =>
    api.post('/auth/verify-otp', { phone, otp, ...(name ? { name } : {}) }),
};

export const meApi = {
  get: () => api.get('/me'),
  update: (data) => api.put('/me', data),
};

export const farmerApi = {
  getProfile: () => api.get('/farmer/profile'),
  createProfile: (data) => api.post('/farmer/profile', data),
  updateProfile: (data) => api.put('/farmer/profile', data),
};

export const cropsApi = {
  list: () => api.get('/crops'),
};

export const farmsApi = {
  list: () => api.get('/farms'),
  create: (data) => api.post('/farms', data),
  get: (id) => api.get(`/farms/${id}`),
  update: (id, data) => api.put(`/farms/${id}`, data),
  delete: (id) => api.delete(`/farms/${id}`),
};

export const soilApi = {
  get: (farmId) => api.get(`/farms/${farmId}/soil-test`),
  create: (farmId, data) => api.post(`/farms/${farmId}/soil-test`, data),
};
