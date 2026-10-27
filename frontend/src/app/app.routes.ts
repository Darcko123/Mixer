import { Routes } from '@angular/router';
import { Placeholder } from './placeholder';

// Las rutas con `title` forman la navegación principal, en este orden.
export const routes: Routes = [
  { path: 'mi-barra', title: 'Mi barra', component: Placeholder },
  { path: 'puedo-preparar', title: 'Puedo preparar', component: Placeholder },
  { path: 'casi-listos', title: 'Casi listos', component: Placeholder },
  { path: 'que-comprar', title: 'Qué comprar', component: Placeholder },
  { path: 'buscar', title: 'Buscar cóctel', component: Placeholder },
  { path: '**', redirectTo: 'mi-barra' },
];
