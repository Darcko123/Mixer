import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RecipeMatch } from './api';
import { App } from './app';
import { routes } from './app.routes';

describe('App', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)],
    });
  });

  it('enlaza las cinco vistas con sus contadores y redirige a Mi barra', async () => {
    // jsdom no implementa `scrollIntoView`; la pestaña activa se desplaza a la vista.
    const scrolled: Element[] = [];
    Element.prototype.scrollIntoView = function (this: Element) {
      scrolled.push(this);
    };
    const fixture = TestBed.createComponent(App);
    await TestBed.inject(Router).navigateByUrl('/');
    TestBed.tick();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/inventory').flush([]);
    await Promise.resolve();
    TestBed.tick();
    const recipe = {} as RecipeMatch;
    http
      .expectOne('/api/matches?max_missing=2&allow_substitutes=true')
      .flush({ can_make: [recipe], almost: [recipe, recipe] });
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const links = [...root.querySelectorAll('nav a')].map((a) => a.textContent?.trim());
    expect(links).toEqual([
      'Mi barra',
      'Puedo preparar 1',
      'Casi listos 2',
      'Qué comprar',
      'Buscar cóctel',
    ]);
    expect(root.querySelector('h1')?.textContent).toBe('Mi barra');
    expect(root.querySelector('a[aria-selected="true"]')?.textContent?.trim()).toBe('Mi barra');
    expect(scrolled.map((a) => a.textContent?.trim())).toEqual(['Mi barra']);
  });
});
