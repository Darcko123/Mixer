import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import {
  MatAutocompleteModule,
  MatAutocompleteSelectedEvent,
} from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { catchError, debounceTime, of, switchMap } from 'rxjs';
import { Api, InventoryItem } from './api';
import { Bar } from './bar';
import { EMPTY_BAR } from './status';

/** Ruta hasta el padre: lo que distingue "Ron blanco" de "Vermut blanco" en las sugerencias. */
const parentPath = (path: string[]) => path.slice(0, -1).join(' › ');

@Component({
  imports: [
    MatAutocompleteModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  selector: 'app-my-bar',
  styles: `
    mat-form-field {
      width: 100%;
    }
    .path {
      display: block;
      font: var(--mat-sys-body-small);
      color: var(--mat-sys-on-surface-variant);
    }
    ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    li {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 4px 0;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
  `,
  template: `
    <h1>Mi barra</h1>
    <mat-form-field>
      <mat-label>Añadir ingrediente</mat-label>
      <input matInput [formControl]="query" [matAutocomplete]="auto" />
      <mat-autocomplete #auto (optionSelected)="add($event)">
        @if (options() === null) {
          <mat-option disabled>✗ No se pudo buscar. Inténtalo de nuevo.</mat-option>
        } @else if (options()?.length === 0) {
          <mat-option disabled>Sin resultados</mat-option>
        }
        @for (option of options() ?? []; track option.slug) {
          <mat-option [value]="option.slug" [disabled]="bar.slugs().has(option.slug)">
            {{ option.name }}
            @if (bar.slugs().has(option.slug)) {
              (ya en tu barra)
            }
            <span class="path">{{ parentPath(option.path) }}</span>
          </mat-option>
        }
      </mat-autocomplete>
    </mat-form-field>

    @if (bar.items()?.length === 0) {
      <p>{{ emptyBar }}</p>
    }
    @for (group of groups(); track group.category) {
      <section>
        <h2>{{ group.category }}</h2>
        <ul>
          @for (item of group.items; track item.slug) {
            <li>
              <span>
                {{ item.name }}
                <span class="path">{{ parentPath(item.path.slice(1)) }}</span>
              </span>
              <button
                mat-button
                (click)="bar.remove(item.slug)"
                [attr.aria-label]="'Quitar ' + item.name"
              >
                Quitar
              </button>
            </li>
          }
        </ul>
      </section>
    }
  `,
})
export class MyBar {
  private readonly api = inject(Api);
  protected readonly bar = inject(Bar);
  protected readonly parentPath = parentPath;
  protected readonly emptyBar = EMPTY_BAR;

  protected readonly query = new FormControl('', { nonNullable: true });
  // `undefined` sin consulta, `[]` sin resultados y `null` si la búsqueda falló.
  protected readonly options = toSignal(
    this.query.valueChanges.pipe(
      debounceTime(200),
      switchMap((q) =>
        q.trim()
          ? this.api.searchIngredients(q.trim()).pipe(catchError(() => of(null)))
          : of(undefined),
      ),
    ),
  );

  /** Agrupa por la categoría raíz (`path[0]`); el inventario ya llega ordenado por ruta. */
  protected readonly groups = computed(() => {
    const groups = new Map<string, InventoryItem[]>();
    for (const item of this.bar.items() ?? []) {
      groups.set(item.path[0], [...(groups.get(item.path[0]) ?? []), item]);
    }
    return [...groups].map(([category, items]) => ({ category, items }));
  });

  protected async add(event: MatAutocompleteSelectedEvent): Promise<void> {
    this.query.setValue('');
    await this.bar.add(event.option.value);
  }
}
