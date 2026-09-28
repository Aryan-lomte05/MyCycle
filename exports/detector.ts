export interface CycleLog {
  id: string;
  start_date: string;
  cycle_length: number; // days
  flow_intensity: number; // 1-4 scale
  pain_score: number; // 0-10 scale
  symptoms: string[];
}

export interface DetectorResult {
  flag_type: 'flag_cycle_length_anomaly' | 'flag_pain_spike' | 'flag_flow_change' | 'flag_irregular_pattern' | null;
  confidence: number;
  contributing_signals: string[];
  inference_time_ms: number;
  tier_used: 'Tier 1 Baseline' | 'Tier 2 ONNX GRU (Fallback to T1)';
}

export function runTier1Detector(cycles: CycleLog[]): DetectorResult {
  const startTime = performance.now();

  if (!cycles || cycles.length < 2) {
    return {
      flag_type: null,
      confidence: 0,
      contributing_signals: ['Insufficient historical cycles logged to establish baseline.'],
      inference_time_ms: Math.round((performance.now() - startTime) * 100) / 100,
      tier_used: 'Tier 1 Baseline',
    };
  }

  const latest = cycles[cycles.length - 1];
  const history = cycles.slice(0, cycles.length - 1);

  // Baseline cycle length stats
  const lengths = history.map((c) => c.cycle_length);
  const meanLength = lengths.reduce((a, b) => a + b, 0) / lengths.length;
  const variance = lengths.reduce((a, b) => a + Math.pow(b - meanLength, 2), 0) / lengths.length;
  const stdDev = Math.sqrt(variance);

  let flag_type: DetectorResult['flag_type'] = null;
  const contributing_signals: string[] = [];
  let confidence = 0.85;

  // 1. Pain spike check
  if (latest.pain_score >= 7) {
    flag_type = 'flag_pain_spike';
    contributing_signals.push(`Pain score reached ${latest.pain_score}/10, exceeding baseline average.`);
    if (latest.symptoms.includes('cramps') || latest.symptoms.includes('backache')) {
      contributing_signals.push(`Severe associated symptoms reported: ${latest.symptoms.join(', ')}.`);
    }
    confidence = 0.92;
  }
  // 2. Cycle length anomaly check
  else if (Math.abs(latest.cycle_length - meanLength) > Math.max(5, 2 * stdDev)) {
    flag_type = 'flag_cycle_length_anomaly';
    contributing_signals.push(
      `Latest cycle length (${latest.cycle_length} days) deviates significantly from your baseline average (${Math.round(meanLength)} ± ${Math.round(stdDev * 10) / 10} days).`
    );
    confidence = 0.88;
  }
  // 3. Flow volume change check
  else if (latest.flow_intensity >= 4) {
    flag_type = 'flag_flow_change';
    contributing_signals.push(`Flow intensity reached maximum level (${latest.flow_intensity}/4).`);
    confidence = 0.86;
  }
  // 4. Irregularity check
  else if (stdDev >= 6) {
    flag_type = 'flag_irregular_pattern';
    contributing_signals.push(`High historical cycle length variance (standard deviation: ${Math.round(stdDev * 10) / 10} days).`);
    confidence = 0.84;
  }

  const endTime = performance.now();
  const inference_time_ms = Math.round((endTime - startTime) * 100) / 100;

  return {
    flag_type,
    confidence,
    contributing_signals,
    inference_time_ms,
    tier_used: 'Tier 1 Baseline',
  };
}
