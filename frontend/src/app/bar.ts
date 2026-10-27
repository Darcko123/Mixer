import { Injectable, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
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
 * compras) leen `inventory.value()` en sus parámetros para recalcularse tras cada cambio.
 */
@Injectable({ providedIn: 'root' })
export class Bar {
  private readonly api = inject(Api);

  readonly inventory = rxResource({ stream: () => this.api.inventory() });
  readonly slugs = computed(() => new Set(this.inventory.value()?.map((item) => item.slug)));

  async add(slug: string): Promise<void> {
    const item = await firstValueFrom(this.api.addToInventory(slug));
    this.inventory.update((items = []) =>
      [...items.filter((i) => i.slug !== slug), item].sort(byPath),
    );
  }

  async remove(slug: string): Promise<void> {
    await firstValueFrom(this.api.removeFromInventory(slug));
    this.inventory.update((items = []) => items.filter((i) => i.slug !== slug));
  }
}
