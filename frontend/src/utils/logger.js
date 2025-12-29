/**
 * Logger utility for frontend
 * In production, only errors are logged
 * In development, all logs are shown
 */

const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development'

const logger = {
  log: (...args) => {
    if (isDevelopment) {
      console.log('[LOG]', ...args)
    }
  },
  
  error: (...args) => {
    console.error('[ERROR]', ...args)
  },
  
  warn: (...args) => {
    if (isDevelopment) {
      console.warn('[WARN]', ...args)
    }
  },
  
  info: (...args) => {
    if (isDevelopment) {
      console.info('[INFO]', ...args)
    }
  }
}

export default logger

