import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import { useVoice } from '../hooks/useVoice';
import { useAppStore } from '../store/useAppStore';
import { Mic, MicOff, Loader2 } from 'lucide-react';

/**
 * Hands-free Voice Input mic button using Web Speech API (en-IN / hi-IN / mr-IN).
 * Automatically updates parent input when transcript is recognized.
 * Hidden if browser unsupported.
 */
export const VoiceInput = ({ onSpeechResult, className = '' }) => {
  const language = useAppStore((state) => state.language);
  const { isSupported, isListening, transcript, startListening, stopListening, resetTranscript } = useVoice(language);

  useEffect(() => {
    if (transcript && onSpeechResult) {
      onSpeechResult(transcript);
    }
  }, [transcript, onSpeechResult]);

  if (!isSupported) {
    return null; // Gracefully hidden if Web Speech API unsupported
  }

  const handleToggle = () => {
    if (isListening) {
      stopListening();
    } else {
      resetTranscript();
      startListening();
    }
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      aria-label={isListening ? 'Stop listening' : 'Start voice input'}
      title={isListening ? 'Listening... Speak now' : 'Tap to speak'}
      className={`p-2.5 rounded-xl transition-all duration-200 touch-target min-h-[44px] min-w-[44px] flex items-center justify-center ${
        isListening
          ? 'bg-rose-600 text-white animate-pulse shadow-md'
          : 'bg-agri-green-100 text-agri-green-800 dark:bg-agri-green-950 dark:text-agri-green-300 hover:bg-agri-green-200'
      } ${className}`}
    >
      {isListening ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  );
};

VoiceInput.propTypes = {
  onSpeechResult: PropTypes.func.isRequired,
  className: PropTypes.string,
};
