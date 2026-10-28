import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, withComponentInputBinding } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { RecipeDetail, RecipeIngredientStatus } from './api';
import { routes } from './app.routes';
import { Bar } from './bar';
import { Units } from './units';

const ref = (name: string) => ({ slug: name.toLowerCase(), name });
const row = (
  name: string,
  status: RecipeIngredientStatus['status'],
  extra: Partial<RecipeIngredientStatus> = {},
): RecipeIngredientStatus => ({
  ingredient: name.toLowerCase(),
  name,
  amount: null,
  unit: null,
  amount_ml: null,
  role: 'required',
  alt_group: null,
  status,
  covered_by: null,
  substitute: null,
  ...extra,
});

const daiquiri: RecipeDetail = {
  ...ref('Daiquirí'),
  method: null,
  glass: null,
  instructions: 'Agitar con hielo.',
  garnish_text: null,
  image: null,
  can_make: false,
  missing_count: 1,
  substitute_count: 1,
  ingredients: [
    row('Ron blanco', 'have_equivalent', { covered_by: ref('Bacardí'), amount_ml: 60 }),
    row('Jugo de lima', 'have'),
    row('Jarabe simple', 'substitute', { substitute: ref('Azúcar') }),
    row('Bitter', 'missing', { alt_group: 1, amount: 2, unit: 'dash' }),
    row('Angostura', 'missing', { alt_group: 1 }),
    row('Lima', null, { role: 'garnish' }),
  ],
  shopping_list: [
    {
      ingredient: ref('Bitter'),
      alt_group: 1,
      examples: [ref('Peychaud')],
      also_unlocks: [ref('Sazerac')],
      also_improves: [],
    },
  ],
};

describe('Search', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes, withComponentInputBinding()),
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  /** Abre la vista por su ruta, para que `?receta=` llegue como en la app. */
  const open = async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/buscar');
    TestBed.tick();
    http.expectOne('/api/inventory').flush([]);
    await harness.fixture.whenStable();
    return { fixture: harness.fixture, root: harness.fixture.nativeElement as HTMLElement };
  };
  // Elegir una receta navega: se espera a que la URL cambie y a que el detalle pida la receta.
  const navigated = async () => {
    await new Promise((r) => setTimeout(r));
    TestBed.tick();
  };

  it('busca con debounce y muestra el detalle con marcas, lista de compras y también desbloquea', async () => {
    const { fixture, root } = await open();

    const input = root.querySelector('input')!;
    input.focus();
    input.value = 'daik';
    input.dispatchEvent(new Event('input'));
    await new Promise((r) => setTimeout(r, 250));
    http.expectOne('/api/recipes?q=daik&limit=10').flush([ref('Daiquirí')]);
    await fixture.whenStable();
    document.querySelector<HTMLElement>('mat-option')!.click();
    await navigated();
    http
      .expectOne('/api/recipes/daiquir%C3%AD?allow_substitutes=true&prefer_original=false')
      .flush(daiquiri);
    await fixture.whenStable();

    // Con la receta abierta el buscador desaparece.
    expect(root.querySelector('input')).toBeNull();
    expect(TestBed.inject(Router).url).toBe('/buscar?receta=daiquir%C3%AD');
    const text = (selector: string) =>
      [...root.querySelectorAll(selector)].map((e) => e.textContent?.replace(/\s+/g, ' ').trim());
    expect(text('.ingredients li')).toEqual([
      '60 ml Ron blanco ✓ vía Bacardí',
      'Jugo de lima ✓ Lo tienes',
      'Jarabe simple ≈ con Azúcar',
      '2 dash Bitter ✗ Falta',
      'o Angostura ✗ Falta',
      'Lima Decoración',
    ]);
    expect(text('mat-card-subtitle')).toEqual(['Falta 1 · ≈ usa sustituto']);
    expect(root.querySelector('.photo')).toBeNull();
    expect(root.querySelector('.mark[data-status="missing"]')?.textContent).toBe('✗ Falta');
    expect(text('ul:not(.ingredients) li')[0]).toMatch(/^Bitter Por ejemplo/);
    expect(text('ul:not(.ingredients) p')).toEqual([
      'Por ejemplo: Peychaud',
      'También desbloquea: Sazerac',
    ]);

    TestBed.inject(Units).set('oz');
    await fixture.whenStable();
    expect(text('.amount')).toEqual(['2 oz', '2 dash']);
    localStorage.clear();
  });

  it('avisa sin resultados, muestra el error del detalle con reintento y lo recalcula al cambiar la barra', async () => {
    const { fixture, root } = await open();

    const input = root.querySelector('input')!;
    input.focus();
    const search = async (q: string) => {
      input.value = q;
      input.dispatchEvent(new Event('input'));
      await new Promise((r) => setTimeout(r, 250));
      return http.expectOne(`/api/recipes?q=${q}&limit=10`);
    };
    const options = () =>
      [...document.querySelectorAll('mat-option')].map((o) => o.textContent?.trim());

    (await search('xyz')).flush([]);
    await fixture.whenStable();
    expect(options()).toEqual(['Sin resultados']);

    (await search('dai')).flush(null, { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();
    expect(options()).toEqual(['✗ No se pudo buscar. Inténtalo de nuevo.']);

    (await search('daik')).flush([ref('Daiquirí')]);
    await fixture.whenStable();
    document.querySelector<HTMLElement>('mat-option')!.click();
    await navigated();
    const url = '/api/recipes/daiquir%C3%AD?allow_substitutes=true&prefer_original=false';
    http.expectOne(url).flush(null, { status: 404, statusText: 'Not Found' });
    await fixture.whenStable();
    expect(root.querySelector('[role="alert"]')?.textContent).toContain('No se pudieron cargar');
    expect(root.querySelector('mat-card')).toBeNull();

    root.querySelector<HTMLButtonElement>('[role="alert"] button')!.click();
    fixture.detectChanges();
    expect(root.querySelector('mat-progress-bar')).not.toBeNull();
    http.expectOne(url).flush(daiquiri);
    await fixture.whenStable();
    expect(root.querySelector('[role="alert"]')).toBeNull();
    expect(root.querySelector('mat-card-subtitle')?.textContent).toContain('Falta 1');

    TestBed.inject(Bar).inventory.set([]);
    TestBed.tick();
    http.expectOne(url).flush({
      ...daiquiri,
      can_make: true,
      missing_count: 0,
      substitute_count: 0,
      image: { url: '/api/images/daiquiri.webp', source_url: 'https://iba-world.com/daiquiri/' },
    });
    await fixture.whenStable();
    expect(root.querySelector('mat-card-subtitle')?.textContent?.trim()).toBe('Puedes prepararlo');
    const img = root.querySelector('.photo img')!;
    expect([img.getAttribute('src'), img.getAttribute('alt')]).toEqual([
      '/api/images/daiquiri.webp',
      'Foto de Daiquirí',
    ]);
    expect(root.querySelector('.photo a')?.getAttribute('href')).toBe(
      'https://iba-world.com/daiquiri/',
    );
  });
});
