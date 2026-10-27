import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

// Vista provisional: cada ruta la sustituye por su componente al implementarse.
@Component({
  selector: 'app-placeholder',
  template: `<h1>{{ title }}</h1>
    <p>Vista en construcción.</p>`,
})
export class Placeholder {
  protected readonly title = inject(ActivatedRoute).snapshot.title;
}
