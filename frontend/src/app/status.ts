import { Component, WritableResource, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';

/** Vacío común a las vistas que recomiendan a partir de la barra. */
export const EMPTY_BAR = 'Añade ingredientes para empezar.';

/** Carga y error de un recurso; el vacío lo decide cada vista porque depende de qué lista mira. */
@Component({
  imports: [MatButtonModule, MatProgressBarModule],
  selector: 'app-status',
  styles: `
    p {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      color: var(--mat-sys-error);
    }
  `,
  template: `
    <!-- La carga va primero: al reintentar, el recurso conserva el error hasta que responde. -->
    @if (resource().isLoading()) {
      <mat-progress-bar mode="indeterminate" aria-label="Cargando" />
    } @else if (resource().error()) {
      <p role="alert">
        ✗ No se pudieron cargar los datos.
        <button mat-button type="button" (click)="resource().reload()">Reintentar</button>
      </p>
    }
  `,
})
export class Status {
  readonly resource = input.required<WritableResource<unknown>>();
}
