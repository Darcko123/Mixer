import { Component, computed, input, model } from '@angular/core';
import { MatChipListboxChange, MatChipsModule } from '@angular/material/chips';
import { Flavor } from './api';

/** Claves en inglés del YAML → texto de la UI, en el orden en que se ofrecen en el filtro. */
export const FLAVORS: Record<Flavor, string> = {
  sweet: 'Dulce',
  sour: 'Ácido',
  bitter: 'Amargo',
  dry: 'Seco',
  strong: 'Fuerte',
  creamy: 'Cremoso',
  fruity: 'Frutal',
  herbal: 'Herbal',
  spicy: 'Picante',
  savory: 'Salado',
};

/** Vacío de una vista con recetas, pero ninguna con todos los sabores elegidos. */
export const NO_FLAVOR_MATCH = 'Ningún cóctel tiene todos esos sabores.';

/** Sabores de una receta en una línea ("Ácido · Dulce"), del dominante al menor. */
export const flavorText = (flavors: readonly Flavor[]): string =>
  flavors.map((f) => FLAVORS[f]).join(' · ');

/** Recetas que tienen todos los sabores elegidos; sin ninguno elegido, todas. */
export const withFlavors = <T extends { flavors: readonly Flavor[] }>(
  recipes: readonly T[],
  selected: readonly Flavor[],
): T[] => recipes.filter((r) => selected.every((f) => r.flavors.includes(f)));

/**
 * Chips para filtrar por sabor. Solo ofrece los sabores presentes en `recipes` (más los ya
 * elegidos, para poder desmarcarlos aunque la lista haya cambiado).
 */
@Component({
  imports: [MatChipsModule],
  selector: 'app-flavor-filter',
  styles: `
    :host {
      display: block;
      margin-bottom: 16px;
    }
  `,
  template: `
    @if (options().length) {
      <mat-chip-listbox
        multiple
        aria-label="Filtrar por sabor"
        [value]="selected()"
        (change)="select($event)"
      >
        @for (flavor of options(); track flavor) {
          <mat-chip-option [value]="flavor">{{ labels[flavor] }}</mat-chip-option>
        }
      </mat-chip-listbox>
    }
  `,
})
export class FlavorFilter {
  readonly recipes = input.required<readonly { flavors: readonly Flavor[] }[]>();
  readonly selected = model.required<readonly Flavor[]>();

  protected readonly labels = FLAVORS;
  protected readonly options = computed(() => {
    const present = new Set([...this.selected(), ...this.recipes().flatMap((r) => r.flavors)]);
    return (Object.keys(FLAVORS) as Flavor[]).filter((f) => present.has(f));
  });

  protected select(event: MatChipListboxChange): void {
    this.selected.set(event.value as Flavor[]);
  }
}
