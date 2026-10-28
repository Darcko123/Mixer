import { Component, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { Api } from './api';
import { Bar } from './bar';
import { RecipeLinks } from './recipe-links';
import { EMPTY_BAR, Status } from './status';

@Component({
  imports: [MatButtonToggleModule, MatCardModule, RecipeLinks, Status],
  selector: 'app-shopping',
  styles: `
    ol {
      list-style: none;
      margin: 16px 0 0;
      padding: 0;
      display: grid;
      gap: 16px;
    }
    .label {
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-on-surface-variant);
    }
    p {
      margin: 8px 0 0;
    }
  `,
  template: `
    <h1>Qué comprar</h1>
    <span class="label" id="k-label">¿Cuántas compras?</span>
    <mat-button-toggle-group
      aria-labelledby="k-label"
      hideSingleSelectionIndicator
      [value]="k()"
      (change)="k.set($event.value)"
    >
      @for (n of options; track n) {
        <mat-button-toggle [value]="n">{{ n }}</mat-button-toggle>
      }
    </mat-button-toggle-group>
    <app-status [resource]="suggestions" />
    @if (suggestions.hasValue()) {
      @if (suggestions.value().length) {
        <ol>
          @for (
            suggestion of suggestions.value();
            track suggestion.ingredient.slug;
            let i = $index
          ) {
            <li>
              <mat-card appearance="outlined">
                <mat-card-header>
                  <mat-card-title>{{ i + 1 }}. {{ suggestion.ingredient.name }}</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  @if (suggestion.unlocks.length) {
                    <p>
                      <span class="label">Desbloquea:</span>&ngsp;<app-recipe-links
                        [recipes]="suggestion.unlocks"
                      />
                    </p>
                  }
                  @if (suggestion.improves.length) {
                    <p>
                      <span class="label">Acerca:</span>&ngsp;<app-recipe-links
                        [recipes]="suggestion.improves"
                      />
                    </p>
                  }
                </mat-card-content>
              </mat-card>
            </li>
          }
        </ol>
      } @else {
        <p>
          {{ bar.items()?.length ? 'Ninguna compra desbloquea recetas nuevas.' : emptyBar }}
        </p>
      }
    }
  `,
})
export class Shopping {
  private readonly api = inject(Api);
  protected readonly bar = inject(Bar);
  protected readonly emptyBar = EMPTY_BAR;

  protected readonly options = [1, 2, 3, 4, 5];
  protected readonly k = signal(3);

  // Las compras son relativas al inventario más las anteriores, así que se recalculan al cambiar
  // cualquiera de los dos; sin inventario cargado aún no se pide nada.
  protected readonly suggestions = rxResource({
    params: () => (this.bar.items() ? { k: this.k(), bar: this.bar.items() } : undefined),
    stream: ({ params }) => this.api.suggestions(params.k),
  });
}
