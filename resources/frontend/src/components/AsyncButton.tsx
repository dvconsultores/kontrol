/**
 * AsyncButton — acción asíncrona con loader dentro del botón (FR-003/004/005/006).
 * Deshabilita y previene doble envío; muestra texto de progreso; conserva ancho.
 * Nunca abre un segundo modal de carga (FR-007).
 */
import { Loader2 } from "lucide-react";
import { type ReactNode, useState } from "react";

import { Button, type ButtonProps } from "./Button";

export interface AsyncButtonProps extends Omit<ButtonProps, "onClick" | "disabled"> {
  onClick: () => Promise<void>;
  loadingText?: string;
  idleText?: ReactNode;
  /** Evita que el botón quede activo mientras se ejecuta la misma acción. */
  disabled?: boolean;
}

export function AsyncButton({
  onClick,
  loadingText,
  idleText,
  disabled,
  children,
  ...props
}: AsyncButtonProps): React.JSX.Element {
  const [loading, setLoading] = useState(false);

  const handleClick = async (): Promise<void> => {
    if (loading || disabled) {
      return;
    }
    setLoading(true);
    try {
      await onClick();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button {...props} onClick={handleClick} disabled={disabled || loading} aria-busy={loading}>
      {loading ? (
        <>
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          <span>{loadingText ?? "Procesando…"}</span>
        </>
      ) : (
        <span>{idleText ?? children}</span>
      )}
    </Button>
  );
}
