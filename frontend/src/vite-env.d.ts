/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
}

interface Window {
  __OBLIDOG_CONFIG__?: {
    VITE_API_URL?: string
  }
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
