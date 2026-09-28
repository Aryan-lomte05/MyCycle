import Dexie, { type Table } from 'dexie';

export interface CycleRecord {
  id: string;
  start_date: string; // YYYY-MM-DD
  cycle_length: number; // days
  flow_intensity: number; // 1-4 scale
  pain_score: number; // 0-10 scale
  symptoms: string[];
  created_at: string;
}

export interface UserSettings {
  id: string; // 'current'
  language: 'en' | 'hi' | 'mr';
  role: 'self' | 'partner' | 'parent' | 'sibling';
  privacy_accepted: boolean;
  disguise_pin_hash?: string;
  disguise_enabled?: boolean;
  active_persona_id?: string;
}

export interface FlagRecord {
  id: string;
  cycle_id: string;
  flag_type: string;
  contributing_signals: string[];
  created_at: string;
}

export class MyCycleDatabase extends Dexie {
  cycles!: Table<CycleRecord>;
  settings!: Table<UserSettings>;
  flags!: Table<FlagRecord>;

  constructor() {
    super('MyCycleDB');
    this.version(1).stores({
      cycles: 'id, start_date, cycle_length',
      settings: 'id',
      flags: 'id, cycle_id, flag_type',
    });
  }
}

export const db = new MyCycleDatabase();

// Initializer helper
export async function ensureUserSettings(): Promise<UserSettings> {
  const existing = await db.settings.get('current');
  if (existing) return existing;

  const defaultSettings: UserSettings = {
    id: 'current',
    language: 'en',
    role: 'self',
    privacy_accepted: false,
    disguise_enabled: false,
  };

  await db.settings.put(defaultSettings);
  return defaultSettings;
}
