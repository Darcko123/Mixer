import { Component, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatCardModule } from '@angular/material/card';
import { Api } from './api';
import { Bar } from './bar';
import { EMPTY_BAR, Status } from './status';

@Component({
  imports: [MatCardModule, Status],
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
    <app-status [resource]="matches" />
    @if (matches.hasValue()) {
      @let recipes = matches.value().can_make;
      @if (recipes.length) {
        <ul>
          @for (recipe of recipes; track recipe.slug) {
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
      } @else {
        <p>
          {{
            bar.items()?.length
              ? 'Aún no puedes preparar ningún cóctel; mira Casi listos.'
              : emptyBar
          }}
        </p>
      }
    }
  `,
})
export class CanMake {
  private readonly api = inject(Api);
  protected readonly bar = inject(Bar);
  protected readonly emptyBar = EMPTY_BAR;

  // Leer el inventario en `params` recalcula las coincidencias tras cada cambio en la barra.
  protected readonly matches = rxResource({
    params: () => this.bar.items(),
    stream: () => this.api.matches(0),
  });
}
