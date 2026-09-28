import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  assertNoCycleData,
  secureFetch,
  getNetworkMetrics,
  resetNetworkMetrics,
} from './netClient';

describe('netClient Privacy & Byte Counter Tests', () => {
  beforeEach(() => {
    resetNetworkMetrics();
    vi.restoreAllMocks();
  });

  it('allows content request payloads without sensitive cycle log data', () => {
    const safePayload = JSON.stringify({ lang: 'en', topic: 'myths' });
    expect(() => assertNoCycleData(safePayload)).not.toThrow();
  });

  it('blocks and throws error if payload contains forbidden cycle log fields', () => {
    const unsafePayload = JSON.stringify({
      start_date: '2026-05-01',
      cycle_length: 28,
      flow_intensity: 2,
    });

    expect(() => assertNoCycleData(unsafePayload)).toThrow(
      /PRIVACY VIOLATION DETECTED/
    );
  });

  it('accurately counts bytes sent and tracks zero user log bytes', async () => {
    const metricsBefore = getNetworkMetrics();
    expect(metricsBefore.userLogBytesSent).toBe(0);

    // Mock global fetch to avoid ENOTFOUND in offline test runner
    global.fetch = vi.fn().mockResolvedValue(new Response('OK', { status: 200 }));

    await secureFetch('/content/en/messages.json', {
      method: 'GET',
    });

    const metricsAfter = getNetworkMetrics();
    expect(metricsAfter.userLogBytesSent).toBe(0);
    expect(metricsAfter.requestCount).toBe(1);
  });
});
