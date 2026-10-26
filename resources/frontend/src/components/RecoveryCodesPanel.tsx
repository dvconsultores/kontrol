/** RecoveryCodesPanel — muestra los códigos de recuperación y permite copiarlos o descargarlos. */
import { useRef, useState } from "react";

import { Button } from "@/components/Button";

export function RecoveryCodesPanel({ codes }: { codes: string[] }): React.JSX.Element {
  const downloadRef = useRef<HTMLAnchorElement>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  const handleDownload = (): void => {
    if (downloadRef.current) {
      downloadRef.current.href = "data:text/plain;charset=utf-8," + encodeURIComponent(codes.join("\n"));
      downloadRef.current.download = "kontrol-codigos-recuperacion.txt";
      downloadRef.current.click();
      downloadRef.current.href = "";
    }
  };

  const handleCopy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopyStatus("Códigos copiados");
    } catch {
      setCopyStatus("Copie los códigos manualmente");
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-sm text-text-700">Cada código sirve una sola vez. No volverá a verlos.</p>
      <ol className="space-y-1 rounded-md border border-border-default bg-surface-50 p-3">
        {codes.map((code) => (
          <li key={code} className="font-mono text-sm text-text-900">
            {code}
          </li>
        ))}
      </ol>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button variant="secondary" onClick={handleCopy}>
          Copiar códigos
        </Button>
        <Button variant="secondary" onClick={handleDownload}>
          Descargar .txt
        </Button>
      </div>
      {copyStatus ? (
        <p role="status" className="text-sm text-text-600">
          {copyStatus}
        </p>
      ) : null}
      {/** Enlace oculto para la descarga; no interfiere con el flujo visual. */}
      <a ref={downloadRef} className="hidden" aria-hidden="true" tabIndex={-1} />
    </div>
  );
}
