'use client';

import React from 'react';
import { Card } from '../components/Card';
import { AudioPlayer } from '../components/AudioPlayer';
import { HelpCircle } from 'lucide-react';

interface MythCardScreenProps {
  messages: any;
}

export const MythCardScreen: React.FC<MythCardScreenProps> = ({ messages }) => {
  const myths = messages?.myths || [];

  return (
    <div className="space-y-5 max-w-md mx-auto pb-24">
      <div className="flex items-center gap-2">
        <HelpCircle className="w-6 h-6 text-teal-700" />
        <h2 className="text-xl font-bold text-slate-900">Audio Myth & Fact Cards</h2>
      </div>

      <div className="space-y-4">
        {myths.map((myth: any) => (
          <Card key={myth.id} variant="flat" className="p-4 space-y-3">
            <h3 className="font-bold text-slate-900 text-base leading-snug">{myth.title}</h3>
            <AudioPlayer audioUrl={myth.audio_url} transcript={myth.transcript} title={myth.title} />
          </Card>
        ))}
      </div>
    </div>
  );
};
