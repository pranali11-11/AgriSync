import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook wrapping native browser WebSocket with reconnect logic.
 * @param {string} url - WebSocket URL to connect to.
 * @param {object} options - Options including autoReconnect, reconnectInterval, onMessage, onError.
 */
export const useWebSocket = (url, options = {}) => {
  const {
    autoReconnect = true,
    reconnectInterval = 3000,
    onMessage,
    onError,
    onOpen,
    onClose,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  const connect = useCallback(() => {
    if (!url) return;
    try {
      const socket = new WebSocket(url);

      socket.onopen = (event) => {
        setIsConnected(true);
        if (onOpen) onOpen(event);
      };

      socket.onmessage = (event) => {
        setLastMessage(event.data);
        if (onMessage) onMessage(event.data);
      };

      socket.onerror = (event) => {
        if (onError) onError(event);
      };

      socket.onclose = (event) => {
        setIsConnected(false);
        if (onClose) onClose(event);

        if (autoReconnect) {
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      socketRef.current = socket;
    } catch (err) {
      if (onError) onError(err);
    }
  }, [url, autoReconnect, reconnectInterval, onMessage, onError, onOpen, onClose]);

  const sendMessage = useCallback((data) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      socketRef.current.send(payload);
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    reconnect: connect,
  };
};
