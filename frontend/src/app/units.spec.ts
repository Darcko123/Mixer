import { formatVolume } from './units';

describe('formatVolume', () => {
  it('muestra ml tal cual', () => {
    expect(formatVolume(60, 'ml')).toBe('60 ml');
  });

  it('convierte a oz redondeando al cuarto', () => {
    expect(formatVolume(60, 'oz')).toBe('2 oz');
    expect(formatVolume(45, 'oz')).toBe('1½ oz');
    expect(formatVolume(22, 'oz')).toBe('¾ oz');
    expect(formatVolume(20, 'oz')).toBe('¾ oz');
    expect(formatVolume(15, 'oz')).toBe('½ oz');
    expect(formatVolume(2, 'oz')).toBe('¼ oz');
  });
});
