import { Component, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import {
  MatAutocompleteModule,
  MatAutocompleteSelectedEvent,
} from '@angular/material/autocomplete';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { debounceTime, of, switchMap } from 'rxjs';
import { Api, RecipeIngredientStatus, RecipeRef } from './api';
import { Bar } from './bar';

/** Marca de cada ingrediente (§5.3), siempre con texto para no depender del color. */
const mark = (row: RecipeIngredientStatus): string => {
  switch (row.status) {
    case 'have':
      return '✓ Lo tienes';
    case 'have_equivalent':
      return `✓ vía ${row.covered_by?.name}`;
    case 'substitute':
      return `≈ con ${row.substitute?.name}`;
    case 'missing':
      return '✗ Falta';
  }
  return row.role === 'optional' ? 'Opcional' : row.role === 'garnish' ? 'Decoración' : '';
};

/** Alternativa de la fila anterior (mismo `alt_group`): se muestra con "o" delante. */
const isAlternative = (rows: { alt_group: number | null }[], i: number) =>
  i > 0 && rows[i].alt_group !== null && rows[i].alt_group === rows[i - 1].alt_group;

@Component({
  imports: [
    MatAutocompleteModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  selector: 'app-search',
  styles: `
    mat-form-field {
      width: 100%;
    }
    ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    li {
      padding: 4px 0;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
    .ingredients li {
      display: flex;
      justify-content: space-between;
      gap: 8px;
    }
    .label,
    .mark {
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-on-surface-variant);
    }
    p {
      margin: 4px 0 0;
    }
  `,
  template: `
    <h1>Buscar cóctel</h1>
    <mat-form-field>
      <mat-label>Nombre del cóctel</mat-label>
      <input matInput [formControl]="query" [matAutocomplete]="auto" />
      <mat-autocomplete #auto (optionSelected)="select($event)">
        @for (option of options(); track option.slug) {
          <mat-option [value]="option">{{ option.name }}</mat-option>
        }
      </mat-autocomplete>
    </mat-form-field>

    @if (recipe.value(); as recipe) {
      <mat-card appearance="outlined">
        <mat-card-header>
          <mat-card-title>{{ recipe.name }}</mat-card-title>
          <mat-card-subtitle>
            @if (recipe.can_make) {
              Puedes prepararlo
            } @else {
              Falta{{ recipe.missing_count === 1 ? '' : 'n' }} {{ recipe.missing_count }}
            }
            @if (recipe.substitute_count > 0) {
              · ≈ usa sustituto
            }
          </mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <h2>Ingredientes</h2>
          <ul class="ingredients">
            @for (row of recipe.ingredients; track $index) {
              <li>
                <span>
                  @if (isAlternative(recipe.ingredients, $index)) {
                    o
                  }
                  {{ row.name }}
                </span>
                <span class="mark">{{ mark(row) }}</span>
              </li>
            }
          </ul>
          @if (recipe.instructions) {
            <h2>Preparación</h2>
            <p>{{ recipe.instructions }}</p>
          }
          @if (recipe.shopping_list.length) {
            <h2>Lista de compras</h2>
            <ul>
              @for (item of recipe.shopping_list; track $index) {
                <li>
                  @if (isAlternative(recipe.shopping_list, $index)) {
                    o
                  }
                  {{ item.ingredient.name }}
                  @if (item.examples.length) {
                    <p><span class="label">Por ejemplo:</span> {{ names(item.examples) }}</p>
                  }
                  @if (item.also_unlocks.length) {
                    <p>
                      <span class="label">También desbloquea:</span> {{ names(item.also_unlocks) }}
                    </p>
                  }
                  @if (item.also_improves.length) {
                    <p>
                      <span class="label">También acerca:</span> {{ names(item.also_improves) }}
                    </p>
                  }
                </li>
              }
            </ul>
          }
        </mat-card-content>
      </mat-card>
    }
  `,
})
export class Search {
  private readonly api = inject(Api);
  private readonly bar = inject(Bar);
  protected readonly mark = mark;
  protected readonly isAlternative = isAlternative;

  // El campo guarda texto al escribir y la receta elegida al seleccionar; `displayWith` no hace
  // falta porque `select` lo devuelve a texto.
  protected readonly query = new FormControl<string | RecipeRef>('', { nonNullable: true });
  protected readonly options = toSignal(
    this.query.valueChanges.pipe(
      debounceTime(200),
      switchMap((q) =>
        typeof q === 'string' && q.trim() ? this.api.searchRecipes(q.trim()) : of([]),
      ),
    ),
    { initialValue: [] },
  );

  protected readonly slug = signal<string | undefined>(undefined);

  // Igual que las demás vistas: el detalle depende del inventario y se recalcula si cambia.
  protected readonly recipe = rxResource({
    params: () =>
      this.slug() && this.bar.inventory.value()
        ? { slug: this.slug()!, bar: this.bar.inventory.value() }
        : undefined,
    stream: ({ params }) => this.api.recipe(params.slug),
  });

  protected select(event: MatAutocompleteSelectedEvent): void {
    const recipe: RecipeRef = event.option.value;
    this.query.setValue(recipe.name, { emitEvent: false });
    this.slug.set(recipe.slug);
  }

  protected names(refs: { name: string }[]): string {
    return refs.map((r) => r.name).join(', ');
  }
}
