import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { RecipeDetail, RecipeIngredientStatus } from './api';
import { Search } from './search';

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
  can_make: false,
  missing_count: 1,
  substitute_count: 1,
  ingredients: [
    row('Ron blanco', 'have_equivalent', { covered_by: ref('Bacardí') }),
    row('Jugo de lima', 'have'),
    row('Jarabe simple', 'substitute', { substitute: ref('Azúcar') }),
    row('Bitter', 'missing', { alt_group: 1 }),
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
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('busca con debounce y muestra el detalle con marcas, lista de compras y también desbloquea', async () => {
    const fixture = TestBed.createComponent(Search);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http.expectOne('/api/inventory').flush([]);
    await fixture.whenStable();

    const input = root.querySelector('input')!;
    input.focus();
    input.value = 'daik';
    input.dispatchEvent(new Event('input'));
    await new Promise((r) => setTimeout(r, 250));
    http.expectOne('/api/recipes?q=daik&limit=10').flush([ref('Daiquirí')]);
    await fixture.whenStable();
    document.querySelector<HTMLElement>('mat-option')!.click();
    TestBed.tick();
    http
      .expectOne('/api/recipes/daiquir%C3%AD?allow_substitutes=true&prefer_original=false')
      .flush(daiquiri);
    await fixture.whenStable();

    expect(input.value).toBe('Daiquirí');
    const text = (selector: string) =>
      [...root.querySelectorAll(selector)].map((e) => e.textContent?.replace(/\s+/g, ' ').trim());
    expect(text('.ingredients li')).toEqual([
      'Ron blanco ✓ vía Bacardí',
      'Jugo de lima ✓ Lo tienes',
      'Jarabe simple ≈ con Azúcar',
      'Bitter ✗ Falta',
      'o Angostura ✗ Falta',
      'Lima Decoración',
    ]);
    expect(text('mat-card-subtitle')).toEqual(['Falta 1 · ≈ usa sustituto']);
    expect(text('ul:not(.ingredients) li')[0]).toMatch(/^Bitter Por ejemplo/);
    expect(text('ul:not(.ingredients) p')).toEqual([
      'Por ejemplo: Peychaud',
      'También desbloquea: Sazerac',
    ]);
  });
});
