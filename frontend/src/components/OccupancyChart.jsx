import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts'

export function DailyOccupancyChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-500 text-center py-8">Sin datos disponibles</p>
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-bold text-gray-800 mb-4">Ocupación Diaria</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip formatter={(value) => `${value}%`} />
          <Legend />
          <Line
            type="monotone"
            dataKey="occupancy_percent"
            stroke="#3b82f6"
            name="Ocupación %"
            dot={{ fill: '#3b82f6' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function WeeklyRequestsChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-500 text-center py-8">Sin datos disponibles</p>
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-bold text-gray-800 mb-4">Solicitudes Semanales</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="week" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="available" fill="#10b981" name="Disponibles" />
          <Bar dataKey="taken" fill="#3b82f6" name="Tomados" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
