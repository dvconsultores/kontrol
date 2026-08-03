import { render, screen } from "@testing-library/react";
import { createColumnHelper } from "@tanstack/react-table";
import { describe, expect, it } from "vitest";

import { DataTable } from "./DataTable";

interface Row {
  id: string;
  name: string;
}

const columnHelper = createColumnHelper<Row>();
const columns = [
  columnHelper.accessor("id", { header: "ID" }),
  columnHelper.accessor("name", { header: "Nombre" }),
];

describe("DataTable", () => {
  it("muestra filas y encabezados", () => {
    render(<DataTable columns={columns} data={[{ id: "1", name: "Demo" }]} />);
    expect(screen.getByText("Demo")).toBeInTheDocument();
    expect(screen.getByText("Nombre")).toBeInTheDocument();
  });

  it("muestra estado vacío (FR-017)", () => {
    render(<DataTable columns={columns} data={[]} emptyTitle="Sin registros" />);
    expect(screen.getByText("Sin registros")).toBeInTheDocument();
  });

  it("no muestra paginación con <= 10 registros (FR-019)", () => {
    const data = Array.from({ length: 5 }, (_, i) => ({ id: String(i), name: `Fila ${i}` }));
    render(<DataTable columns={columns} data={data} />);
    expect(screen.queryByRole("navigation", { name: "Paginación" })).not.toBeInTheDocument();
  });

  it("muestra paginación con > 10 registros (FR-019)", () => {
    const data = Array.from({ length: 15 }, (_, i) => ({ id: String(i), name: `Fila ${i}` }));
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByRole("navigation", { name: "Paginación" })).toBeInTheDocument();
  });
});
