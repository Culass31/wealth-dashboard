import React from 'react';
import { Typography, Grid, CircularProgress, Box } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { getGlobalKpis, getChartsData } from '../services/api';
import KpiCard from '../components/KpiCard';
import PerformanceChart from '../components/PerformanceChart';
import InvestmentsTable from '../components/InvestmentsTable';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import PercentIcon from '@mui/icons-material/Percent';

const DashboardPage = () => {
  const { data: globalKpis, isLoading: isLoadingKpis, error: errorKpis } = useQuery({
    queryKey: ['globalKpis'],
    queryFn: getGlobalKpis,
  });

  const { data: chartsData, isLoading: isLoadingCharts, error: errorCharts } = useQuery({
    queryKey: ['chartsData'],
    queryFn: getChartsData,
  });

  if (isLoadingKpis || isLoadingCharts) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (errorKpis) {
    return <Typography color="error">Error loading global KPIs: {errorKpis.message}</Typography>;
  }

  if (errorCharts) {
    return <Typography color="error">Error loading charts data: {errorCharts.message}</Typography>;
  }

  return (
    <>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Patrimoine Total"
            value={`${globalKpis.patrimoine_total.toFixed(2)} €`}
            icon={<AccountBalanceWalletIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Plus-value Nette"
            value={`${globalKpis.plus_value_nette.toFixed(2)} €`}
            icon={<TrendingUpIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Total Apports"
            value={`${globalKpis.total_apports.toFixed(2)} €`}
            icon={<AttachMoneyIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="TRI Global Net"
            value={`${globalKpis.tri_global_net.toFixed(2)} %`}
            icon={<PercentIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Indice Herfindahl"
            value={`${globalKpis.herfindahl_index.toFixed(2)}`}
            icon={<PercentIcon />}
          />
        </Grid>
        <Grid item xs={12}>
          <PerformanceChart data={chartsData.evolution_data} />
        </Grid>
        <Grid item xs={12}>
          <InvestmentsTable />
        </Grid>
      </Grid>
    </>
  );
};

export default DashboardPage;