// 注册离线缓存用的 service worker。sw.js 放在站点根目录，按本脚本的位置推算它的地址，
// 这样在 GitHub Pages 的 /MHR/ 子路径和 Cloudflare 的根路径下都能用。
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register(new URL("../../sw.js", document.currentScript.src));
}
