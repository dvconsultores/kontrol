import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MfaQrImage } from "./MfaQrImage";

const validSvgDataUri = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'><rect width='100' height='100'/></svg>";

describe("MfaQrImage", () => {
  it("no contiene APIs de inserción de HTML ni elementos embebibles", () => {
    const source = readFileSync(resolve(__dirname, "MfaQrImage.tsx"), "utf8");
    expect(source).not.toContain("dangerouslySetInnerHTML");
    expect(source).not.toContain("innerHTML");
    expect(source).not.toContain("<object");
    expect(source).not.toContain("<iframe");
    expect(source).not.toContain("<embed");
  });

  it("pinta img con data URI de svg válido", () => {
    render(<MfaQrImage dataUri={validSvgDataUri} />);
    const img = screen.getByAltText(/Código QR para su aplicación/i);
    expect(img.tagName).toBe("IMG");
    expect(img).toHaveAttribute("src", validSvgDataUri);
    expect(img).toHaveAttribute("width", "192");
    expect(img).toHaveAttribute("height", "192");
  });

  it.each(["javascript:alert(1)", "<svg onload=alert(1)>", "data:image/png;base64,abc", ""])(
    "no pinta img para %s y muestra alternativa",
    (dangerousValue) => {
      render(<MfaQrImage dataUri={dangerousValue} />);
      expect(screen.queryByRole("img")).not.toBeInTheDocument();
      expect(screen.getByText("No se pudo mostrar el código QR; use la clave manual")).toBeInTheDocument();
    },
  );
});

// La seguridad es estructural: MfaQrImage solo usa <img> y valida el prefijo.
// No hay inyección de marcado en tiempo de ejecución.
