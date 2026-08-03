/** ErrorBoundary — captura errores de renderizado de rutas/módulos (FR-029). */
import { Component, type ErrorInfo, type ReactNode } from "react";

import { ErrorState } from "./ErrorState";

interface Props {
  /** Contenido a proteger. Opcional para uso como errorElement del router. */
  children?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // En producción, enviar a observabilidad (sanitizado, sin secretos).
    console.error("ErrorBoundary capturó un error", error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <ErrorState
          title="Ocurrió un error inesperado"
          message="La operación no pudo completarse. Vuelva a intentar; si persiste, contacte a soporte."
          onRetry={() => this.setState({ error: null })}
        />
      );
    }
    return this.props.children;
  }
}
