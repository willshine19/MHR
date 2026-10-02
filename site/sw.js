// 离线缓存。安装时把全站文件存进缓存；之后每次请求都先走网络，并用结果更新缓存，
// 网络 3 秒内没有响应或断网时改用缓存，所以联网时看到的总是最新内容。
//
// site/ 下增删文件后要同步改 PRECACHE（路径相对站点根目录），check_site.py 会检查两边是否一致。
// 本文件内容一变，浏览器就会装上新版本，安装时把 PRECACHE 全部重新下载一遍。
// VERSION 由 CI 在每次部署时换成提交号，保证每次部署后已安装的应用都会把全站刷新到最新，
// 包括没有联网打开过的页面。这一行不要改，check_site.py 会检查。

const VERSION = "dev";
const CACHE = "mhr";
const NETWORK_TIMEOUT_MS = 3000;

const PRECACHE = [
  "index.html",
  "about.html",
  "404.html",
  "builds/index.html",
  "builds/lance-mr2.html",
  "builds/lance-mr3.html",
  "builds/bow-mr3.html",
  "monsters/index.html",
  "monsters/almudron.html",
  "monsters/astalos.html",
  "monsters/aurora-somnacanth.html",
  "monsters/barioth.html",
  "monsters/diablos.html",
  "monsters/espinas.html",
  "monsters/garangolm.html",
  "monsters/gore-magala.html",
  "monsters/goss-harag.html",
  "monsters/lunagaron.html",
  "monsters/magma-almudron.html",
  "monsters/magnamalo.html",
  "monsters/mizutsune.html",
  "monsters/nargacuga.html",
  "monsters/pyre-rakna-kadaki.html",
  "monsters/rakna-kadaki.html",
  "monsters/rathalos.html",
  "monsters/seregios.html",
  "monsters/shogun-ceanataur.html",
  "monsters/tigrex.html",
  "monsters/zinogre.html",
  "assets/css/site.css",
  "assets/js/sw-register.js",
  "assets/icons/apple-touch-icon.png",
  "assets/icons/icon-192.png",
  "assets/icons/icon-512.png",
  "assets/icons/icon-maskable-512.png",
  "assets/img/monsters/almudron.webp",
  "assets/img/monsters/astalos.webp",
  "assets/img/monsters/aurora-somnacanth.webp",
  "assets/img/monsters/barioth.webp",
  "assets/img/monsters/diablos.webp",
  "assets/img/monsters/espinas.webp",
  "assets/img/monsters/garangolm.webp",
  "assets/img/monsters/gore-magala.webp",
  "assets/img/monsters/goss-harag.webp",
  "assets/img/monsters/lunagaron.webp",
  "assets/img/monsters/magma-almudron.webp",
  "assets/img/monsters/magnamalo.webp",
  "assets/img/monsters/mizutsune.webp",
  "assets/img/monsters/nargacuga.webp",
  "assets/img/monsters/pyre-rakna-kadaki.webp",
  "assets/img/monsters/rakna-kadaki.webp",
  "assets/img/monsters/rathalos.webp",
  "assets/img/monsters/seregios.webp",
  "assets/img/monsters/shogun-ceanataur.webp",
  "assets/img/monsters/tigrex.webp",
  "assets/img/monsters/zinogre.webp",
  "manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE.map((path) => new Request(path, { cache: "reload" }))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    // 删掉不在 PRECACHE 里的条目（已删除或改名的页面）；目录地址这类顺带缓存的条目，下次访问会再存
    const cache = await caches.open(CACHE);
    const keep = new Set(PRECACHE.map((path) => new URL(path, self.location).href));
    for (const request of await cache.keys()) {
      if (!keep.has(request.url)) await cache.delete(request);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(networkFirst(event));
});

async function networkFirst(event) {
  const request = event.request;
  const cache = await caches.open(CACHE);
  const network = fetch(request);
  // 即使先用缓存应答了，网络请求也会在后台跑完，把缓存更新到最新
  event.waitUntil(network.then(async (response) => {
    if (response.ok) await cache.put(request, response.clone());
  }).catch(() => {}));

  try {
    return await withTimeout(network, NETWORK_TIMEOUT_MS);
  } catch {
    const cached = await matchCache(cache, request);
    if (cached) return cached;
    if (request.mode === "navigate") {
      const notFound = await cache.match("404.html");
      if (notFound) return notFound;
    }
    return network; // 缓存里也没有：继续等网络，失败就照常报错
  }
}

// 以 / 结尾的地址（例如站点根目录）对应目录下的 index.html
async function matchCache(cache, request) {
  const cached = await cache.match(request, { ignoreSearch: true });
  if (cached) return cached;
  const url = new URL(request.url);
  if (url.pathname.endsWith("/")) return cache.match(new URL("index.html", url));
  return undefined;
}

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), ms);
    promise.then(
      (value) => { clearTimeout(timer); resolve(value); },
      (error) => { clearTimeout(timer); reject(error); },
    );
  });
}
