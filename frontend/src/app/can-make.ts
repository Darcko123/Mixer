import { Component, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatCardModule } from '@angular/material/card';
import { Api } from './api';
import { Bar } from './bar';

@Component({
  imports: [MatCardModule],
  selector: 'app-can-make',
  styles: `
    ul {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 16px;
    }
    mat-card {
      height: 100%;
    }
    .substitute {
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-tertiary);
    }
  `,
  template: `
    <h1>Puedo preparar</h1>
    <ul>
      @for (recipe of matches.value()?.can_make; track recipe.slug) {
        <li>
          <mat-card appearance="outlined">
            <mat-card-header>
              <mat-card-title>{{ recipe.name }}</mat-card-title>
              <mat-card-subtitle>{{ recipe.required_count }} ingredientes</mat-card-subtitle>
            </mat-card-header>
            @if (recipe.substitute_count > 0) {
              <mat-card-content>
                <span class="substitute">≈ usa sustituto</span>
              </mat-card-content>
            }
          </mat-card>
        </li>
      }
    </ul>
  `,
})
export class CanMake {
  private readonly api = inject(Api);
  private readonly bar = inject(Bar);

  // Leer el inventario en `params` recalcula las coincidencias tras cada cambio en la barra.
  protected readonly matches = rxResource({
    params: () => this.bar.inventory.value(),
    stream: () => this.api.matches(0),
  });
}
