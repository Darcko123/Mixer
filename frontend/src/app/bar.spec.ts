import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Api, InventoryItem } from './api';
import { Bar } from './bar';

const item = (slug: string, ...path: string[]): InventoryItem => ({
  slug,
  name: path.at(-1)!,
  kind: 'generic',
  path,
  added_at: '2026-10-27T00:00:00Z',
});

describe('Bar', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('carga el inventario, añade en orden por ruta y quita', async () => {
    const bar = TestBed.inject(Bar);
    TestBed.tick();
    http.expectOne('/api/inventory').flush([item('vodka', 'Destilado', 'Vodka')]);
    await TestBed.inject(ApplicationRef).whenStable();
    expect(bar.inventory.value()?.map((i) => i.slug)).toEqual(['vodka']);

    const adding = bar.add('ron-blanco');
    const put = http.expectOne('/api/inventory/ron-blanco');
    expect(put.request.method).toBe('PUT');
    put.flush(item('ron-blanco', 'Destilado', 'Ron', 'Ron blanco'));
    await adding;
    expect(bar.inventory.value()?.map((i) => i.slug)).toEqual(['ron-blanco', 'vodka']);
    expect(bar.slugs().has('ron-blanco')).toBe(true);

    const removing = bar.remove('vodka');
    const del = http.expectOne('/api/inventory/vodka');
    expect(del.request.method).toBe('DELETE');
    del.flush(null, { status: 204, statusText: 'No Content' });
    await removing;
    expect(bar.inventory.value()?.map((i) => i.slug)).toEqual(['ron-blanco']);
  });

  it('envía los parámetros de consulta de §7', () => {
    const api = TestBed.inject(Api);
    api.matches(1, false).subscribe();
    http.expectOne('/api/matches?max_missing=1&allow_substitutes=false').flush({});
    api.recipe('daiquiri').subscribe();
    http.expectOne('/api/recipes/daiquiri?allow_substitutes=true&prefer_original=false').flush({});
  });
});
