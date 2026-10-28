import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { RouterLink } from '@angular/router';
import { Bar, Matches } from './bar';
import { FlavorFilter, NO_FLAVOR_MATCH, flavorText, withFlavors } from './flavors';
import { RecipePhoto } from './recipe-photo';
import { EMPTY_BAR, Status } from './status';

@Component({
  imports: [
    FlavorFilter,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    RecipePhoto,
    RouterLink,
    Status,
  ],
  selector: 'app-almost',
  styles: `
    ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }
    /* En móvil las tarjetas son horizontales (styles.scss) y van una por fila. */
    @media (max-width: 599px) {
      .cards {
        grid-template-columns: 1fr;
      }
    }
    mat-card {
      height: 100%;
    }
    .missing li {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .flavors {
      margin: 0 0 8px;
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-on-surface-variant);
    }
    .substitute {
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-tertiary);
    }
  `,
  template: `
    <h1>Casi listos</h1>
    <app-status [resource]="matches" />
    @if (matches.hasValue()) {
      @let all = matches.value().almost;
      @let recipes = withFlavors(all, flavors());
      @if (all.length) {
        <app-flavor-filter [recipes]="all" [(selected)]="flavors" />
      }
      @if (recipes.length) {
        <ul class="cards">
          @for (recipe of recipes; track recipe.slug) {
            <li>
              <mat-card class="recipe-card" appearance="outlined">
                <app-recipe-photo [image]="recipe.image" />
                <mat-card-header>
                  <mat-card-title>
                    <a
                      class="recipe-link"
                      routerLink="/buscar"
                      [queryParams]="{ receta: recipe.slug }"
                      >{{ recipe.name }}</a
                    >
                  </mat-card-title>
                  <mat-card-subtitle>
                    Falta{{ recipe.missing_count === 1 ? '' : 'n' }} {{ recipe.missing_count }} de
                    {{ recipe.required_count }}
                  </mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  @if (recipe.flavors.length) {
                    <p class="flavors">{{ flavorText(recipe.flavors) }}</p>
                  }
                  <ul class="missing" [attr.aria-label]="'Faltantes de ' + recipe.name">
                    @for (ingredient of recipe.missing; track ingredient.slug) {
                      <li>
                        <mat-chip-set>
                          <mat-chip>{{ ingredient.name }}</mat-chip>
                        </mat-chip-set>
                        <button
                          mat-button
                          type="button"
                          [attr.aria-label]="'Ya tengo ' + ingredient.name"
                          (click)="bar.add(ingredient.slug)"
                        >
                          Ya lo tengo
                        </button>
                      </li>
                    }
                  </ul>
                  @if (recipe.substitute_count > 0) {
                    <span class="substitute">≈ usa sustituto</span>
                  }
                </mat-card-content>
              </mat-card>
            </li>
          }
        </ul>
      } @else if (all.length) {
        <p>{{ noFlavorMatch }}</p>
      } @else {
        <p>
          {{ bar.items()?.length ? 'Ningún cóctel está a uno o dos ingredientes.' : emptyBar }}
        </p>
      }
    }
  `,
})
export class Almost {
  // El backend ya ordena por faltantes (§5.4). "Ya lo tengo" cambia el inventario y eso relanza
  // las coincidencias.
  protected readonly bar = inject(Bar);
  protected readonly matches = inject(Matches).resource;
  protected readonly flavors = inject(Matches).flavors;
  protected readonly emptyBar = EMPTY_BAR;
  protected readonly noFlavorMatch = NO_FLAVOR_MATCH;
  protected readonly flavorText = flavorText;
  protected readonly withFlavors = withFlavors;
}
