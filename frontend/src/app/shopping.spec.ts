import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { PurchaseSuggestion } from './api';
import { Shopping } from './shopping';

const ref = (name: string) => ({ slug: name.toLowerCase(), name });
const suggestion = (
  name: string,
  unlocks: string[],
  improves: string[] = [],
): PurchaseSuggestion => ({
  ingredient: ref(name),
  unlocks: unlocks.map(ref),
  improves: improves.map(ref),
});

describe('Shopping', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('muestra las compras con lo que desbloquean y recalcula al cambiar k', async () => {
    const fixture = TestBed.createComponent(Shopping);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http.expectOne('/api/inventory').flush([]);
    await Promise.resolve();
    TestBed.tick();
    http
      .expectOne('/api/shopping/suggestions?k=3&allow_substitutes=true')
      .flush([
        suggestion('Ron', ['Daiquirí', 'Mojito'], ['Cuba libre']),
        suggestion('Lima', ['Caipiriña']),
      ]);
    await fixture.whenStable();
    const cards = () =>
      [...root.querySelectorAll('mat-card')].map((c) =>
        [...c.querySelectorAll('mat-card-title, p')].map((e) => e.textContent?.trim()).join(' | '),
      );
    expect(cards()).toEqual([
      '1. Ron | Desbloquea: Daiquirí, Mojito | Acerca: Cuba libre',
      '2. Lima | Desbloquea: Caipiriña',
    ]);

    const toggle = [...root.querySelectorAll<HTMLButtonElement>('mat-button-toggle button')];
    toggle.find((b) => b.textContent?.trim() === '1')!.click();
    TestBed.tick();
    http
      .expectOne('/api/shopping/suggestions?k=1&allow_substitutes=true')
      .flush([suggestion('Ron', ['Daiquirí', 'Mojito'])]);
    await fixture.whenStable();
    expect(cards()).toEqual(['1. Ron | Desbloquea: Daiquirí, Mojito']);
  });
});
