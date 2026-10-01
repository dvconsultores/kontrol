import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  // Los dos casos de arriba fijan las mitades —5 y 15— pero dejaban fuera el
  // borde, que es donde la regla se decide: con exactamente diez no hay segunda
  // página. Un E2E de documentos daba por hecho que «Página siguiente» siempre
  // está, la base llegó justo a diez y la espera por un control inexistente
  // agotó la prueba. El borde se cubre aquí, que es donde vive el contrato, y no
  // sembrando un registro once en una base compartida.
  it("no muestra paginación con exactamente 10 registros (FR-019)", () => {
    const data = Array.from({ length: 10 }, (_, i) => ({ id: String(i), name: `Fila ${i}` }));
    render(<DataTable columns={columns} data={data} />);
    expect(screen.queryByRole("navigation", { name: "Paginación" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Página siguiente" })).not.toBeInTheDocument();
    expect(screen.getByText("Fila 9")).toBeInTheDocument();
  });

  it("no muestra paginación con 9 registros (FR-019)", () => {
    const data = Array.from({ length: 9 }, (_, i) => ({ id: String(i), name: `Fila ${i}` }));
    render(<DataTable columns={columns} data={data} />);
    expect(screen.queryByRole("navigation", { name: "Paginación" })).not.toBeInTheDocument();
  });

  it("con 11 registros la segunda página trae el que sobra (FR-019)", async () => {
    const data = Array.from({ length: 11 }, (_, i) => ({ id: String(i), name: `Fila ${i}` }));
    render(<DataTable columns={columns} data={data} />);

    // Primera página: diez, y el undécimo todavía no.
    expect(screen.getByText("Fila 0")).toBeInTheDocument();
    expect(screen.getByText("Fila 9")).toBeInTheDocument();
    expect(screen.queryByText("Fila 10")).not.toBeInTheDocument();

    const siguiente = screen.getByRole("button", { name: "Página siguiente" });
    expect(siguiente).toBeEnabled();
    expect(screen.getByRole("button", { name: "Página anterior" })).toBeDisabled();

    await userEvent.click(siguiente);

    expect(screen.getByText("Fila 10")).toBeInTheDocument();
    expect(screen.queryByText("Fila 0")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Página siguiente" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Página anterior" })).toBeEnabled();
  });

  it("con paginación manual pinta la página recibida tal cual y deja el paginador a la pantalla", () => {
    const filas = Array.from({ length: 25 }, (_, i) => ({ id: String(i + 1), name: `Fila ${i + 1}` }));
    render(<DataTable columns={columns} data={filas} manualPagination getRowId={(r) => r.id} />);
    expect(screen.getAllByRole("row")).toHaveLength(26);
    expect(screen.queryByRole("navigation", { name: "Paginación" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Mostrando/)).not.toBeInTheDocument();
  });
});
