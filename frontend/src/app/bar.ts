import { Injectable, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';
import { Api, InventoryItem } from './api';

// Mismo orden que `GET /inventory`: por ruta, comparando nombre a nombre.
const byPath = (a: InventoryItem, b: InventoryItem) => {
  const x = a.path.join('\0');
  const y = b.path.join('\0');
  return x < y ? -1 : x > y ? 1 : 0;
};

/**
 * Inventario compartido por todas las vistas. Las vistas que dependen de él (coincidencias,
 * compras) leen `items()` en sus parámetros para recalcularse tras cada cambio.
 */
@Injectable({ providedIn: 'root' })
export class Bar {
  private readonly api = inject(Api);
  private readonly snackBar = inject(MatSnackBar);

  readonly inventory = rxResource({ stream: () => this.api.inventory() });
  /** El inventario, o `undefined` mientras carga o si falló (`value()` lanza en estado de error). */
  readonly items = computed(() => (this.inventory.hasValue() ? this.inventory.value() : undefined));
  readonly slugs = computed(() => new Set(this.items()?.map((item) => item.slug)));

  // Los errores se avisan aquí y no se propagan: los botones que llaman a `add`/`remove` no esperan
  // la promesa.
  async add(slug: string): Promise<void> {
    try {
      const item = await firstValueFrom(this.api.addToInventory(slug));
      this.inventory.update((items = []) =>
        [...items.filter((i) => i.slug !== slug), item].sort(byPath),
      );
    } catch {
      this.snackBar.open('No se pudo añadir el ingrediente.', 'Cerrar');
    }
  }

  // Quitar no pide confirmación: se puede deshacer desde el aviso.
  async remove(slug: string): Promise<void> {
    const name = this.items()?.find((i) => i.slug === slug)?.name ?? 'Ingrediente';
    try {
      await firstValueFrom(this.api.removeFromInventory(slug));
      this.inventory.update((items = []) => items.filter((i) => i.slug !== slug));
      this.snackBar
        .open(`${name} quitado de tu barra.`, 'Deshacer', { duration: 6000 })
        .onAction()
        .subscribe(() => this.add(slug));
    } catch {
      this.snackBar.open('No se pudo quitar el ingrediente.', 'Cerrar');
    }
  }
}

/**
 * Coincidencias de §5.4 (`can_make` y `almost`), compartidas por la navegación (que muestra cuántas
 * hay) y por sus dos vistas. Leer el inventario en `params` las recalcula tras cada cambio en la barra.
 */
@Injectable({ providedIn: 'root' })
export class Matches {
  private readonly api = inject(Api);
  private readonly bar = inject(Bar);

  readonly resource = rxResource({
    params: () => this.bar.items(),
    stream: () => this.api.matches(),
  });
}
