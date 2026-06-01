/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  Telegram?: {
    WebApp: {
      ready: () => void
      expand: () => void
      close: () => void
      MainButton: {
        text: string
        show: () => void
        hide: () => void
        onClick: (callback: () => void) => void
      }
    }
  }
}
