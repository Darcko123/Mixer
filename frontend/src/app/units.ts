import { Injectable, signal } from '@angular/core';

export type VolumeUnit = 'ml' | 'oz';

const ML_PER_OZ = 30;
const QUARTERS = ['', '¼', '½', '¾'];
const STORAGE_KEY = 'mixer.volumeUnit';

/** `amount_ml` de la API → texto en la unidad elegida. Las oz se redondean al cuarto (mínimo ¼). */
export function formatVolume(ml: number, unit: VolumeUnit): string {
  if (unit === 'ml') return `${ml} ml`;
  const quarters = Math.max(1, Math.round((ml / ML_PER_OZ) * 4));
  const whole = Math.floor(quarters / 4);
  return `${whole || ''}${QUARTERS[quarters % 4]} oz`;
}

/** Cantidad de un ingrediente: volumen en la unidad elegida, o `amount` + `unit` tal cual (dash, pieza…). */
export function formatAmount(
  row: { amount: number | null; unit: string | null; amount_ml: number | null },
  unit: VolumeUnit,
): string {
  if (row.amount_ml !== null) return formatVolume(row.amount_ml, unit);
  return [row.amount, row.unit].filter((part) => part !== null).join(' ');
}

/** Unidad de volumen elegida por el usuario, recordada en `localStorage`. */
@Injectable({ providedIn: 'root' })
export class Units {
  readonly volume = signal<VolumeUnit>(load());

  set(unit: VolumeUnit): void {
    this.volume.set(unit);
    try {
      localStorage.setItem(STORAGE_KEY, unit);
    } catch {
      // Sin almacenamiento (modo privado): la elección dura lo que la pestaña.
    }
  }
}

function load(): VolumeUnit {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'oz' ? 'oz' : 'ml';
  } catch {
    return 'ml';
  }
}
