import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RecipeMatch } from './api';
import { Bar } from './bar';
import { CanMake } from './can-make';

const match = (
  slug: string,
  name: string,
  substitute_count = 0,
  image: RecipeMatch['image'] = null,
): RecipeMatch => ({
  slug,
  name,
  popularity: 0,
  required_count: 3,
  missing_count: 0,
  substitute_count,
  missing: [],
  image,
});

describe('CanMake', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('muestra las recetas, marca las que usan sustituto y recalcula al cambiar la barra', async () => {
    const fixture = TestBed.createComponent(CanMake);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http.expectOne('/api/inventory').flush([]);
    await Promise.resolve();
    TestBed.tick();
    http.expectOne('/api/matches?max_missing=2&allow_substitutes=true').flush({
      can_make: [
        match('daiquiri', 'Daiquirí', 0, { url: '/api/images/daiquiri.webp', source_url: null }),
        match('mojito', 'Mojito', 1),
      ],
      almost: [],
    });
    await fixture.whenStable();
    // Con foto, la imagen (decorativa: el nombre va al lado); sin foto, el marcador ocupa su hueco.
    const photos = [...root.querySelectorAll('app-recipe-photo')];
    expect(photos[0].querySelector('img')?.getAttribute('src')).toBe('/api/images/daiquiri.webp');
    expect(photos[0].querySelector('img')?.getAttribute('alt')).toBe('');
    expect(photos[1].querySelector('img')).toBeNull();
    expect(photos[1].querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
    photos[0].querySelector('img')!.dispatchEvent(new Event('error'));
    await fixture.whenStable();
    expect(photos[0].querySelector('img')).toBeNull();
    const cards = () =>
      [...root.querySelectorAll('mat-card')].map((c) => [
        c.querySelector('mat-card-title')?.textContent,
        c.querySelector('.substitute')?.textContent ?? null,
      ]);
    expect(cards()).toEqual([
      ['Daiquirí', null],
      ['Mojito', '≈ usa sustituto'],
    ]);
    expect(root.querySelector('mat-card a')?.getAttribute('href')).toBe('/buscar?receta=daiquiri');

    const removing = TestBed.inject(Bar).remove('ron-blanco');
    http
      .expectOne('/api/inventory/ron-blanco')
      .flush(null, { status: 204, statusText: 'No Content' });
    await removing;
    TestBed.tick();
    http
      .expectOne('/api/matches?max_missing=2&allow_substitutes=true')
      .flush({ can_make: [], almost: [] });
    await fixture.whenStable();
    expect(cards()).toEqual([]);
  });

  it('pide añadir ingredientes con la barra vacía y permite reintentar tras un error', async () => {
    const fixture = TestBed.createComponent(CanMake);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http.expectOne('/api/inventory').flush([]);
    await Promise.resolve();
    TestBed.tick();
    const url = '/api/matches?max_missing=2&allow_substitutes=true';
    http.expectOne(url).flush({ can_make: [], almost: [] });
    await fixture.whenStable();
    expect(root.querySelector('p')?.textContent?.trim()).toBe('Añade ingredientes para empezar.');

    TestBed.inject(Bar).inventory.set([]);
    TestBed.tick();
    http.expectOne(url).flush(null, { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();
    expect(root.querySelector('[role="alert"]')?.textContent).toContain('No se pudieron cargar');

    root.querySelector<HTMLButtonElement>('[role="alert"] button')!.click();
    fixture.detectChanges();
    expect(root.querySelector('mat-progress-bar')).not.toBeNull();
    http.expectOne(url).flush({ can_make: [match('daiquiri', 'Daiquirí')], almost: [] });
    await fixture.whenStable();
    expect(root.querySelector('[role="alert"]')).toBeNull();
    expect(root.querySelector('mat-card-title')?.textContent).toBe('Daiquirí');
  });
});
