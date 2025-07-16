import React, { useState } from 'react';
import { Paper, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, Typography, Box, CircularProgress, TextField, MenuItem } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { getInvestments } from '../services/api';

const InvestmentsTable = () => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [platformFilter, setPlatformFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data: investments, isLoading, error } = useQuery({
    queryKey: ['investments', { platform: platformFilter, status: statusFilter }],
    queryFn: () => getInvestments({ platform: platformFilter, status: statusFilter }),
  });

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handlePlatformFilterChange = (event) => {
    setPlatformFilter(event.target.value);
    setPage(0);
  };

  const handleStatusFilterChange = (event) => {
    setStatusFilter(event.target.value);
    setPage(0);
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Typography color="error">Error loading investments: {error.message}</Typography>;
  }

  const emptyRows = rowsPerPage - Math.min(rowsPerPage, investments.length - page * rowsPerPage);

  // Extract unique platforms and statuses for filters
  const uniquePlatforms = [...new Set(investments.map(inv => inv.platform))];
  const uniqueStatuses = [...new Set(investments.map(inv => inv.status))];

  return (
    <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" gutterBottom>
        Investments
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField
          select
          label="Filter by Platform"
          value={platformFilter}
          onChange={handlePlatformFilterChange}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All Platforms</MenuItem>
          {uniquePlatforms.map((platform) => (
            <MenuItem key={platform} value={platform}>
              {platform}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Filter by Status"
          value={statusFilter}
          onChange={handleStatusFilterChange}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All Statuses</MenuItem>
          {uniqueStatuses.map((status) => (
            <MenuItem key={status} value={status}>
              {status}
            </MenuItem>
          ))}
        </TextField>
      </Box>
      <TableContainer>
        <Table stickyHeader aria-label="investments table">
          <TableHead>
            <TableRow>
              <TableCell>Platform</TableCell>
              <TableCell>Project Name</TableCell>
              <TableCell align="right">Invested Amount</TableCell>
              <TableCell align="right">Remaining Capital</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Investment Date</TableCell>
              <TableCell>Expected End Date</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(rowsPerPage > 0
              ? investments.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              : investments
            ).map((row) => (
              <TableRow key={row.id}>
                <TableCell component="th" scope="row">
                  {row.platform}
                </TableCell>
                <TableCell>{row.project_name}</TableCell>
                <TableCell align="right">{row.invested_amount ? parseFloat(row.invested_amount).toFixed(2) : 'N/A'} €</TableCell>
                <TableCell align="right">{row.remaining_capital ? parseFloat(row.remaining_capital).toFixed(2) : 'N/A'} €</TableCell>
                <TableCell>{row.status}</TableCell>
                <TableCell>{row.investment_date}</TableCell>
                <TableCell>{row.expected_end_date}</TableCell>
              </TableRow>
            ))}
            {emptyRows > 0 && (
              <TableRow style={{ height: 53 * emptyRows }}>
                <TableCell colSpan={7} />
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        rowsPerPageOptions={[5, 10, 25]}
        component="div"
        count={investments.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
    </Paper>
  );
};

export default InvestmentsTable;
