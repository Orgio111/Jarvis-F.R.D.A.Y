import React from 'react';
import ReactDOM from 'react-dom/client';
import { Providers } from './providers';
import { BootstrapGate } from '@/features/bootstrap/BootstrapGate';
import { AppShell } from '@/components/ui/AppShell';
import { AppRouter } from './router';
import '@/styles/globals.css';

function App() {
  return (
    <Providers>
      {/*
        BootstrapGate: blocks all feature rendering until /api/bootstrap succeeds.
        Shows animated loader while bootstrapping.
        Shows RecoveryScreen on persistent failure with retry.
      */}
      <BootstrapGate>
        <AppShell>
          <AppRouter />
        </AppShell>
      </BootstrapGate>
    </Providers>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

export default App;
