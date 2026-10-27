import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { InventoryItem } from './api';
import { Bar } from './bar';
import { MyBar } from './my-bar';

const item = (slug: string, ...path: string[]): InventoryItem => ({
  slug,
  name: path.at(-1)!,
  kind: 'generic',
  path,
  added_at: '2026-10-27T00:00:00Z',
});

describe('MyBar', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('agrupa por categoría, busca con la ruta visible, añade y quita', async () => {
    const fixture = TestBed.createComponent(MyBar);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http
      .expectOne('/api/inventory')
      .flush([
        item('ron-blanco', 'Destilados', 'Ron', 'Ron blanco'),
        item('vodka', 'Destilados', 'Vodka'),
        item('jugo-lima', 'Jugos y purés', 'Jugo de lima'),
      ]);
    await fixture.whenStable();
    const groups = () =>
      [...root.querySelectorAll('section')].map((s) => [
        s.querySelector('h2')?.textContent,
        s.querySelectorAll('li').length,
      ]);
    expect(groups()).toEqual([
      ['Destilados', 2],
      ['Jugos y purés', 1],
    ]);

    const input = root.querySelector('input')!;
    input.focus();
    input.value = 'jarabe';
    input.dispatchEvent(new Event('input'));
    await new Promise((r) => setTimeout(r, 250));
    http
      .expectOne('/api/ingredients?q=jarabe&limit=10')
      .flush([item('jarabe-simple', 'Jarabes y endulzantes', 'Jarabe simple')]);
    await fixture.whenStable();
    const option = document.querySelector<HTMLElement>('mat-option')!;
    expect(option.textContent).toContain('Jarabes y endulzantes');

    option.click();
    http
      .expectOne('/api/inventory/jarabe-simple')
      .flush(item('jarabe-simple', 'Jarabes y endulzantes', 'Jarabe simple'));
    await fixture.whenStable();
    expect(groups()).toHaveLength(3);
    expect(input.value).toBe('');

    root.querySelector<HTMLButtonElement>('button[aria-label="Quitar Vodka"]')!.click();
    http.expectOne('/api/inventory/vodka').flush(null, { status: 204, statusText: 'No Content' });
    await fixture.whenStable();
    expect(groups()[0]).toEqual(['Destilados', 1]);
  });

  it('muestra el vacío, marca lo que ya está, avisa sin resultados o con error y si no pudo quitar', async () => {
    const fixture = TestBed.createComponent(MyBar);
    const root = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    http.expectOne('/api/inventory').flush([]);
    await fixture.whenStable();
    expect(root.querySelector('p')?.textContent?.trim()).toBe('Añade ingredientes para empezar.');

    const input = root.querySelector('input')!;
    input.focus();
    const search = async (q: string) => {
      input.value = q;
      input.dispatchEvent(new Event('input'));
      await new Promise((r) => setTimeout(r, 250));
      return http.expectOne(`/api/ingredients?q=${q}&limit=10`);
    };
    const options = () =>
      [...document.querySelectorAll('mat-option')].map((o) => [
        o.textContent?.replace(/\s+/g, ' ').trim(),
        o.getAttribute('aria-disabled'),
      ]);

    (await search('xyz')).flush([]);
    await fixture.whenStable();
    expect(options()).toEqual([['Sin resultados', 'true']]);

    (await search('ron')).flush(null, { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();
    expect(options()).toEqual([['✗ No se pudo buscar. Inténtalo de nuevo.', 'true']]);

    // Tras un error la búsqueda sigue funcionando.
    TestBed.inject(Bar).inventory.set([item('vodka', 'Destilados', 'Vodka')]);
    (await search('vod')).flush([item('vodka', 'Destilados', 'Vodka')]);
    await fixture.whenStable();
    expect(options()).toEqual([['Vodka (ya en tu barra) Destilados', 'true']]);
    expect(root.querySelector('p')).toBeNull();

    root.querySelector<HTMLButtonElement>('button[aria-label="Quitar Vodka"]')!.click();
    http.expectOne('/api/inventory/vodka').flush(null, { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();
    expect(root.querySelectorAll('section li')).toHaveLength(1);
    expect(document.querySelector('simple-snack-bar')?.textContent).toContain(
      'No se pudo quitar el ingrediente.',
    );
  });
});
