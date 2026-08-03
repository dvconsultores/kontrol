import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormField } from "./FormField";
import { TextInput } from "./TextInput";

describe("FormField", () => {
  it("asocia label, ayuda y error con aria (FR-009)", () => {
    render(
      <FormField label="RIF" required help="Identificador como texto" error="RIF inválido">
        <TextInput aria-invalid />
      </FormField>,
    );
    expect(screen.getByLabelText(/RIF/)).toBeInTheDocument();
    expect(screen.getByText("RIF inválido")).toBeInTheDocument();
    expect(screen.getByText(/Identificador como texto/)).toBeInTheDocument();
  });
});
