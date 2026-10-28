import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { RouterLink } from '@angular/router';
import { Bar, Matches } from './bar';
import { EMPTY_BAR, Status } from './status';

@Component({
  imports: [MatButtonModule, MatCardModule, MatChipsModule, RouterLink, Status],
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
    mat-card {
      height: 100%;
    }
    .missing li {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
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
      @let recipes = matches.value().almost;
      @if (recipes.length) {
        <ul class="cards">
          @for (recipe of recipes; track recipe.slug) {
            <li>
              <mat-card class="recipe-card" appearance="outlined">
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
  protected readonly emptyBar = EMPTY_BAR;
}
