import { Providers } from './providers';
import { BootstrapGate } from '@/features/bootstrap/BootstrapGate';
import { AppShell } from '@/components/ui/AppShell';
import { AppRouter } from './router';

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

export default App;
