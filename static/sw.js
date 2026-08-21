// Service worker mínimo — só existe para o Chrome/Android considerar o
// app "instalável" como PWA. Não faz cache nem funciona offline de
// propósito: os dados dos alunos são sempre ao vivo via Supabase, então
// uma versão desatualizada em cache faria mais mal do que bem aqui.

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
