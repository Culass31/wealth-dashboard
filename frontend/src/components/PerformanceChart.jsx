import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Paper, Typography, Box } from '@mui/material';

const PerformanceChart = ({ data }) => {
  if (!data || data.length === 0) {
    return <Typography>No data available for performance chart.</Typography>;
  }

  // Recharts expects data in an array of objects, where each object represents a point on the chart
  // and keys correspond to data keys (e.g., 'date', 'patrimoine', 'benchmark').
  // The API returns data as dictionaries with date strings as keys.
  // We need to transform it.
  const transformedData = Object.keys(data.patrimoine_total_evolution).map(date => ({
    date,
    patrimoine: data.patrimoine_total_evolution[date],
    benchmark: data.benchmark[date],
  })).sort((a, b) => new Date(a.date) - new Date(b.date)); // Sort by date

  return (
    <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 400 }}>
      <Typography variant="h6" gutterBottom>
        Performance vs. Benchmark
      </Typography>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={transformedData}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="patrimoine" stroke="#8884d8" activeDot={{ r: 8 }} name="Patrimoine" />
          <Line type="monotone" dataKey="benchmark" stroke="#82ca9d" name="Benchmark (CW8.PA)" />
        </LineChart>
      </ResponsiveContainer>
    </Paper>
  );
};

export default PerformanceChart;
