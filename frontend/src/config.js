// AWS configuration — values injected from .env at build time by Vite.
// Fill in .env (copy from .env.example) before running npm run dev or npm run build.

const config = {
  Auth: {
    Cognito: {
      userPoolId:       import.meta.env.VITE_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
      loginWith: {
        email: true,
      },
    },
  },
}

export const API_URL = import.meta.env.VITE_API_URL

export default config
