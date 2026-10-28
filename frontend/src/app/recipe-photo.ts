import { Component, input, linkedSignal } from '@angular/core';
import { RecipeImage } from './api';

/**
 * Foto de una receta, recortada al cuadro que le dé quien la usa (cuadrada por defecto). Sin foto, o
 * si no carga, ocupa el mismo hueco con una copa para que la cuadrícula no salte.
 */
@Component({
  selector: 'app-recipe-photo',
  styles: `
    :host {
      display: block;
      aspect-ratio: 1;
      overflow: hidden;
      background: var(--mat-sys-surface-container-high);
      color: var(--mat-sys-outline);
    }
    img,
    svg {
      display: block;
      width: 100%;
      height: 100%;
    }
    /* Las fotos IBA (2:3) tienen la copa en la mitad de abajo: el recorte conserva el ancho y baja.
       Las de TheCocktailDB son cuadradas y no se recortan en las tarjetas. */
    img {
      object-fit: cover;
      object-position: 50% 75%;
    }
    svg {
      box-sizing: border-box;
      padding: 36%;
    }
  `,
  template: `
    @if (image() && !failed()) {
      <img
        [src]="image()!.url"
        [alt]="alt()"
        width="682"
        height="1024"
        loading="lazy"
        decoding="async"
        (error)="failed.set(true)"
      />
    } @else {
      <svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
        <path d="M21 5V3H3v2l8 9v5H6v2h12v-2h-5v-5l8-9zM7.43 7 5.66 5h12.69l-1.78 2H7.43z" />
      </svg>
    }
  `,
})
export class RecipePhoto {
  readonly image = input.required<RecipeImage | null>();
  /** Vacío en las tarjetas, donde el nombre ya está al lado. */
  readonly alt = input('');
  // Vuelve a intentarlo si cambia la foto (el detalle reutiliza el componente entre recetas).
  protected readonly failed = linkedSignal({ source: this.image, computation: () => false });
}
