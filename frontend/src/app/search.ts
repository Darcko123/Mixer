import { Component, inject, input } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import {
  MatAutocompleteModule,
  MatAutocompleteSelectedEvent,
} from '@angular/material/autocomplete';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Router } from '@angular/router';
import { catchError, debounceTime, of, switchMap } from 'rxjs';
import { Api, RecipeIngredientStatus, RecipeRef } from './api';
import { Bar } from './bar';
import { flavorText } from './flavors';
import { RecipeLinks } from './recipe-links';
import { RecipePhoto } from './recipe-photo';
import { Status } from './status';
import { formatAmount, Units } from './units';

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

// Claves en inglés del YAML (§6.1) → texto de la UI; una clave nueva se muestra tal cual.
const METHODS: Record<string, string> = {
  shake: 'Agitado',
  stir: 'Removido',
  build: 'Directo en el vaso',
  blend: 'Licuado',
  muddle: 'Macerado',
};
const GLASSES: Record<string, string> = {
  cocktail: 'Copa de cóctel',
  coupe: 'Copa coupé',
  flute: 'Copa flauta',
  wine: 'Copa de vino',
  goblet: 'Copa goblet',
  cordial: 'Copa de licor',
  'brandy-snifter': 'Copa de brandy',
  hurricane: 'Copa hurricane',
  'irish-coffee': 'Copa irish coffee',
  'pousse-cafe': 'Copa pousse-café',
  'whiskey-sour': 'Copa whiskey sour',
  highball: 'Vaso highball',
  collins: 'Vaso collins',
  'old-fashioned': 'Vaso old fashioned',
  'double-old-fashioned': 'Vaso old fashioned doble',
  shot: 'Vaso de shot',
  tiki: 'Vaso tiki',
  cobbler: 'Vaso cobbler',
  'julep-cup': 'Vaso julep',
  'mule-cup': 'Taza de cobre',
  'coffee-mug': 'Taza',
  beer: 'Vaso de cerveza',
  'beer-mug': 'Tarro de cerveza',
  'beer-pilsner': 'Vaso pilsner',
  pint: 'Vaso pinta',
  jar: 'Frasco',
  pitcher: 'Jarra',
  'punch-bowl': 'Ponchera',
};

/** Método y vaso en una línea ("Agitado · Copa de cóctel"). */
const serving = (recipe: { method: string | null; glass: string | null }): string =>
  [
    recipe.method && (METHODS[recipe.method] ?? recipe.method),
    recipe.glass && (GLASSES[recipe.glass] ?? recipe.glass.replaceAll('-', ' ')),
  ]
    .filter(Boolean)
    .join(' · ');

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
    RecipeLinks,
    RecipePhoto,
    Status,
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
    .amount {
      font-weight: 500;
    }
    .label,
    .mark,
    .hint {
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-on-surface-variant);
    }
    /* El color refuerza la marca; el texto (✓ / ≈ / ✗) sigue siendo lo que la comunica. */
    .mark[data-status='have'],
    .mark[data-status='have_equivalent'] {
      color: var(--mat-sys-primary);
    }
    .mark[data-status='substitute'] {
      color: var(--mat-sys-tertiary);
    }
    .mark[data-status='missing'] {
      color: var(--mat-sys-error);
    }
    p {
      margin: 4px 0 0;
    }
    /* Con foto: arriba y cuadrada en pantallas estrechas; entera (2:3) en una columna a la izquierda
       en las anchas. */
    .photo {
      margin: 16px 16px 0;
    }
    .photo app-recipe-photo {
      border-radius: 12px;
    }
    .photo figcaption {
      margin-top: 4px;
      font: var(--mat-sys-label-medium);
      color: var(--mat-sys-on-surface-variant);
    }
    @media (min-width: 720px) {
      .detail:has(.photo) {
        display: grid;
        grid-template-columns: 240px 1fr;
        align-items: start;
      }
      .photo {
        margin-bottom: 16px;
      }
      .photo app-recipe-photo {
        aspect-ratio: 2 / 3;
      }
    }
  `,
  template: `
    <h1>Buscar cóctel</h1>
    <!-- Con una receta abierta el buscador sobra: la pestaña "Buscar cóctel" lo vuelve a mostrar. -->
    @if (!receta()) {
      <mat-form-field>
        <mat-label>Nombre del cóctel</mat-label>
        <input matInput [formControl]="query" [matAutocomplete]="auto" />
        <mat-autocomplete #auto (optionSelected)="select($event)">
          @if (options() === null) {
            <mat-option disabled>✗ No se pudo buscar. Inténtalo de nuevo.</mat-option>
          } @else if (options()?.length === 0) {
            <mat-option disabled>Sin resultados</mat-option>
          }
          @for (option of options() ?? []; track option.slug) {
            <mat-option [value]="option">{{ option.name }}</mat-option>
          }
        </mat-autocomplete>
      </mat-form-field>
      <p class="hint">
        Escribe el nombre de un cóctel, o abre uno desde Puedo preparar, Casi listos o Qué comprar.
      </p>
    }
    <app-status [resource]="detail" />
    @if (detail.hasValue()) {
      @let recipe = detail.value();
      <mat-card class="detail" appearance="outlined">
        @if (recipe.image) {
          <figure class="photo">
            <app-recipe-photo [image]="recipe.image" [alt]="'Foto de ' + recipe.name" />
            @if (recipe.image.source_url) {
              <figcaption>
                <a [href]="recipe.image.source_url" target="_blank" rel="noopener"
                  >Fuente de la foto</a
                >
              </figcaption>
            }
          </figure>
        }
        <div>
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
            @if (serving(recipe)) {
              <mat-card-subtitle class="serving">{{ serving(recipe) }}</mat-card-subtitle>
            }
            @if (recipe.flavors.length) {
              <mat-card-subtitle class="flavors">{{
                flavorText(recipe.flavors)
              }}</mat-card-subtitle>
            }
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
                    @let amount = formatAmount(row, units.volume());
                    @if (amount) {
                      <span class="amount">{{ amount }}</span>
                    }
                    {{ row.name }}
                  </span>
                  <span class="mark" [attr.data-status]="row.status">{{ mark(row) }}</span>
                </li>
              }
            </ul>
            @if (recipe.instructions) {
              <h2>Preparación</h2>
              <p>{{ recipe.instructions }}</p>
            }
            @if (recipe.garnish_text) {
              <p><span class="label">Decoración:</span> {{ recipe.garnish_text }}</p>
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
                      <p>
                        <span class="label">Por ejemplo:</span>
                        {{ names(item.examples) }}
                      </p>
                    }
                    @if (item.also_unlocks.length) {
                      <p>
                        <span class="label">También desbloquea:</span>&ngsp;<app-recipe-links
                          [recipes]="item.also_unlocks"
                        />
                      </p>
                    }
                    @if (item.also_improves.length) {
                      <p>
                        <span class="label">También acerca:</span>&ngsp;<app-recipe-links
                          [recipes]="item.also_improves"
                        />
                      </p>
                    }
                  </li>
                }
              </ul>
            }
          </mat-card-content>
        </div>
      </mat-card>
    }
  `,
})
export class Search {
  private readonly api = inject(Api);
  private readonly bar = inject(Bar);
  private readonly router = inject(Router);
  protected readonly mark = mark;
  protected readonly serving = serving;
  protected readonly flavorText = flavorText;
  protected readonly isAlternative = isAlternative;
  protected readonly formatAmount = formatAmount;
  protected readonly units = inject(Units);

  // El campo guarda texto al escribir y la receta elegida al seleccionar; `displayWith` no hace
  // falta porque `select` lo vacía.
  protected readonly query = new FormControl<string | RecipeRef>('', { nonNullable: true });
  // Como en `MyBar`: `undefined` sin consulta, `[]` sin resultados y `null` si la búsqueda falló.
  protected readonly options = toSignal(
    this.query.valueChanges.pipe(
      debounceTime(200),
      switchMap((q) =>
        typeof q === 'string' && q.trim()
          ? this.api.searchRecipes(q.trim()).pipe(catchError(() => of(null)))
          : of(undefined),
      ),
    ),
  );

  /** Receta abierta, de `?receta=` en la URL: el detalle se puede enlazar y "atrás" funciona. */
  readonly receta = input<string>();

  // Igual que las demás vistas: el detalle depende del inventario y se recalcula si cambia.
  protected readonly detail = rxResource({
    params: () =>
      this.receta() && this.bar.items()
        ? { slug: this.receta()!, bar: this.bar.items() }
        : undefined,
    stream: ({ params }) => this.api.recipe(params.slug),
  });

  protected select(event: MatAutocompleteSelectedEvent): void {
    const recipe: RecipeRef = event.option.value;
    // Al volver a la búsqueda el campo aparece vacío y sin las opciones anteriores.
    this.query.reset();
    void this.router.navigate(['/buscar'], { queryParams: { receta: recipe.slug } });
  }

  protected names(refs: { name: string }[]): string {
    return refs.map((r) => r.name).join(', ');
  }
}
