import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { App } from './app';
import { routes } from './app.routes';

describe('App', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
  });

  it('enlaza las cinco vistas y redirige a Mi barra', async () => {
    const fixture = TestBed.createComponent(App);
    await TestBed.inject(Router).navigateByUrl('/');
    await fixture.whenStable();
    const root = fixture.nativeElement as HTMLElement;
    const links = [...root.querySelectorAll('nav a')].map((a) => a.textContent?.trim());
    expect(links).toEqual([
      'Mi barra',
      'Puedo preparar',
      'Casi listos',
      'Qué comprar',
      'Buscar cóctel',
    ]);
    expect(root.querySelector('h1')?.textContent).toBe('Mi barra');
    expect(root.querySelector('a[aria-selected="true"]')?.textContent?.trim()).toBe('Mi barra');
  });
});
