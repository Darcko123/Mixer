import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Flavor, RecipeMatch } from './api';
import { Bar, Matches } from './bar';
import { CanMake } from './can-make';

const match = (
  slug: string,
  name: string,
  substitute_count = 0,
  image: RecipeMatch['image'] = null,
  flavors: Flavor[] = [],
): RecipeMatch => ({
  slug,
  name,
  popularity: 0,
  required_count: 3,
  missing_count: 0,
  substitute_count,
  missing: [],
  image,
  flavors,
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

  it('filtra por sabor: solo las recetas con todos los sabores elegidos', async () => {
    const fixture = TestBed.createComponent(CanMake);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http.expectOne('/api/inventory').flush([]);
    await Promise.resolve();
    TestBed.tick();
    http.expectOne('/api/matches?max_missing=2&allow_substitutes=true').flush({
      can_make: [
        match('daiquiri', 'Daiquirí', 0, null, ['sour', 'sweet']),
        match('old-fashioned', 'Old Fashioned', 0, null, ['strong', 'sweet']),
        match('mojito', 'Mojito'),
      ],
      almost: [],
    });
    await fixture.whenStable();
    const chips = () => [...root.querySelectorAll<HTMLButtonElement>('button[role="option"]')];
    const titles = () => [...root.querySelectorAll('mat-card-title')].map((t) => t.textContent);
    const toggle = async (label: string) => {
      chips()
        .find((c) => c.textContent?.trim() === label)!
        .click();
      await fixture.whenStable();
    };
    // Solo los sabores presentes, en el orden del vocabulario; cada tarjeta muestra los suyos.
    expect(chips().map((c) => c.textContent?.trim())).toEqual(['Dulce', 'Ácido', 'Fuerte']);
    expect(root.querySelector('.flavors')?.textContent).toBe('Ácido · Dulce');

    await toggle('Dulce');
    expect(titles()).toEqual(['Daiquirí', 'Old Fashioned']);
    await toggle('Ácido');
    expect(titles()).toEqual(['Daiquirí']);
    await toggle('Fuerte');
    expect(titles()).toEqual([]);
    expect(root.querySelector('p:not(.flavors)')?.textContent?.trim()).toBe(
      'Ningún cóctel tiene todos esos sabores.',
    );

    // La selección vive en Matches: se conserva al volver a la vista.
    expect(TestBed.inject(Matches).flavors()).toEqual(['sweet', 'sour', 'strong']);
  });
});
