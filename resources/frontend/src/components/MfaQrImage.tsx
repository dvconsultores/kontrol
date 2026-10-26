/** MfaQrImage — pinta SOLO el SVG del QR como imagen. */
export function MfaQrImage({ dataUri, alt }: { dataUri: string; alt?: string }): React.JSX.Element {
  const isValidSvgDataUri = dataUri.startsWith("data:image/svg+xml");
  const fallbackAlt =
    "Código QR para su aplicación de autenticación; si no puede usarlo, introduzca la clave manual";

  if (!isValidSvgDataUri) {
    return (
      <div className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-700">
        No se pudo mostrar el código QR; use la clave manual
      </div>
    );
  }

  return <img src={dataUri} alt={alt ?? fallbackAlt} width={192} height={192} className="mx-auto block" />;
}
