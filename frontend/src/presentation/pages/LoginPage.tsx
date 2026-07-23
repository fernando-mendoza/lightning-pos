import { useAuth } from "../../application/hooks/useAuth";
import PinPad from "../components/PinPad";
import BrandingFooter from "../components/BrandingFooter";

interface Props {
  onAuthenticated: () => void;
}

export default function LoginPage({ onAuthenticated }: Props) {
  const { pinSet, loading, login, setupPin } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg-primary">
        <p className="text-text-secondary">Cargando...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-bg-primary">
      {pinSet ? (
        <PinPad
          title="Lightning POS"
          subtitle="Ingresa tu PIN"
          onSubmit={async (pin) => {
            const ok = await login(pin);
            if (ok) onAuthenticated();
            return ok;
          }}
        />
      ) : (
        <PinPad
          title="Lightning POS"
          subtitle="Configura tu PIN de acceso"
          onSubmit={async (pin) => {
            const ok = await setupPin(pin);
            if (ok) onAuthenticated();
            return ok;
          }}
        />
      )}
      <a
        href="/demo"
        className="mt-6 text-xs text-text-secondary underline-offset-4 hover:text-text-primary hover:underline"
      >
        Ver demostración
      </a>
      <BrandingFooter />
    </div>
  );
}
