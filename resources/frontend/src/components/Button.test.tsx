import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "./Button";

describe("Button", () => {
  it("renderiza con texto", () => {
    render(<Button>Guardar</Button>);
    expect(screen.getByRole("button", { name: "Guardar" })).toBeInTheDocument();
  });

  it("respeta variante primary por defecto", () => {
    render(<Button>OK</Button>);
    const button = screen.getByRole("button", { name: "OK" });
    expect(button.className).toContain("bg-brand-600");
  });

  it("deshabilita cuando se indica", () => {
    render(<Button disabled>OK</Button>);
    expect(screen.getByRole("button", { name: "OK" })).toBeDisabled();
  });
});
