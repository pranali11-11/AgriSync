import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request Interceptor: Attach JWT Access Token
api.interceptors.request.use(
  (config) => {
    let token = localStorage.getItem('agrisync_access_token');
    try {
      const persisted = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
      token = persisted?.state?.token || token;
    } catch {}
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Automatic Refresh Token Interceptor
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      let refreshToken = localStorage.getItem('agrisync_refresh_token');
      try {
        const persisted = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
        refreshToken = persisted?.state?.refreshToken || refreshToken;
      } catch {}
      if (!refreshToken) {
        isRefreshing = false;
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(
          `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/refresh-token`,
          { refresh_token: refreshToken }
        );

        const { access_token } = response.data;
        localStorage.setItem('agrisync_access_token', access_token);
        try {
          const persisted = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
          if (persisted.state) {
            persisted.state.token = access_token;
            localStorage.setItem('agrisync-onboarding', JSON.stringify(persisted));
          }
        } catch {}
        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

        processQueue(null, access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        localStorage.removeItem('agrisync_access_token');
        localStorage.removeItem('agrisync_refresh_token');
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
