'use client';

import React, { useState } from 'react';
import { Volume2, VolumeX, FileText, Play, Pause } from 'lucide-react';
import { Button } from './Button';

interface AudioPlayerProps {
  audioUrl: string;
  transcript: string;
  title: string;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, transcript, title }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [synth, setSynth] = useState<SpeechSynthesisUtterance | null>(null);

  const handlePlayToggle = () => {
    if (typeof window === 'undefined') return;

    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
    } else {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(transcript);
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);
      window.speechSynthesis.speak(utterance);
      setSynth(utterance);
      setIsPlaying(true);
    }
  };

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 my-2">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {isPlaying ? (
            <Volume2 className="w-5 h-5 text-teal-700 animate-pulse" />
          ) : (
            <VolumeX className="w-5 h-5 text-slate-400" />
          )}
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
            {isPlaying ? 'Playing Audio' : 'Audio Explanation'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant={isPlaying ? 'amber' : 'primary'}
            size="sm"
            onClick={handlePlayToggle}
            aria-label={isPlaying ? 'Pause audio' : 'Play audio explanation'}
          >
            {isPlaying ? (
              <>
                <Pause className="w-4 h-4 mr-1.5" /> Pause Audio
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-1.5" /> Listen Audio
              </>
            )}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowTranscript(!showTranscript)}
            aria-label="Toggle text transcript"
          >
            <FileText className="w-4 h-4 mr-1" />
            {showTranscript ? 'Hide Text' : 'Read Text'}
          </Button>
        </div>
      </div>

      {showTranscript && (
        <div className="mt-3 pt-3 border-t border-slate-200 text-sm text-slate-700 leading-relaxed bg-white p-3 rounded-lg border">
          <div className="font-medium text-slate-900 mb-1">Transcript:</div>
          <p>{transcript}</p>
        </div>
      )}
    </div>
  );
};
