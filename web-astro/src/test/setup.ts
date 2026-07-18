import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

vi.mock('@clerk/astro/react', () => ({
  useAuth: () => ({
    isLoaded: true,
    isSignedIn: true,
    sessionId: 'sess_test',
    userId: 'user_test',
    getToken: vi.fn().mockResolvedValue('mock-jwt-token'),
  }),
}));
