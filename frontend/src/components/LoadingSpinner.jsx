export default function LoadingSpinner({ size = 'md' }) {
  const sizeClasses = {
    sm: 'h-6 w-6 border-2',
    md: 'h-12 w-12 border-4',
    lg: 'h-16 w-16 border-4'
  }

  return (
    <div className="flex justify-center items-center">
      <div 
        className={`animate-spin rounded-full border-primary-600 border-t-transparent ${sizeClasses[size]}`}
        role="status"
        aria-label="Cargando"
      >
        <span className="sr-only">Cargando...</span>
      </div>
    </div>
  )
}
