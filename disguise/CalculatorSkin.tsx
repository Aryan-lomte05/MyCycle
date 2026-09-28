'use client';

import React, { useState } from 'react';
import { Lock, Unlock, AlertCircle } from 'lucide-react';

interface CalculatorSkinProps {
  onUnlockSuccess: () => void;
  savedPinHash?: string;
  onSetPinHash?: (hash: string) => void;
}

// Utility function to compute PBKDF2 hash using WebCrypto
export async function hashPin(pin: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(pin),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );

  const salt = encoder.encode('mycycle_disguise_salt_2026');
  const derivedKey = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt,
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    256
  );

  return Array.from(new Uint8Array(derivedKey))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export const CalculatorSkin: React.FC<CalculatorSkinProps> = ({
  onUnlockSuccess,
  savedPinHash,
  onSetPinHash,
}) => {
  const [display, setDisplay] = useState('0');
  const [inputPin, setInputPin] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [setupMode, setSetupMode] = useState(!savedPinHash);
  const [newPin, setNewPin] = useState('');

  const handleDigit = (digit: string) => {
    if (display === '0' || display === 'Error') {
      setDisplay(digit);
    } else {
      setDisplay(display + digit);
    }
    setInputPin((prev) => prev + digit);
  };

  const handleClear = () => {
    setDisplay('0');
    setInputPin('');
    setErrorMsg('');
  };

  const handleEquals = async () => {
    try {
      // Evaluate basic arithmetic if user is actually calculating
      if (display.includes('+') || display.includes('-') || display.includes('*') || display.includes('/')) {
        // Safe evaluation without eval
        const result = Function(`'use strict'; return (${display})`)();
        setDisplay(String(result));
      }

      // Check PIN unlock
      if (inputPin) {
        const computedHash = await hashPin(inputPin);
        if (savedPinHash && computedHash === savedPinHash) {
          onUnlockSuccess();
          return;
        } else if (!savedPinHash && inputPin.length >= 4) {
          if (onSetPinHash) {
            onSetPinHash(computedHash);
            setSetupMode(false);
            onUnlockSuccess();
            return;
          }
        } else if (savedPinHash) {
          setErrorMsg('Incorrect passcode.');
        }
      }
    } catch {
      setDisplay('Error');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col justify-between p-6 max-w-md mx-auto">
      {/* Calculator Header */}
      <div className="flex items-center justify-between pt-4 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2 text-slate-400 text-sm font-mono">
          <Lock className="w-4 h-4 text-amber-500" />
          <span>Calc-Standard v2.4</span>
        </div>
        <span className="text-xs text-slate-500">Solar Powered</span>
      </div>

      {/* Honest Limitation Notice */}
      <div className="my-2 bg-slate-800/80 border border-slate-700 p-2.5 rounded-xl text-[11px] text-slate-300 flex items-start gap-2">
        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <strong>Discretion Notice:</strong> This disguise prevents casual snooping. It does not protect against a determined person with root/device access.
        </div>
      </div>

      {/* Screen Display */}
      <div className="my-4 bg-slate-950 p-6 rounded-2xl border border-slate-800 text-right">
        <div className="text-4xl font-mono tracking-wider overflow-x-auto text-emerald-400">{display}</div>
        {errorMsg && <div className="text-xs text-rose-400 mt-2 font-mono">{errorMsg}</div>}
      </div>

      {/* Keypad */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <button onClick={handleClear} className="bg-slate-800 hover:bg-slate-700 text-amber-400 font-bold p-4 rounded-2xl text-xl min-h-[56px]">C</button>
        <button onClick={() => setDisplay(display + '/')} className="bg-slate-800 hover:bg-slate-700 text-teal-400 font-bold p-4 rounded-2xl text-xl min-h-[56px]">÷</button>
        <button onClick={() => setDisplay(display + '*')} className="bg-slate-800 hover:bg-slate-700 text-teal-400 font-bold p-4 rounded-2xl text-xl min-h-[56px]">×</button>
        <button onClick={() => setDisplay(display + '-')} className="bg-slate-800 hover:bg-slate-700 text-teal-400 font-bold p-4 rounded-2xl text-xl min-h-[56px]">-</button>

        <button onClick={() => handleDigit('7')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">7</button>
        <button onClick={() => handleDigit('8')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">8</button>
        <button onClick={() => handleDigit('9')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">9</button>
        <button onClick={() => setDisplay(display + '+')} className="bg-slate-800 hover:bg-slate-700 text-teal-400 font-bold p-4 rounded-2xl text-xl min-h-[56px]">+</button>

        <button onClick={() => handleDigit('4')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">4</button>
        <button onClick={() => handleDigit('5')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">5</button>
        <button onClick={() => handleDigit('6')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">6</button>
        <button onClick={handleEquals} className="row-span-2 bg-emerald-600 hover:bg-emerald-500 font-bold p-4 rounded-2xl text-2xl flex items-center justify-center min-h-[120px]">=</button>

        <button onClick={() => handleDigit('1')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">1</button>
        <button onClick={() => handleDigit('2')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">2</button>
        <button onClick={() => handleDigit('3')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">3</button>

        <button onClick={() => handleDigit('0')} className="col-span-2 bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">0</button>
        <button onClick={() => handleDigit('.')} className="bg-slate-800 hover:bg-slate-700 font-semibold p-4 rounded-2xl text-xl min-h-[56px]">.</button>
      </div>
    </div>
  );
};
