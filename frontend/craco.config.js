/**
 * CRACO devServer override to avoid hard-coded proxy port.
 * Proxies unknown requests to process.env.REACT_APP_API_URL.
 */
module.exports = {
  devServer: (devServerConfig) => {
    const target = process.env.REACT_APP_API_URL;
    if (!target) {
      throw new Error('REACT_APP_API_URL must be set (e.g., http://localhost:<BACKEND_HOST_PORT>)');
    }
    devServerConfig.proxy = {
      '/': {
        target,
        changeOrigin: true,
        secure: false,
      },
    };
    return devServerConfig;
  },
};
