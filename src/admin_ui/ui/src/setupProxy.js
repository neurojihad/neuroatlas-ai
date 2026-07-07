const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function (app) {
  app.use(
    createProxyMiddleware(["/api", "/guard"], {
      target: process.env.REACT_APP_ADMIN_URL || "http://localhost:8000",
      changeOrigin: true,
    }),
  );
};
