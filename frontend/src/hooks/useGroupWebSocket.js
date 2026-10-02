import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export function useGroupWebSocket(groupId) {
  const queryClient = useQueryClient();
  const socketRef = useRef(null);
  const timerRef = useRef(null);
  const [state, setState] = useState('connecting');
  const attempts = useRef(0);
  useEffect(() => {
    if (!groupId) return undefined;
    let stopped = false;
    const poll = setInterval(() => queryClient.invalidateQueries({ queryKey: ['group', groupId] }), 10000);
    const connect = () => {
      if (stopped) return;
      const persisted = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
      const token = persisted?.state?.token;
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const socket = new WebSocket(`${protocol}://${window.location.hostname}:8000/api/v1/ws/groups/${groupId}?token=${encodeURIComponent(token || '')}`);
      socketRef.current = socket;
      socket.onopen = () => { attempts.current = 0; setState('live'); };
      socket.onmessage = () => queryClient.invalidateQueries({ queryKey: ['group', groupId] });
      socket.onerror = () => setState('reconnecting');
      socket.onclose = () => {
        if (stopped) return;
        setState('reconnecting');
        const delay = Math.min(30000, 1000 * (2 ** attempts.current));
        attempts.current += 1;
        timerRef.current = setTimeout(connect, delay);
      };
    };
    connect();
    return () => { stopped = true; clearInterval(poll); clearTimeout(timerRef.current); socketRef.current?.close(); };
  }, [groupId, queryClient]);
  return state;
}
