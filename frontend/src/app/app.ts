import { Component, computed, inject } from '@angular/core';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTabsModule } from '@angular/material/tabs';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { routes } from './app.routes';
import { Bar, Matches } from './bar';
import { Status } from './status';
import { Units } from './units';

@Component({
  imports: [
    MatButtonToggleModule,
    MatTabsModule,
    MatToolbarModule,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    Status,
  ],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  // Todas las vistas dependen del inventario: su carga y su error se muestran una vez aquí.
  protected readonly bar = inject(Bar);
  protected readonly units = inject(Units);
  private readonly matches = inject(Matches).resource;
  protected readonly views = routes.filter((route) => typeof route.title === 'string');
  /** Recetas en cada vista de coincidencias: muestran al momento qué cambió al tocar la barra. */
  protected readonly counts = computed((): Record<string, number | undefined> => {
    const matches = this.matches.hasValue() ? this.matches.value() : undefined;
    return { 'puedo-preparar': matches?.can_make.length, 'casi-listos': matches?.almost.length };
  });
}
