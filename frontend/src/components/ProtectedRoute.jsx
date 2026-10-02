import React from 'react';
import PropTypes from 'prop-types';
import { Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchMe, fetchFarms } from '../api/farmer';
import { useAppStore } from '../store/useAppStore';
import { Loader2 } from 'lucide-react';

export const ProtectedRoute = ({ children, requireFarm = false }) => {
  const token = localStorage.getItem('agrisync_access_token');
  const setUser = useAppStore((state) => state.setUser);

  const { data: user, isLoading: isLoadingUser, isError: isUserError } = useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
    enabled: !!token,
    onSuccess: (data) => setUser(data),
  });

  const { data: farms, isLoading: isLoadingFarms } = useQuery({
    queryKey: ['farms'],
    queryFn: fetchFarms,
    enabled: !!token && !!user,
  });

  if (!token || isUserError) {
    return <Navigate to="/login" replace />;
  }

  if (isLoadingUser || (requireFarm && isLoadingFarms)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="w-8 h-8 text-agri-green-700 animate-spin" />
          <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
            Loading AgriSync Profile...
          </span>
        </div>
      </div>
    );
  }

  if (requireFarm && user?.role === 'farmer' && (!farms || farms.length === 0)) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
};

ProtectedRoute.propTypes = {
  children: PropTypes.node.isRequired,
  requireFarm: PropTypes.bool,
};
