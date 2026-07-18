// @ts-check
import { defineConfig } from 'astro/config';

import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  // Dev server port: 4321 (Vite dashboard uses 5173, FastAPI uses 8000)
  server: { port: 4321 },

  integrations: [react()],

  vite: {
    plugins: [tailwindcss()],
  },
});