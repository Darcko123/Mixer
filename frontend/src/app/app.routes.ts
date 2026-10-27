import { Routes } from '@angular/router';
import { Placeholder } from './placeholder';

// Las rutas con `title` forman la navegación principal, en este orden.
export const routes: Routes = [
  {
    path: 'mi-barra',
    title: 'Mi barra',
    loadComponent: () => import('./my-bar').then((m) => m.MyBar),
  },
  {
    path: 'puedo-preparar',
    title: 'Puedo preparar',
    loadComponent: () => import('./can-make').then((m) => m.CanMake),
  },
  {
    path: 'casi-listos',
    title: 'Casi listos',
    loadComponent: () => import('./almost').then((m) => m.Almost),
  },
  {
    path: 'que-comprar',
    title: 'Qué comprar',
    loadComponent: () => import('./shopping').then((m) => m.Shopping),
  },
  { path: 'buscar', title: 'Buscar cóctel', component: Placeholder },
  { path: '**', redirectTo: 'mi-barra' },
];
