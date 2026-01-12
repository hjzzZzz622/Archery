import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "node:path";

// 方案 A：新旧并存
// - 页面入口：/ui/...
// - 静态资源：/static/ui/...
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  base: "/static/ui/",
  build: {
    outDir: resolve(__dirname, "../common/static/ui"),
    emptyOutDir: true,
  },
});

