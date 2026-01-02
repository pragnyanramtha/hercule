import '@testing-library/jest-dom/vitest';
import { vi, beforeEach } from 'vitest';

// Mock chrome API for extension testing
const mockChrome = {
  tabs: {
    query: vi.fn(),
    sendMessage: vi.fn(),
  },
  runtime: {
    onMessage: {
      addListener: vi.fn(),
      removeListener: vi.fn(),
    },
    sendMessage: vi.fn(),
  },
  storage: {
    local: {
      get: vi.fn(),
      set: vi.fn(),
    },
  },
  scripting: {
    executeScript: vi.fn(),
  },
};

// @ts-expect-error - mock chrome global
globalThis.chrome = mockChrome;

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
});
