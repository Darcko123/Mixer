import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

// Espejo a mano de `backend/app/schemas.py` (§7 del plan).

export type Kind = 'category' | 'generic' | 'brand';
export type Role = 'required' | 'optional' | 'garnish';
export type Status = 'have' | 'have_equivalent' | 'substitute' | 'missing';

export interface IngredientRef {
  slug: string;
  name: string;
}

export type RecipeRef = IngredientRef;

/** `path` son los nombres desde la raíz hasta el propio nodo ("Destilado › Ron › Ron blanco"). */
export interface IngredientSummary extends IngredientRef {
  kind: Kind;
  path: string[];
}

export interface IngredientNode extends IngredientRef {
  kind: Kind;
  children: IngredientNode[];
}

export interface InventoryItem extends IngredientSummary {
  added_at: string;
}

export interface RecipeMatch extends RecipeRef {
  popularity: number;
  required_count: number;
  missing_count: number;
  substitute_count: number;
  missing: IngredientRef[];
}

export interface MatchesResponse {
  can_make: RecipeMatch[];
  almost: RecipeMatch[];
}

export interface PurchaseSuggestion {
  ingredient: IngredientRef;
  unlocks: RecipeRef[];
  improves: RecipeRef[];
}

export interface ShoppingItem {
  ingredient: IngredientRef;
  alt_group: number | null;
  examples: IngredientRef[];
  also_unlocks: RecipeRef[];
  also_improves: RecipeRef[];
}

/** `status` es `null` en `optional`/`garnish` y en las alternativas no usadas de un `alt_group`. */
export interface RecipeIngredientStatus {
  ingredient: string;
  name: string;
  amount: number | null;
  unit: string | null;
  amount_ml: number | null;
  role: Role;
  alt_group: number | null;
  status: Status | null;
  covered_by: IngredientRef | null;
  substitute: IngredientRef | null;
}

export interface RecipeDetail extends RecipeRef {
  method: string | null;
  glass: string | null;
  instructions: string | null;
  garnish_text: string | null;
  can_make: boolean;
  missing_count: number;
  substitute_count: number;
  ingredients: RecipeIngredientStatus[];
  shopping_list: ShoppingItem[];
}

export interface Health {
  status: 'ok';
  catalog: { ingredients: number; recipes: number } | null;
}

@Injectable({ providedIn: 'root' })
export class Api {
  private readonly http = inject(HttpClient);

  searchIngredients(q: string, limit = 10): Observable<IngredientSummary[]> {
    return this.http.get<IngredientSummary[]>('/api/ingredients', { params: { q, limit } });
  }

  ingredientTree(): Observable<IngredientNode[]> {
    return this.http.get<IngredientNode[]>('/api/ingredients/tree');
  }

  inventory(): Observable<InventoryItem[]> {
    return this.http.get<InventoryItem[]>('/api/inventory');
  }

  addToInventory(slug: string): Observable<InventoryItem> {
    return this.http.put<InventoryItem>(`/api/inventory/${encodeURIComponent(slug)}`, null);
  }

  removeFromInventory(slug: string): Observable<void> {
    return this.http.delete<void>(`/api/inventory/${encodeURIComponent(slug)}`);
  }

  matches(maxMissing = 2, allowSubstitutes = true): Observable<MatchesResponse> {
    return this.http.get<MatchesResponse>('/api/matches', {
      params: { max_missing: maxMissing, allow_substitutes: allowSubstitutes },
    });
  }

  suggestions(k = 3, allowSubstitutes = true): Observable<PurchaseSuggestion[]> {
    return this.http.get<PurchaseSuggestion[]>('/api/shopping/suggestions', {
      params: { k, allow_substitutes: allowSubstitutes },
    });
  }

  searchRecipes(q: string, limit = 10): Observable<RecipeRef[]> {
    return this.http.get<RecipeRef[]>('/api/recipes', { params: { q, limit } });
  }

  recipe(slug: string, allowSubstitutes = true, preferOriginal = false): Observable<RecipeDetail> {
    return this.http.get<RecipeDetail>(`/api/recipes/${encodeURIComponent(slug)}`, {
      params: { allow_substitutes: allowSubstitutes, prefer_original: preferOriginal },
    });
  }

  health(): Observable<Health> {
    return this.http.get<Health>('/api/health');
  }
}
