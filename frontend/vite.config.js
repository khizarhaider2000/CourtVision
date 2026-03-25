import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/health': { target: apiTarget, changeOrigin: true },
        '/seasons': { target: apiTarget, changeOrigin: true },
        '/ai': { target: apiTarget, changeOrigin: true },
        // /query is ALSO a React Router page (GET), so only proxy POST requests.
        // bypass() returning a string tells Vite to skip the proxy for that request.
        '/query': {
          target: apiTarget,
          changeOrigin: true,
          bypass(req) {
            if (req.method !== 'POST') return req.url;
          },
        },
        '/metrics': { target: apiTarget, changeOrigin: true },
      },
    },
  };
});
