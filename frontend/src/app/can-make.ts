import { Component, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { RouterLink } from '@angular/router';
import { Bar, Matches } from './bar';
import { FlavorFilter, NO_FLAVOR_MATCH, flavorText, withFlavors } from './flavors';
import { RecipePhoto } from './recipe-photo';
import { EMPTY_BAR, Status } from './status';

@Component({
  imports: [FlavorFilter, MatCardModule, RecipePhoto, RouterLink, Status],
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
    /* En móvil las tarjetas son horizontales (styles.scss) y van una por fila. */
    @media (max-width: 599px) {
      ul {
        grid-template-columns: 1fr;
      }
    }
    mat-card {
      height: 100%;
    }
    .flavors {
      margin: 0;
      font: var(--mat-sys-label-large);
      color: var(--mat-sys-on-surface-variant);
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
      @let all = matches.value().can_make;
      @let recipes = withFlavors(all, flavors());
      @if (all.length) {
        <app-flavor-filter [recipes]="all" [(selected)]="flavors" />
      }
      @if (recipes.length) {
        <ul>
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
                  <mat-card-subtitle>{{ recipe.required_count }} ingredientes</mat-card-subtitle>
                </mat-card-header>
                @if (recipe.flavors.length || recipe.substitute_count > 0) {
                  <mat-card-content>
                    @if (recipe.flavors.length) {
                      <p class="flavors">{{ flavorText(recipe.flavors) }}</p>
                    }
                    @if (recipe.substitute_count > 0) {
                      <span class="substitute">≈ usa sustituto</span>
                    }
                  </mat-card-content>
                }
              </mat-card>
            </li>
          }
        </ul>
      } @else if (all.length) {
        <p>{{ noFlavorMatch }}</p>
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
  protected readonly bar = inject(Bar);
  protected readonly matches = inject(Matches).resource;
  protected readonly flavors = inject(Matches).flavors;
  protected readonly emptyBar = EMPTY_BAR;
  protected readonly noFlavorMatch = NO_FLAVOR_MATCH;
  protected readonly flavorText = flavorText;
  protected readonly withFlavors = withFlavors;
}
