import { useState } from "react";
import { Delete } from "lucide-react";

interface Props {
  title: string;
  subtitle?: string;
  onSubmit: (pin: string) => Promise<boolean>;
  pinLength?: number;
}

export default function PinPad({ title, subtitle, onSubmit, pinLength = 4 }: Props) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleDigit = async (digit: string) => {
    if (loading) return;
    setError(false);
    const next = pin + digit;
    setPin(next);

    if (next.length >= pinLength) {
      setLoading(true);
      const ok = await onSubmit(next);
      if (!ok) {
        setError(true);
        setPin("");
      }
      setLoading(false);
    }
  };

  const handleDelete = () => {
    setError(false);
    setPin((p) => p.slice(0, -1));
  };

  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "del", "0", ""];

  return (
    <div className="flex flex-col items-center">
      <h1 className="mb-2 text-xl font-bold">{title}</h1>
      {subtitle && (
        <p className="mb-6 text-sm text-text-secondary">{subtitle}</p>
      )}

      {/* Dots */}
      <div className="mb-8 flex gap-3">
        {Array.from({ length: pinLength }).map((_, i) => (
          <div
            key={i}
            className={`h-3 w-3 rounded-full transition-colors ${
              i < pin.length
                ? error
                  ? "bg-error"
                  : "bg-accent"
                : "bg-border-default"
            }`}
          />
        ))}
      </div>

      {error && (
        <p className="mb-4 text-sm text-error">PIN incorrecto</p>
      )}

      {/* Keypad */}
      <div className="grid grid-cols-3 gap-3">
        {keys.map((key, i) => {
          if (key === "") return <div key={i} />;
          if (key === "del") {
            return (
              <button
                key={i}
                onClick={handleDelete}
                className="flex h-16 w-16 items-center justify-center rounded-xl text-text-secondary hover:bg-bg-surface-hover"
              >
                <Delete size={20} />
              </button>
            );
          }
          return (
            <button
              key={i}
              onClick={() => handleDigit(key)}
              disabled={loading}
              className="flex h-16 w-16 items-center justify-center rounded-xl bg-bg-surface text-xl font-medium transition-colors hover:bg-bg-surface-hover active:bg-accent active:text-bg-primary disabled:opacity-50"
            >
              {key}
            </button>
          );
        })}
      </div>
    </div>
  );
}
