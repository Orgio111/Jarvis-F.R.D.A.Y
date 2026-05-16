# Frontend security notes

## Applied npm overrides

`package.json` pins the following to patched releases via `overrides`:

| Package | Forced version | Reason |
|---|---|---|
| `dompurify` | `^3.4.2` | Patches 8 XSS / prototype-pollution advisories in `<= 3.3.3` that monaco-editor would otherwise pull in. |
| `esbuild` | `^0.25.0` | Patches GHSA-67mh-4wv8-2f99 (dev-server CORS read) in `<= 0.24.2`. |

## Deferred advisories

| Advisory | Affects | Decision | Revisit when |
|---|---|---|---|
| GHSA-4w7w-66w2-5vf9 | Vite `<= 6.4.1` — dev-server `.map` path traversal | Defer | Upgrading to Vite 6 LTS |

**Risk profile**: this is a dev-server-only vulnerability. It can be exploited only if a malicious origin is visited *while* `vite dev` is running locally. Production builds and `vite preview` are unaffected. The fix path (Vite 5 → 8) is a breaking change requiring Node 20+, plugin API migration, and a lockstep vitest bump — deferred until the next major Vite migration window.
