export type VolumeUnit = 'ml' | 'oz';

const ML_PER_OZ = 30;
const QUARTERS = ['', '¼', '½', '¾'];

/** `amount_ml` de la API → texto en la unidad elegida. Las oz se redondean al cuarto (mínimo ¼). */
export function formatVolume(ml: number, unit: VolumeUnit): string {
  if (unit === 'ml') return `${ml} ml`;
  const quarters = Math.max(1, Math.round((ml / ML_PER_OZ) * 4));
  const whole = Math.floor(quarters / 4);
  return `${whole || ''}${QUARTERS[quarters % 4]} oz`;
}
