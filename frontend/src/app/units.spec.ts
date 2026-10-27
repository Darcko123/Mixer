import { TestBed } from '@angular/core/testing';
import { formatAmount, formatVolume, Units } from './units';

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

describe('formatAmount', () => {
  it('usa amount_ml si existe y, si no, amount + unit', () => {
    expect(formatAmount({ amount: 1.5, unit: 'oz', amount_ml: 45 }, 'ml')).toBe('45 ml');
    expect(formatAmount({ amount: 1.5, unit: 'oz', amount_ml: 45 }, 'oz')).toBe('1½ oz');
    expect(formatAmount({ amount: 2, unit: 'dash', amount_ml: null }, 'oz')).toBe('2 dash');
    expect(formatAmount({ amount: null, unit: null, amount_ml: null }, 'ml')).toBe('');
  });
});

describe('Units', () => {
  afterEach(() => localStorage.clear());

  it('recuerda la unidad elegida', () => {
    expect(TestBed.inject(Units).volume()).toBe('ml');
    TestBed.inject(Units).set('oz');
    TestBed.resetTestingModule();
    expect(TestBed.inject(Units).volume()).toBe('oz');
  });
});
