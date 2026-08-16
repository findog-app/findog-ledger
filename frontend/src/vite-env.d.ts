/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
}

interface Window {
  __FINDOG_LEDGER_CONFIG__?: {
    VITE_API_URL?: string
  }
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
