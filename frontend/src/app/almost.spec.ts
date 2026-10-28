import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RecipeMatch } from './api';
import { Almost } from './almost';

const match = (slug: string, name: string, ...missing: string[]): RecipeMatch => ({
  slug,
  name,
  popularity: 0,
  required_count: 3,
  missing_count: missing.length,
  substitute_count: 0,
  missing: missing.map((m) => ({ slug: m.toLowerCase(), name: m })),
  image: null,
});

describe('Almost', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('muestra los faltantes como chips y "ya lo tengo" añade a la barra y recalcula', async () => {
    const fixture = TestBed.createComponent(Almost);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http.expectOne('/api/inventory').flush([]);
    await Promise.resolve();
    TestBed.tick();
    http.expectOne('/api/matches?max_missing=2&allow_substitutes=true').flush({
      can_make: [],
      almost: [match('mojito', 'Mojito', 'Menta'), match('daiquiri', 'Daiquirí', 'Lima', 'Ron')],
    });
    await fixture.whenStable();
    const cards = () =>
      [...root.querySelectorAll('mat-card')].map((c) => [
        c.querySelector('mat-card-title')?.textContent,
        [...c.querySelectorAll('mat-chip')].map((chip) => chip.textContent?.trim()),
      ]);
    expect(cards()).toEqual([
      ['Mojito', ['Menta']],
      ['Daiquirí', ['Lima', 'Ron']],
    ]);

    root.querySelector<HTMLButtonElement>('[aria-label="Ya tengo Menta"]')!.click();
    const put = http.expectOne('/api/inventory/menta');
    expect(put.request.method).toBe('PUT');
    put.flush({ slug: 'menta', name: 'Menta', kind: 'generic', path: ['Menta'], added_at: '' });
    await Promise.resolve();
    TestBed.tick();
    http.expectOne('/api/matches?max_missing=2&allow_substitutes=true').flush({
      can_make: [],
      almost: [match('daiquiri', 'Daiquirí', 'Lima', 'Ron')],
    });
    await fixture.whenStable();
    expect(cards()).toEqual([['Daiquirí', ['Lima', 'Ron']]]);
  });
});
