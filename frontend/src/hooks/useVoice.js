import { useState, useEffect, useCallback } from 'react';

/**
 * Custom hook wrapping Web Speech API with language support and text fallback.
 * @param {string} langCode - Language code ('en', 'hi', 'mr').
 */
export const useVoice = (langCode = 'en') => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);
  const [recognitionInstance, setRecognitionInstance] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState(null);

  const langMap = {
    en: 'en-IN',
    hi: 'hi-IN',
    mr: 'mr-IN',
  };

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      setIsSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = langMap[langCode] || 'en-IN';

      recognition.onresult = (event) => {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
        }
        setTranscript(currentTranscript);
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      setRecognitionInstance(recognition);
    } else {
      setIsSupported(false);
    }
  }, [langCode]);

  const speak = useCallback((text) => {
    if (!window.speechSynthesis || !text) {
      setError('Text-to-speech is not available in this browser.');
      return false;
    }
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = langMap[langCode] || 'en-IN';
      utterance.onstart = () => {
        setError(null);
        setPaused(false);
        setSpeaking(true);
      };
      utterance.onend = () => {
        setPaused(false);
        setSpeaking(false);
      };
      utterance.onerror = () => {
        setPaused(false);
        setSpeaking(false);
        setError('Audio could not be played. You can read the advisory on screen.');
      };
      window.speechSynthesis.speak(utterance);
      return true;
    } catch {
      setSpeaking(false);
      setError('Audio could not be played. You can read the advisory on screen.');
      return false;
    }
  }, [langCode]);

  const pause = useCallback(() => {
    if (!window.speechSynthesis || !speaking) return;
    window.speechSynthesis.pause();
    setPaused(true);
  }, [speaking]);

  const resume = useCallback(() => {
    if (!window.speechSynthesis || !paused) return;
    window.speechSynthesis.resume();
    setPaused(false);
  }, [paused]);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setPaused(false);
    setSpeaking(false);
  }, []);

  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  const startListening = useCallback(() => {
    if (recognitionInstance && !isListening) {
      try {
        setTranscript('');
        recognitionInstance.start();
        setIsListening(true);
      } catch (err) {
        console.error('Failed to start speech recognition:', err);
      }
    }
  }, [recognitionInstance, isListening]);

  const stopListening = useCallback(() => {
    if (recognitionInstance && isListening) {
      try {
        recognitionInstance.stop();
        setIsListening(false);
      } catch (err) {
        console.error('Failed to stop speech recognition:', err);
      }
    }
  }, [recognitionInstance, isListening]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
  }, []);

  return {
    isSupported,
    isListening,
    transcript,
    setTranscript,
    startListening,
    stopListening,
    resetTranscript,
    speak,
    speaking,
    paused,
    pause,
    resume,
    stop,
    error,
  };
};
