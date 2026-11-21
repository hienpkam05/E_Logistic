import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config.js'

// Dùng chung cấu hình Vite (plugin Vue, env) để test chạy giống ứng dụng thật.
export default defineConfig((env) =>
  mergeConfig(viteConfig(env), {
    test: {
      environment: 'jsdom',
      include: ['src/**/*.spec.js'],
      restoreMocks: true,
      unstubGlobals: true,
    },
  }),
)
