'use client';

import React, { useState } from 'react';
import { Mic, MicOff, Check, AlertCircle, RefreshCw } from 'lucide-react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { db, CycleRecord } from '../db/database';
import voicePhrasesData from '../../content/en/voice_phrases.json';

interface VoiceLoggingScreenProps {
  onSaved: () => void;
}

export const VoiceLoggingScreen: React.FC<VoiceLoggingScreenProps> = ({ onSaved }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [parsedLog, setParsedLog] = useState<Partial<CycleRecord> | null>(null);

  const handleStartSimulatedVoice = () => {
    setIsListening(true);
    setTimeout(() => {
      // Pick a sample phrase from voice_phrases.json
      const sample = voicePhrasesData.phrases[0];
      setTranscript(sample.text);

      const parsed: Partial<CycleRecord> = {
        start_date: new Date().toISOString().split('T')[0],
        cycle_length: 28,
        flow_intensity: sample.expected.flow_intensity,
        pain_score: sample.expected.pain_score,
        symptoms: sample.expected.symptoms,
      };

      setParsedLog(parsed);
      setIsListening(false);
    }, 1200);
  };

  const handleConfirmSave = async () => {
    if (!parsedLog) return;

    const record: CycleRecord = {
      id: 'cycle_' + Date.now(),
      start_date: parsedLog.start_date || new Date().toISOString().split('T')[0],
      cycle_length: parsedLog.cycle_length || 28,
      flow_intensity: parsedLog.flow_intensity || 2,
      pain_score: parsedLog.pain_score || 3,
      symptoms: parsedLog.symptoms || [],
      created_at: new Date().toISOString(),
    };

    await db.cycles.put(record);
    onSaved();
    setTranscript('');
    setParsedLog(null);
  };

  return (
    <div className="space-y-6 max-w-md mx-auto pb-24">
      <div className="flex items-center gap-2">
        <Mic className="w-6 h-6 text-teal-700" />
        <h2 className="text-xl font-bold text-slate-900">On-Device Voice Logging</h2>
      </div>

      <Card variant="flat" className="p-5 text-center space-y-4">
        <p className="text-xs text-slate-600 leading-relaxed">
          Speak your symptoms or cycle details in English, Hindi, or Marathi. Voice parsing runs entirely on your phone — audio is never uploaded.
        </p>

        <div className="py-4">
          <button
            onClick={handleStartSimulatedVoice}
            className={`w-20 h-20 rounded-full mx-auto flex items-center justify-center transition-all ${
              isListening ? 'bg-amber-500 animate-ping text-white' : 'bg-teal-700 text-white shadow-lg hover:scale-105'
            }`}
          >
            {isListening ? <MicOff className="w-8 h-8" /> : <Mic className="w-8 h-8" />}
          </button>
          <div className="text-xs font-semibold text-slate-700 mt-3">
            {isListening ? 'Listening & Parsing On-Device...' : 'Tap Mic to Speak Log'}
          </div>
        </div>
      </Card>

      {/* Review Screen for Parsed Fields */}
      {parsedLog && (
        <Card variant="teal" className="p-4 space-y-3">
          <div className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
            <Check className="w-4 h-4 text-teal-700" />
            Review Parsed Log Before Saving
          </div>

          <div className="bg-white p-3 rounded-xl border text-xs space-y-1 text-slate-800">
            <div>Transcript: <em>"{transcript}"</em></div>
            <div>Parsed Flow Intensity: <strong>Level {parsedLog.flow_intensity} / 4</strong></div>
            <div>Parsed Pain Score: <strong>{parsedLog.pain_score} / 10</strong></div>
            <div>Parsed Symptoms: <strong>{parsedLog.symptoms?.join(', ') || 'None'}</strong></div>
          </div>

          <div className="flex gap-2">
            <Button variant="primary" fullWidth size="md" onClick={handleConfirmSave}>
              Confirm & Save Log
            </Button>

            <Button variant="outline" size="md" onClick={() => setParsedLog(null)}>
              Discard
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};
