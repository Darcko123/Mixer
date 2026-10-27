import { Component, inject } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { routes } from './app.routes';
import { Bar } from './bar';
import { Status } from './status';

@Component({
  imports: [MatTabsModule, MatToolbarModule, RouterLink, RouterLinkActive, RouterOutlet, Status],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  // Todas las vistas dependen del inventario: su carga y su error se muestran una vez aquí.
  protected readonly bar = inject(Bar);
  protected readonly views = routes.filter((route) => typeof route.title === 'string');
}
