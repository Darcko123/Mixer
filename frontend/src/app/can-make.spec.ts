import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { RecipeMatch } from './api';
import { Bar } from './bar';
import { CanMake } from './can-make';

const match = (slug: string, name: string, substitute_count = 0): RecipeMatch => ({
  slug,
  name,
  popularity: 0,
  required_count: 3,
  missing_count: 0,
  substitute_count,
  missing: [],
});

describe('CanMake', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
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
    http.expectOne('/api/matches?max_missing=0&allow_substitutes=true').flush({
      can_make: [match('daiquiri', 'Daiquirí'), match('mojito', 'Mojito', 1)],
      almost: [],
    });
    await fixture.whenStable();
    const cards = () =>
      [...root.querySelectorAll('mat-card')].map((c) => [
        c.querySelector('mat-card-title')?.textContent,
        c.querySelector('.substitute')?.textContent ?? null,
      ]);
    expect(cards()).toEqual([
      ['Daiquirí', null],
      ['Mojito', '≈ usa sustituto'],
    ]);

    const removing = TestBed.inject(Bar).remove('ron-blanco');
    http
      .expectOne('/api/inventory/ron-blanco')
      .flush(null, { status: 204, statusText: 'No Content' });
    await removing;
    TestBed.tick();
    http
      .expectOne('/api/matches?max_missing=0&allow_substitutes=true')
      .flush({ can_make: [], almost: [] });
    await fixture.whenStable();
    expect(cards()).toEqual([]);
  });
});
