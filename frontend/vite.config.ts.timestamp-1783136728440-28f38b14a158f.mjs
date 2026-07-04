// vite.config.ts
import { defineConfig, loadEnv } from "file:///D:/code/live_calc/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/code/live_calc/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import vuetify from "file:///D:/code/live_calc/frontend/node_modules/vite-plugin-vuetify/dist/index.mjs";
var vite_config_default = defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const allowedHostsEnv = env.VITE_ALLOWED_HOSTS || "localhost,127.0.0.1,::1";
  const allowedHostsArray = allowedHostsEnv.split(",").map((host) => host.trim());
  console.log("Allowed hosts:", allowedHostsArray);
  return {
    plugins: [
      vue(),
      vuetify({ autoImport: true })
      // eruda(),
    ],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true
        }
      },
      allowedHosts: [
        ...allowedHostsArray
      ]
    },
    resolve: {
      alias: {
        "@": "/src"
      }
    }
  };
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxjb2RlXFxcXGxpdmVfY2FsY1xcXFxmcm9udGVuZFwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiRDpcXFxcY29kZVxcXFxsaXZlX2NhbGNcXFxcZnJvbnRlbmRcXFxcdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Q6L2NvZGUvbGl2ZV9jYWxjL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnLCBsb2FkRW52IH0gZnJvbSAndml0ZSdcclxuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXHJcbmltcG9ydCB2dWV0aWZ5IGZyb20gJ3ZpdGUtcGx1Z2luLXZ1ZXRpZnknXHJcbi8vIGltcG9ydCBlcnVkYSBmcm9tICd2aXRlLXBsdWdpbi1lcnVkYSdcclxuXHJcbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZygoeyBtb2RlIH0pID0+IHtcclxuICAvLyBcdTUyQTBcdThGN0RcdTczQUZcdTU4ODNcdTUzRDhcdTkxQ0ZcclxuICBjb25zdCBlbnYgPSBsb2FkRW52KG1vZGUsIHByb2Nlc3MuY3dkKCksICcnKVxyXG5cclxuICAvLyBcdThCRkJcdTUzRDZcdTczQUZcdTU4ODNcdTUzRDhcdTkxQ0ZcdTY3NjVcdTkxNERcdTdGNkVcdTUxNDFcdThCQjhcdTc2ODRcdTRFM0JcdTY3M0FcclxuICBjb25zdCBhbGxvd2VkSG9zdHNFbnYgPSBlbnYuVklURV9BTExPV0VEX0hPU1RTIHx8ICdsb2NhbGhvc3QsMTI3LjAuMC4xLDo6MSdcclxuICBjb25zdCBhbGxvd2VkSG9zdHNBcnJheSA9IGFsbG93ZWRIb3N0c0Vudi5zcGxpdCgnLCcpLm1hcChob3N0ID0+IGhvc3QudHJpbSgpKVxyXG5cclxuICBjb25zb2xlLmxvZygnQWxsb3dlZCBob3N0czonLCBhbGxvd2VkSG9zdHNBcnJheSkgLy8gXHU4QzAzXHU4QkQ1XHU0RkUxXHU2MDZGXHJcblxyXG4gIHJldHVybiB7XHJcbiAgcGx1Z2luczogW1xyXG4gICAgdnVlKCksXHJcbiAgICB2dWV0aWZ5KHsgYXV0b0ltcG9ydDogdHJ1ZSB9KSxcclxuICAgIC8vIGVydWRhKCksXHJcbiAgXSxcclxuICBzZXJ2ZXI6IHtcclxuICAgIGhvc3Q6ICcwLjAuMC4wJyxcclxuICAgIHBvcnQ6IDUxNzMsXHJcbiAgICBwcm94eToge1xyXG4gICAgICAnL2FwaSc6IHtcclxuICAgICAgICB0YXJnZXQ6ICdodHRwOi8vbG9jYWxob3N0OjgwMDAnLFxyXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgICBhbGxvd2VkSG9zdHM6IFtcclxuICAgICAgLi4uYWxsb3dlZEhvc3RzQXJyYXlcclxuICAgIF1cclxuICB9LFxyXG4gIHJlc29sdmU6IHtcclxuICAgIGFsaWFzOiB7XHJcbiAgICAgICdAJzogJy9zcmMnLFxyXG4gICAgfSxcclxuICB9LFxyXG4gIH1cclxufSlcclxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUF3USxTQUFTLGNBQWMsZUFBZTtBQUM5UyxPQUFPLFNBQVM7QUFDaEIsT0FBTyxhQUFhO0FBR3BCLElBQU8sc0JBQVEsYUFBYSxDQUFDLEVBQUUsS0FBSyxNQUFNO0FBRXhDLFFBQU0sTUFBTSxRQUFRLE1BQU0sUUFBUSxJQUFJLEdBQUcsRUFBRTtBQUczQyxRQUFNLGtCQUFrQixJQUFJLHNCQUFzQjtBQUNsRCxRQUFNLG9CQUFvQixnQkFBZ0IsTUFBTSxHQUFHLEVBQUUsSUFBSSxVQUFRLEtBQUssS0FBSyxDQUFDO0FBRTVFLFVBQVEsSUFBSSxrQkFBa0IsaUJBQWlCO0FBRS9DLFNBQU87QUFBQSxJQUNQLFNBQVM7QUFBQSxNQUNQLElBQUk7QUFBQSxNQUNKLFFBQVEsRUFBRSxZQUFZLEtBQUssQ0FBQztBQUFBO0FBQUEsSUFFOUI7QUFBQSxJQUNBLFFBQVE7QUFBQSxNQUNOLE1BQU07QUFBQSxNQUNOLE1BQU07QUFBQSxNQUNOLE9BQU87QUFBQSxRQUNMLFFBQVE7QUFBQSxVQUNOLFFBQVE7QUFBQSxVQUNSLGNBQWM7QUFBQSxRQUNoQjtBQUFBLE1BQ0Y7QUFBQSxNQUNBLGNBQWM7QUFBQSxRQUNaLEdBQUc7QUFBQSxNQUNMO0FBQUEsSUFDRjtBQUFBLElBQ0EsU0FBUztBQUFBLE1BQ1AsT0FBTztBQUFBLFFBQ0wsS0FBSztBQUFBLE1BQ1A7QUFBQSxJQUNGO0FBQUEsRUFDQTtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
