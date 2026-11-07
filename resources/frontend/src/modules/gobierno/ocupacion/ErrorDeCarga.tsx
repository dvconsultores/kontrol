import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";

export function ErrorDeCarga({ message, onRetry }: { message: string; onRetry?: () => void }): React.JSX.Element {
  return (
    <EmptyState
      title="No fue posible cargar"
      description={message}
      action={
        onRetry ? (
          <Button variant="secondary" onClick={onRetry}>
            Reintentar
          </Button>
        ) : undefined
      }
    />
  );
}
