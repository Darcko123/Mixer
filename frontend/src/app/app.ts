import { Component, inject } from '@angular/core';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTabsModule } from '@angular/material/tabs';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { routes } from './app.routes';
import { Bar } from './bar';
import { Status } from './status';
import { Units } from './units';

@Component({
  imports: [
    MatButtonToggleModule,
    MatTabsModule,
    MatToolbarModule,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    Status,
  ],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  // Todas las vistas dependen del inventario: su carga y su error se muestran una vez aquí.
  protected readonly bar = inject(Bar);
  protected readonly units = inject(Units);
  protected readonly views = routes.filter((route) => typeof route.title === 'string');
}
