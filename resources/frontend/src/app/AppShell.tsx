/** AppShell — envoltura del shell de la aplicación con layout y rutas. */
import { Outlet } from "react-router-dom";

import { PageLayout } from "@/layout/PageLayout";

export function AppShell(): React.JSX.Element {
  return (
    <PageLayout>
      <Outlet />
    </PageLayout>
  );
}
