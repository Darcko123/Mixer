import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { RecipeRef } from './api';

/**
 * Recetas como enlaces a su detalle (`/buscar?receta=`), separadas por comas. El espacio tras la coma
 * es el salto de línea que sigue a la interpolación.
 */
@Component({
  imports: [RouterLink],
  selector: 'app-recipe-links',
  template: `
    @for (recipe of recipes(); track recipe.slug) {
      <a routerLink="/buscar" [queryParams]="{ receta: recipe.slug }">{{ recipe.name }}</a
      >{{ $last ? '' : ',' }}
    }
  `,
})
export class RecipeLinks {
  readonly recipes = input.required<RecipeRef[]>();
}
